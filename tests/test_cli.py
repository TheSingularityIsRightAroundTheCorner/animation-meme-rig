"""Unified CLI contracts written before its implementation."""
import copy
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from PIL import Image
from _support import SKILL, core, sprite


class CLIRegressionTests(unittest.TestCase):
    def test_globe_rejects_unimplemented_rotation_knobs(self):
        for key in ('spin_start', 'spin_turns', 'cloud_drift_turns'):
            spec = {'version': 1, 'mode': 'globe', 'land': 'land.png', key: .25}
            with self.assertRaisesRegex(ValueError, key):
                core('spec').validate_spec(spec, check_assets=False)

    def run_cli(self, *args):
        return subprocess.run([sys.executable, str(SKILL / 'scripts' / 'render.py'), *map(str, args)],
                              cwd='/', capture_output=True, text=True, env=os.environ.copy())

    def make_rig(self, directory):
        root = Path(directory)
        sprite((32, 32), (10, 9, 19, 23)).save(root / 'part.png')
        spec = {'version': 1, 'mode': 'rig', 'out_size': [32, 32], 'output': 'rendered',
                'parts': {'body': {'file': 'part.png', 'pivot': [16, 16], 'z': 0}},
                'frames': [{'layers': {}, 'camera': [0, 0, 32, 32], 'ms': 40},
                           {'layers': {'body': {'dx': 2}}, 'camera': [0, 0, 32, 32], 'ms': 80}]}
        path = root / 'rig.json'
        path.write_text(json.dumps(spec))
        return path, spec

    def test_rig_end_to_end_relative_assets_and_variable_durations(self):
        with tempfile.TemporaryDirectory() as directory:
            path, _ = self.make_rig(directory)
            result = self.run_cli(path)
            self.assertEqual(result.returncode, 0, result.stderr)
            output = Path(directory) / 'rendered'
            self.assertEqual(len(list(output.glob('*.png'))), 2)
            timing = json.loads((output / 'timing.json').read_text())
            self.assertEqual(timing['durations_ms'], [40, 80])
            with Image.open(output / '00001.png') as image:
                self.assertEqual(image.size, (32, 32))
                self.assertEqual(image.getpixel((21, 15)), (220, 40, 30))

    def test_validate_reads_inputs_but_does_not_render(self):
        with tempfile.TemporaryDirectory() as directory:
            path, _ = self.make_rig(directory)
            result = self.run_cli(path, '--validate')
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertFalse((Path(directory) / 'rendered').exists())
            self.assertIn('valid', result.stdout.lower())

    def test_output_cannot_overwrite_supplied_art(self):
        with tempfile.TemporaryDirectory() as directory:
            path, _ = self.make_rig(directory)
            art = Path(directory) / 'part.png'
            original = art.read_bytes()
            result = self.run_cli(path, '--out', art)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn('input', result.stderr.lower())
            self.assertEqual(art.read_bytes(), original)

    def test_sequence_output_cannot_overwrite_numbered_input_asset(self):
        with tempfile.TemporaryDirectory() as directory:
            path, spec = self.make_rig(directory)
            art = Path(directory) / '00000.png'
            (Path(directory) / 'part.png').rename(art)
            spec['parts']['body']['file'] = '00000.png'
            path.write_text(json.dumps(spec))
            original = art.read_bytes()
            result = self.run_cli(path, '--out', directory)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn('input', result.stderr.lower())
            self.assertEqual(art.read_bytes(), original)

    def test_unknown_mode_and_malformed_camera_or_duration_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            path, spec = self.make_rig(directory)
            cases = []
            bad = copy.deepcopy(spec); bad['mode'] = 'invented'; cases.append(bad)
            bad = copy.deepcopy(spec); bad['frames'][0]['camera'] = [0, 0, 0, 32]; cases.append(bad)
            bad = copy.deepcopy(spec); bad['frames'][0]['ms'] = -1; cases.append(bad)
            for bad in cases:
                path.write_text(json.dumps(bad))
                result = self.run_cli(path, '--validate')
                self.assertNotEqual(result.returncode, 0)
                self.assertFalse((Path(directory) / 'rendered').exists())

    def test_legacy_rig_and_assets_override(self):
        with tempfile.TemporaryDirectory() as directory:
            path, spec = self.make_rig(directory)
            del spec['version']; del spec['mode']; del spec['output']
            spec['base_dir'] = '/mnt/data/no_longer_present'
            spec['out'] = '/mnt/data/no_longer_present/old.gif'
            path.write_text(json.dumps(spec))
            result = self.run_cli(path, '--assets', directory, '--out', str(Path(directory) / 'legacy'))
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertTrue((Path(directory) / 'legacy' / '00000.png').exists())

    def test_profile_deep_merge_is_relative_to_spec(self):
        with tempfile.TemporaryDirectory() as directory:
            path, spec = self.make_rig(directory)
            profile = {'out_size': [32, 32], 'fps': 24, 'bg': [255, 255, 255, 255]}
            (Path(directory) / 'profile.json').write_text(json.dumps(profile))
            spec['profile'] = 'profile.json'
            spec.pop('out_size')
            path.write_text(json.dumps(spec))
            loaded = core('spec').load_spec(path)
            self.assertEqual(loaded['fps'], 24)
            self.assertEqual(loaded['out_size'], [32, 32])
            self.assertEqual(loaded['mode'], 'rig')
            self.assertEqual(json.loads((Path(directory) / 'profile.json').read_text()), profile)

    def test_legacy_pant_list_adapter_renders_only_named_layers(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            Image.new('RGBA', (16, 16), (255, 0, 0, 255)).save(root / 'red.png')
            Image.new('RGBA', (16, 16), (0, 0, 255, 255)).save(root / 'blue.png')
            spec = {'parts': {'red': 'red.png', 'blue': 'blue.png'}, 'crop': [0, 0, 16, 16],
                    'height': 16, 'frames': [{'ms': 110, 'layers': [{'part': 'red'}]},
                                            {'ms': 210, 'layers': [{'part': 'blue'}]}]}
            path = root / 'pant.json'; path.write_text(json.dumps(spec))
            result = self.run_cli(path, '--out', root / 'pant')
            self.assertEqual(result.returncode, 0, result.stderr)
            for index, expected in enumerate([(255, 0, 0), (0, 0, 255)]):
                with Image.open(root / 'pant' / f'{index:05d}.png') as image:
                    self.assertEqual(image.getpixel((8, 8)), expected)
            self.assertEqual(json.loads((root / 'pant' / 'timing.json').read_text())['durations_ms'], [110, 210])

    def test_camera_consumes_pose_exposure_and_screen_world_effects(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            Image.new('RGBA', (32, 32), (100, 100, 100, 255)).save(root / 'base.png')
            sprite((32, 32), (8, 8, 23, 23), (240, 0, 0, 255)).save(root / 'pose.png')
            sprite((32, 32), (0, 0, 1, 31), (0, 0, 255, 255)).save(root / 'lines.png')
            spec = {'version': 1, 'mode': 'camera', 'canvas': [32, 32], 'out_size': [16, 16],
                    'parts': {'base': 'base.png', 'pose': 'pose.png', 'lines': 'lines.png'},
                    'layers': ['base'], 'shots': [{'frame_start': [0, 0, 32, 32], 'frames': 2,
                    'frame_ms': 40, 'exposure': [.5, 1], 'swap': [{'at': 0, 'part': 'pose'}],
                    'screen_effects': [{'part': 'lines'}], 'world_effects': []}]}
            path = root / 'camera.json'; path.write_text(json.dumps(spec))
            result = self.run_cli(path, '--out', root / 'camera')
            self.assertEqual(result.returncode, 0, result.stderr)
            with Image.open(root / 'camera' / '00000.png') as first, Image.open(root / 'camera' / '00001.png') as last:
                self.assertEqual(first.getpixel((8, 8)), (120, 0, 0))
                self.assertEqual(last.getpixel((8, 8)), (240, 0, 0))
                self.assertGreater(first.getpixel((0, 8))[2], 200, 'screen effects must follow exposure')

    def test_camera_rejects_unimplemented_legacy_punch_knob(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            Image.new('RGB', (16, 16), 'white').save(root / 'base.png')
            spec = {'version': 1, 'mode': 'camera', 'canvas': [16, 16], 'parts': {'base': 'base.png'},
                    'layers': ['base'], 'shots': [{'frame_start': [0, 0, 16, 16], 'frames': 2, 'punch': {'at': 'land'}}]}
            path = root / 'camera.json'; path.write_text(json.dumps(spec))
            result = self.run_cli(path, '--validate')
            self.assertNotEqual(result.returncode, 0)
            self.assertIn('punch', result.stderr)

    def test_camera_speedline_pulse_uses_only_lines_and_repeats(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            Image.new('RGBA', (16, 16), (90, 110, 130, 255)).save(root / 'base.png')
            line = Image.new('RGBA', (16, 16), 'white')
            for y in range(16): line.putpixel((8, y), (0, 0, 0, 255))
            line.save(root / 'line.png')
            spec = {'version': 1, 'mode': 'camera', 'fps': 30, 'canvas': [16, 16],
                    'parts': {'base': 'base.png', 'line': 'line.png'}, 'layers': ['base'],
                    'shots': [{'frame_start': [0, 0, 16, 16], 'frames': 17, 'frame_ms': 1000/30,
                    'screen_effects': [{'part': 'line', 'kind': 'speedline',
                                        'pulse': {'pulse_interval_sec': .5, 'visible_envelope_frames': [1]}}]}]}
            path = root / 'pulse.json'; path.write_text(json.dumps(spec))
            result = self.run_cli(path, '--out', root / 'pulse')
            self.assertEqual(result.returncode, 0, result.stderr)
            for index, color in [(0, (0, 0, 0)), (1, (90, 110, 130)), (15, (0, 0, 0))]:
                with Image.open(root / 'pulse' / f'{index:05d}.png') as frame:
                    self.assertEqual(frame.getpixel((8, 8)), color)
                    self.assertEqual(frame.getpixel((2, 8)), (90, 110, 130))

    def test_camera_alpha_survives_exposure_and_temporal_samples(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            sprite((16, 16), (4, 4, 11, 11), (200, 100, 50, 128)).save(root / 'part.png')
            spec = {'version': 1, 'mode': 'camera', 'canvas': [16, 16], 'preserve_alpha': True,
                    'bg': [0, 0, 0, 0], 'parts': {'part': 'part.png'}, 'layers': ['part'],
                    'shots': [{'frame_start': [0, 0, 16, 16], 'frames': 3,
                               'exposure': [.5, .5], 'motion_blur': True, 'blur_steps': 3}]}
            path = root / 'alpha.json'; path.write_text(json.dumps(spec))
            result = self.run_cli(path, '--out', root / 'alpha')
            self.assertEqual(result.returncode, 0, result.stderr)
            with Image.open(root / 'alpha' / '00001.png') as frame:
                self.assertEqual(frame.mode, 'RGBA')
                self.assertEqual(frame.getpixel((0, 0))[3], 0)
                self.assertEqual(frame.getpixel((8, 8)), (100, 50, 25, 128))

    def test_legacy_pant_transparent_background_preserves_alpha(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            sprite((16, 16), (4, 4, 11, 11), (200, 100, 50, 128)).save(root / 'part.png')
            spec = {'parts': {'part': 'part.png'}, 'bg': [0, 0, 0, 0], 'frames': [{'layers': [{'part': 'part'}]}]}
            path = root / 'pant.json'; path.write_text(json.dumps(spec))
            result = self.run_cli(path, '--out', root / 'pant')
            self.assertEqual(result.returncode, 0, result.stderr)
            with Image.open(root / 'pant' / '00000.png') as frame:
                self.assertEqual(frame.mode, 'RGBA')
                self.assertEqual(frame.getpixel((0, 0))[3], 0)

    def test_opaque_modes_reject_alpha_request_explicitly(self):
        spec = {'version': 1, 'mode': 'globe', 'land': 'not_used.png', 'preserve_alpha': True}
        with self.assertRaisesRegex(ValueError, 'alpha'):
            core('spec').validate_spec(spec, check_assets=False)


if __name__ == '__main__':
    unittest.main()
