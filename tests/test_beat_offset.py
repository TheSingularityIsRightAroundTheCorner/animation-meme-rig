"""Regression for the unwired song downbeat offset reported after migration."""
import json
from pathlib import Path
import tempfile
import unittest

import numpy as np
from PIL import Image

from _support import SKILL, core, sprite


class BeatOffsetRegressionTests(unittest.TestCase):
    def test_fractional_offset_rounds_absolute_edges_without_drift(self):
        count, bpm, fps, offset = 1000, 189.9, 30, 88.5 * 30 / 1000
        step = 60 / bpm * fps
        edges = [round(offset + k * step) for k in range(count + 1)]
        actual = core('beat_grid').frame_counts(count, bpm, fps, 1, offset_frames=offset)
        self.assertEqual(actual, [b - a for a, b in zip(edges, edges[1:])])
        self.assertEqual(sum(actual), edges[-1] - edges[0])
        self.assertNotEqual(edges, [round(offset) + round(k * step) for k in range(count + 1)])

    def test_fractional_offset_moves_pose_cuts_on_the_export_timeline(self):
        colors = [(220, 30, 20), (20, 30, 220)]
        images = [Image.new('RGBA', (16, 16), (*color, 255)) for color in colors]
        sequence = [(1 + k % 2, 'none', 0) for k in range(6)]
        edges = [round(2.655 + k * 60 / 189.9 * 30) for k in range(7)]
        frames = core('mesh_warp').render_sequence(
            images, sequence, size=(16, 16), bpm=189.9, fps=30,
            beats_per_pose=1, offset_ms=88.5)
        expected = [colors[0]] * edges[0]
        for k, (start, end) in enumerate(zip(edges, edges[1:])):
            expected.extend([colors[k % 2]] * (end - start))
        self.assertEqual(len(frames), edges[-1])
        self.assertEqual([f.getpixel((8, 8)) for f in frames], expected)

    def motion_scene(self, offset_ms=0):
        return core('mesh_warp').render_sequence(
            [sprite((32, 48), (8, 4, 18, 40))],
            [(1, 'waveR', 1), (1, 'shakeL', 1)], size=(32, 48),
            bpm=60, fps=8, beats_per_pose=1, offset_ms=offset_ms)

    def test_positive_offset_holds_initial_pose_without_starting_motion_early(self):
        baseline = self.motion_scene()
        delayed = self.motion_scene(250)
        self.assertEqual(len(delayed), len(baseline) + 2)
        self.assertTrue(any(not np.array_equal(baseline[0], f) for f in baseline[1:8]))
        for frame in delayed[:2]:
            np.testing.assert_array_equal(frame, baseline[0])
        for actual, expected in zip(delayed[2:], baseline):
            np.testing.assert_array_equal(actual, expected)

    def test_negative_offset_crops_elapsed_motion_without_restarting_phase(self):
        baseline = self.motion_scene()
        advanced = self.motion_scene(-250)
        self.assertEqual(len(advanced), len(baseline) - 2)
        for actual, expected in zip(advanced, baseline[2:]):
            np.testing.assert_array_equal(actual, expected)

    def test_offset_cannot_place_the_entire_sequence_before_output_zero(self):
        with self.assertRaisesRegex(ValueError, 'offset_ms.*no output frames'):
            self.motion_scene(-2000)

    def test_scene_offset_must_be_a_finite_number(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            sprite().save(root / 'pose.png')
            spec = {'version': 1, 'mode': 'mesh', 'assets': {'poses': ['pose.png']},
                    'sequence': [[1, 'none', 0]]}
            for invalid in (True, '88.5', None, float('nan'), float('inf')):
                with self.subTest(offset_ms=invalid):
                    spec['offset_ms'] = invalid
                    (root / 'scene.json').write_text(json.dumps(spec))
                    with self.assertRaisesRegex(ValueError, 'offset_ms'):
                        core('spec').validate_spec(core('spec').load_spec(root / 'scene.json'))
            for valid in (0, 88.5, -88.5):
                spec['offset_ms'] = valid
                (root / 'scene.json').write_text(json.dumps(spec))
                loaded = core('spec').load_spec(root / 'scene.json')
                core('spec').validate_spec(loaded)
                self.assertEqual(loaded['offset_ms'], valid)

    def test_portable_schema_exposes_offset_in_milliseconds(self):
        schema = json.loads((SKILL / 'schemas/animation.schema.json').read_text())
        mesh = next(rule['then'] for rule in schema['allOf']
                    if rule.get('if', {}).get('properties', {}).get('mode', {}).get('const') == 'mesh')
        self.assertEqual(mesh['properties']['offset_ms']['type'], 'number')


if __name__ == '__main__':
    unittest.main()
