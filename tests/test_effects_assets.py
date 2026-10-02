import tempfile
import unittest
import unicodedata
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw
from _support import core, original, sprite


class EffectsRegressionTests(unittest.TestCase):
    def test_alpha_only_black_rgb_lines_do_not_blackout_screen(self):
        e = core('effects')
        lines = sprite(box=(30, 0, 32, 63), color=(0, 0, 0, 255))
        overlay = Image.fromarray(e.build_speedline_overlay(lines, (64, 64)))
        result = e.composite_effect(Image.new('RGBA', (64, 64), (210, 160, 90, 255)), overlay)
        self.assertEqual(result.getpixel((0, 0)), (210, 160, 90, 255))
        self.assertEqual(result.getpixel((31, 31)), (0, 0, 0, 255))

    def test_speedline_topmost_covers_fist(self):
        e = core('effects')
        canvas = Image.new('RGBA', (64, 64), (255, 255, 255, 255))
        canvas.alpha_composite(sprite())
        lines = sprite(box=(30, 0, 32, 63), color=(0, 0, 0, 255))
        result = e.composite_effect(canvas, lines)
        self.assertEqual(result.getpixel((31, 30)), (0, 0, 0, 255))
        self.assertEqual(result.getpixel((25, 30)), (220, 40, 30, 255))

    def test_line_pulse_changes_only_effect_pixels_no_fullscreen_flash(self):
        e = core('effects')
        base = Image.new('RGBA', (64, 64), (83, 103, 123, 255))
        line = sprite(box=(30, 0, 32, 63), color=(0, 0, 0, 255))
        for strength in (0, .25, 1):
            result = e.composite_effect(base, line, strength=strength)
            np.testing.assert_array_equal(np.asarray(result)[:, :30], np.asarray(base)[:, :30])
            np.testing.assert_array_equal(np.asarray(result)[:, 33:], np.asarray(base)[:, 33:])

    def test_pulse_half_second_envelope_and_disabled(self):
        e = core('effects')
        cfg = {'enabled': True, 'pulse_interval_sec': .5, 'visible_envelope_frames': [.25, .75, 1, .55, .18]}
        values = [e.pulse_strength(i, 30, cfg) for i in range(31)]
        self.assertEqual(values[:5], cfg['visible_envelope_frames'])
        self.assertEqual(values[5:15], [0] * 10)
        self.assertEqual(values[:15], values[15:30])
        cfg['enabled'] = False
        self.assertEqual([e.pulse_strength(i, 30, cfg) for i in range(31)], [0] * 31)

    def test_effect_independent_disable(self):
        e = core('effects')
        im = sprite()
        np.testing.assert_array_equal(np.asarray(e.composite_effect(im, Image.new('RGBA', im.size, 'white'), enabled=False)), np.asarray(im))

    def test_screen_glass_preserves_underlying_detail(self):
        e = core('effects')
        base = Image.new('RGBA', (2, 1), (20, 40, 60, 255))
        base.putpixel((1, 0), (100, 120, 140, 255))
        glass = Image.new('RGBA', (2, 1), (170, 190, 210, 255))
        result = e.composite_effect(base, glass, mode='screen')
        a, b = np.array(result)[0, 0, :3], np.array(result)[0, 1, :3]
        self.assertTrue(np.all(b > a))
        self.assertTrue(np.all(a >= np.array([20, 40, 60])))

    def test_multiply_transparent_regions_and_internal_whites(self):
        e = core('effects')
        base = Image.new('RGBA', (64, 64), (100, 150, 200, 255))
        result = e.composite_effect(base, sprite(box=(30, 0, 32, 63), color=(0, 0, 0, 255)), mode='multiply')
        self.assertEqual(result.getpixel((0, 0)), base.getpixel((0, 0)))
        self.assertEqual(result.getpixel((31, 30)), (0, 0, 0, 255))

    def test_lens_fill_closes_white_holes_without_bridging_lenses(self):
        e = core('effects')
        mask = np.zeros((12, 32), np.uint8)
        mask[3:9, 2] = 255; mask[3:9, 11] = 255
        mask[3:9, 20] = 255; mask[3:9, 29] = 255
        result = np.asarray(e.fill_lens_mask(Image.fromarray(mask), split_x=16))
        self.assertTrue(np.all(result[3:9, 2:12] == 255))
        self.assertTrue(np.all(result[3:9, 20:30] == 255))
        self.assertTrue(np.all(result[:, 12:20] == 0))

    def test_line_width_compensates_camera_zoom(self):
        e = core('effects')
        for zoom in (1.4, 2.3, 3):
            self.assertAlmostEqual(e.scaled_line_width(4, zoom) * zoom, 4)

    def test_original_speedline_pixels_and_timing_golden(self):
        e, old = core('effects'), original('gpt', 'punch_barrage_speedline_topmost.py')
        im = sprite(box=(4, 5, 10, 20), color=(25, 25, 25, 150))
        np.testing.assert_array_equal(e.build_speedline_overlay(im, (48, 48)), old.build_speedline_overlay(im, (48, 48)))
        for i in range(45):
            self.assertEqual(e.pulse_strength(i, 30, {}), old.pulse_strength(i, 30, {}))


class AssetRegressionTests(unittest.TestCase):
    def test_canvas_mismatch_rejected(self):
        with self.assertRaises((ValueError, AssertionError)):
            core('assets').validate_canvases({'one': Image.new('RGBA', (64, 64)), 'two': Image.new('RGBA', (32, 64))})

    def test_unicode_nfd_asset_name_resolves(self):
        a = core('assets')
        with tempfile.TemporaryDirectory() as directory:
            name = '그림.png'
            stored = Path(directory) / unicodedata.normalize('NFD', name)
            sprite().save(stored)
            self.assertEqual(Path(a.resolve_asset(directory, name)), stored)

    def test_edge_white_removal_keeps_enclosed_eye_white(self):
        a = core('assets')
        im = Image.new('RGBA', (32, 32), 'white')
        draw = ImageDraw.Draw(im)
        draw.rectangle((6, 6, 25, 25), fill=(20, 20, 20, 255))
        draw.rectangle((12, 12, 19, 19), fill='white')
        result = a.remove_edge_white(im)
        self.assertEqual(result.getpixel((0, 0))[3], 0)
        self.assertEqual(result.getpixel((15, 15)), (255, 255, 255, 255))
        self.assertEqual(result.getpixel((7, 7)), (20, 20, 20, 255))

    def test_border_stripe_and_missing_part_diagnostics(self):
        qa = core('qa')
        im = Image.new('RGB', (64, 64), (100, 100, 100))
        self.assertFalse(qa.inspect_frame(im))
        border = im.copy()
        ImageDraw.Draw(border).rectangle((0, 0, 2, 63), fill='black')
        self.assertIn('border', {item['code'] for item in qa.inspect_frame(border)})
        stripe = im.copy()
        ImageDraw.Draw(stripe).line((0, 32, 63, 32), fill='white')
        self.assertIn('stripe', {item['code'] for item in qa.inspect_frame(stripe)})
        empty = Image.new('RGBA', (64, 64), (0, 0, 0, 0))
        self.assertIn('missing_part', {item['code'] for item in qa.inspect_parts({'a': empty}, {})})
        self.assertNotIn('missing_part', {item['code'] for item in qa.inspect_parts({'a': empty}, {'a': {'visible': False}})})

    def test_edge_bound_part_upward_motion_is_detected(self):
        r, qa = core('rig_tree'), core('qa')
        im = Image.new('RGBA', (64, 64), (100, 100, 100, 255))
        parts = {'a': {'pivot': [0, 0], 'z': 0}}
        canvas, _ = r.compose_frame(parts, {'a': im}, {'a': {'dy': -4}}, bg=(255, 255, 255, 255))
        self.assertIn('border', {item['code'] for item in qa.inspect_frame(canvas)})
