import copy
import hashlib
import tempfile
import unittest
from pathlib import Path
import numpy as np
from PIL import Image
from _support import core, sprite


class RenderGuardTests(unittest.TestCase):
    def test_transparent_rig_png_retains_alpha_through_temporal_blur(self):
        r = core('rig_tree')
        with tempfile.TemporaryDirectory() as d:
            path = Path(d)
            sprite(box=(8, 8, 12, 12), color=(255, 0, 0, 255)).save(path / 'a.png')
            spec = {'base_dir': d, 'out_size': [64, 64], 'bg': [0, 0, 0, 0],
                    'parts': {'a': {'file': 'a.png', 'pivot': [0, 0], 'z': 0}},
                    'frames': [{'layers': {}, 'camera': [0, 0, 64, 64], 'substeps': [{'a': {'dx': 0}}, {'a': {'dx': 16}}]}]}
            frames, _ = r.render(spec, path / 'frames')
            self.assertEqual(frames[0].mode, 'RGBA')
            self.assertEqual(frames[0].getpixel((0, 0))[3], 0)
            self.assertEqual(frames[0].getpixel((10, 10)), (255, 0, 0, 127))
            with Image.open(path / 'frames' / '00000.png') as saved:
                self.assertEqual(saved.mode, 'RGBA')

    def test_guides_excluded_without_deleting_red_art(self):
        r = core('rig_tree')
        parts = {'art': {'pivot': [0, 0], 'z': 1}, 'guide': {'pivot': [0, 0], 'z': 100, 'role': 'guide'}}
        art = sprite(color=(240, 0, 0, 255))
        images = {'art': art, 'guide': Image.new('RGBA', art.size, (0, 255, 0, 255))}
        canvas, _ = r.compose_frame(parts, images, {}, bg=(255, 255, 255, 255))
        self.assertEqual(canvas.getpixel((30, 30)), (240, 0, 0, 255))
        self.assertEqual(canvas.getpixel((0, 0)), (255, 255, 255, 255))

    def test_substeps_retain_base_visibility(self):
        r = core('rig_tree')
        with tempfile.TemporaryDirectory() as d:
            p = Path(d)
            sprite().save(p / 'a.png')
            spec = {'base_dir': d, 'out_size': [64, 64], 'parts': {'a': {'file': 'a.png', 'pivot': [0, 0], 'z': 0}}, 'frames': [{'layers': {'a': {'visible': False}}, 'camera': [0, 0, 64, 64], 'substeps': [{'a': {'dx': 1}}, {'a': {'dx': 2}}]}]}
            frames, _ = r.render(spec, None)
            self.assertTrue(np.all(np.asarray(frames[0]) == 255))

    def test_original_assets_unchanged_and_missing_asset_fails(self):
        r = core('rig_tree')
        with tempfile.TemporaryDirectory() as d:
            p = Path(d)
            sprite().save(p / 'a.png')
            before = hashlib.sha256((p / 'a.png').read_bytes()).hexdigest()
            spec = {'base_dir': d, 'out_size': [64, 64], 'parts': {'a': {'file': 'a.png', 'pivot': [0, 0], 'z': 0}}, 'frames': [{'layers': {}, 'camera': [0, 0, 64, 64]}]}
            r.render(spec, None)
            self.assertEqual(hashlib.sha256((p / 'a.png').read_bytes()).hexdigest(), before)
            spec['parts']['a']['file'] = 'missing.png'
            with self.assertRaises(FileNotFoundError):
                r.render(spec, None)

    def test_explicit_anchor_alignment_and_projected_diagnostics(self):
        r = core('rig_tree')
        parts = {'a': {'pivot': [0, 0], 'z': 0, 'anchors': {'wrist': [10, 20]}}}
        layers = {'a': {'turn': {'axis_x': 0, 'axis_y': 0, 'theta': 45, 'focal': 130}}}
        expected = r.turn_matrix(0, 0, 45, 130) @ np.array([10, 20, 1])
        np.testing.assert_allclose(r.anchor_world(parts, layers, 'a', 'wrist', projected=True), expected[:2] / expected[2])
        aligned = r.align_anchor(parts, {}, 'a', 'wrist', [30, 35])
        np.testing.assert_allclose(r.anchor_world(parts, aligned, 'a', 'wrist'), [30, 35], atol=.25)
