"""Contracts written before factoring the supplied punch and mesh prototypes."""
import ast
import copy
import json
import math
import unittest

import cv2
import numpy as np
from PIL import Image, ImageDraw

from _support import SOURCES, SKILL, core, source_functions, sprite


def punch_fixture():
    cfg = json.loads((SOURCES / 'gpt' / 'punch_barrage_params.json').read_text())
    cfg['canvas'] = [64, 48]
    cfg['punch']['count'] = 4
    cfg['shoulders'] = {'L': [23, 22], 'R': [41, 22]}
    cfg['fists'] = [{'side': side, 'centroid': point} for side, point in
                    [('L', [42, 48]), ('R', [250, 149]), ('L', [37, 141]), ('R', [268, 38])]]
    body = sprite((64, 48), (18, 14, 47, 48), (190, 100, 65, 255))
    fists = [sprite((307, 173), (20, 20, 27, 29), color) for color in
             [(240, 40, 20, 255), (20, 190, 60, 255), (30, 50, 210, 255), (210, 70, 190, 255)]]
    lines = Image.new('RGBA', (64, 48), 'white')
    ImageDraw.Draw(lines).line((0, 0, 63, 47), fill='black', width=2)
    return body, fists, lines, cfg


def original_punch_frames(body, fists, lines, cfg):
    """Extract only the original rendering body; never run argparse or encoders."""
    source = SOURCES / 'gpt' / 'punch_barrage_speedline_topmost.py'
    parsed = ast.parse(source.read_text())
    helpers = source_functions('gpt', source.name,
                               ['clamp01', 'ease_in', 'ease_out', 'lerp',
                                'build_speedline_overlay', 'pulse_strength'],
                               {'np': np, 'Image': Image})
    env = dict(helpers.__dict__)
    env.update({'math': math, 'cfg': cfg, 'body': body, 'fist_srcs': fists,
                'w': cfg['canvas'][0], 'h': cfg['canvas'][1], 'fps': cfg['fps'],
                'speedline_rgba': helpers.build_speedline_overlay(lines, tuple(cfg['canvas']))})
    main = next(n for n in parsed.body if isinstance(n, ast.FunctionDef) and n.name == 'main')
    start = next(i for i, node in enumerate(main.body)
                 if isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id == 'punch_cfg' for t in node.targets))
    end = next(i for i, node in enumerate(main.body)
               if isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id == 'suffix' for t in node.targets))
    exec(compile(ast.Module(body=main.body[start:end], type_ignores=[]), str(source), 'exec'), env)
    return env['frames']


class PunchMigrationTests(unittest.TestCase):
    def test_original_renderer_fixture_runs_without_assets_or_side_effects(self):
        frames = original_punch_frames(*punch_fixture())
        self.assertEqual(len(frames), 21)
        self.assertTrue(all(f.mode == 'RGB' and f.size == (64, 48) for f in frames))

    def test_gpt_pixels_match_original_temporal_and_camera_formulas(self):
        inputs = punch_fixture()
        before = copy.deepcopy(inputs[-1])
        expected = original_punch_frames(*inputs)
        actual = core('punch').render_frames(*inputs)
        self.assertEqual(len(expected), len(actual))
        for i, (old, new) in enumerate(zip(expected, actual)):
            np.testing.assert_array_equal(np.asarray(new), np.asarray(old), err_msg=f'frame {i}')
        self.assertEqual(inputs[-1], before, 'renderer must not rewrite the input profile')

    def test_punch_does_not_remain_tiny_until_last_moment(self):
        # Claude source lines 48-49 identifies t**2.4 as the tiny-smudge failure.
        self.assertGreater(core('punch').ease_in(.5), .30)
        self.assertAlmostEqual(core('punch').ease_in(.5), .5 ** 1.65)

    def test_punch_profiles_keep_overlap_and_distinct_motion(self):
        heavy = json.loads((SKILL / 'presets' / 'punch_gpt_heavy.json').read_text())
        fast = json.loads((SKILL / 'presets' / 'punch_claude_machinegun.json').read_text())
        for cfg in (heavy, fast):
            self.assertLess(cfg['punch']['step_frames'], cfg['punch']['duration_frames'])
            self.assertEqual(cfg['motion_blur']['type'], 'temporal_substeps')
        self.assertLess(fast['punch']['step_frames'], heavy['punch']['step_frames'])
        self.assertLess(fast['punch']['duration_frames'], heavy['punch']['duration_frames'])
        self.assertLess(heavy['body']['max_horizontal_brace_px'], fast['body']['max_horizontal_brace_px'])

    def test_disabled_line_effect_does_not_require_an_asset(self):
        body, fists, lines, cfg = punch_fixture()
        cfg['speedline']['enabled'] = False
        actual = core('punch').render_frames(body, fists, None, cfg)
        blank = Image.new('RGBA', lines.size, 'white')
        expected = original_punch_frames(body, fists, blank, cfg)
        for a, b in zip(actual, expected):
            np.testing.assert_array_equal(a, b)


class MeshAndTimingMigrationTests(unittest.TestCase):
    def test_absolute_fractional_boundaries_do_not_drift(self):
        count, bpm, fps = 1000, 189.9, 30
        step = 60 / bpm * 2 * fps
        expected = [round(k * step) for k in range(count + 1)]
        self.assertEqual(core('beat_grid').boundaries(count, bpm, fps), expected)
        self.assertLessEqual(abs(expected[-1] - count * step), .5)
        self.assertNotEqual(expected[-1], count * round(step))

    def test_mesh_pixels_match_original_row_warp(self):
        foot, top, height, width = 50, 6, 64, 48
        yy, xx = np.indices((height, width), dtype=np.float32)
        source = source_functions('gpt', 'mesh_dance_test.py', ['warp_rgba'],
                                  {'np': np, 'cv2': cv2, 'FOOT_Y': foot, 'TOP_Y': top,
                                   'YY': yy, 'XX': xx})
        arr = np.asarray(sprite((width, height), (12, top, 30, foot)))
        for kwargs in ({}, {'sway': 8, 'sy': .98, 'bend': -4}, {'sway': -10, 'sy': 1.02, 'bend': 5}):
            actual = core('mesh_warp').warp_rgba(arr, foot, top, **kwargs)
            expected = source.warp_rgba(arr, **kwargs)
            np.testing.assert_array_equal(actual, expected)

    def test_foot_baseline_stays_fixed(self):
        arr = np.zeros((64, 48, 4), dtype=np.uint8)
        arr[50, 20] = [220, 30, 20, 255]
        warped = core('mesh_warp').warp_rgba(arr, 50, 6, sway=12, sy=1.025, bend=-8)
        np.testing.assert_array_equal(warped[50, 20], arr[50, 20])

    def test_motion_presets_match_original_and_breathing_stays_subtle(self):
        old = source_functions('gpt', 'mesh_dance_test.py', ['bump', 'gauss', 'motion_params'], {'math': math})
        new = core('mesh_warp')
        for preset in ('shakeR', 'shakeL', 'clapR', 'clapL', 'cross', 'pulse', 'breathe',
                       'pop', 'leanR', 'leanL', 'reachR', 'reachL', 'final', 'waveR', 'waveL'):
            for phase in (0, .17, .25, .51, 1):
                self.assertEqual(new.motion_params(preset, phase), old.motion_params(preset, phase))
        breath = new.motion_params('breathe', .25)
        self.assertEqual(breath['sway'], 1)
        self.assertAlmostEqual(breath['sy'], 1.009)

    def test_alignment_preserves_horizontal_layout_and_relative_pose_size(self):
        images = [sprite((48, 64), (3, 10, 9, 50)), sprite((48, 64), (28, 20, 42, 52))]
        aligned, foot, top = core('mesh_warp').align_poses(images, (48, 64))
        self.assertEqual(foot, 51)
        self.assertEqual(top, 15)
        for arr, expected in zip(aligned, [(3, 9), (28, 42)]):
            yy, xx = np.where(arr[:, :, 3] > 10)
            self.assertEqual((int(xx.min()), int(xx.max())), expected)
            self.assertEqual(int(yy.max()), foot)

    def test_pose_swaps_are_hard_cuts(self):
        red = Image.new('RGBA', (16, 16), (255, 0, 0, 255))
        blue = Image.new('RGBA', (16, 16), (0, 0, 255, 255))
        frames = core('mesh_warp').render_sequence(
            [red, blue], [(1, 'none', 1), (2, 'none', 1)],
            size=(16, 16), bpm=60, fps=2, beats_per_pose=1)
        self.assertEqual([f.getpixel((8, 8)) for f in frames],
                         [(255, 0, 0), (255, 0, 0), (0, 0, 255), (0, 0, 255)])


if __name__ == '__main__':
    unittest.main()
