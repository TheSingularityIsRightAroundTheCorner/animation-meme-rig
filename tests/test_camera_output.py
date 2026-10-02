import json
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw
from _support import core, original, SOURCES


class CameraRegressionTests(unittest.TestCase):
    def test_exact_start_end_camera(self):
        c = core('camera_25d')
        p = json.loads((SOURCES / 'gpt' / 'run25d_camera_box_params.json').read_text())
        for progress, expected in [(0, p['camera_start']), (1, p['camera_end'])]:
            actual = c.camera_at(p['camera_start'], p['camera_end'], progress)
            for key in ('eye', 'target', 'fov'):
                np.testing.assert_allclose(actual[key], expected[key], atol=1e-12)

    def test_billboard_pose_hard_swap_schedule(self):
        c = core('camera_25d')
        schedule = [{'at': 0, 'part': 'pose1'}, {'at': .4, 'part': 'pose2'}, {'at': .72, 'part': 'pose3'}]
        for progress, pose in [(0, 'pose1'), (.399, 'pose1'), (.4, 'pose2'), (.719, 'pose2'), (.72, 'pose3'), (1, 'pose3')]:
            self.assertEqual(c.pose_at(schedule, progress), pose)

    def test_frame_guide_measured_and_canvas_mismatch_rejected(self):
        c = core('camera_25d')
        im = Image.new('RGBA', (320, 180), (0, 0, 0, 0))
        ImageDraw.Draw(im).rectangle((40, 30, 199, 119), fill=(0, 0, 255, 90))
        np.testing.assert_allclose(c.measure_frame(im, (320, 180), color='blue'), (40, 30, 200, 120))
        with self.assertRaises(ValueError):
            c.measure_frame(im, (640, 360), color='blue')

    def test_crop_outside_canvas_rejected_no_black_border(self):
        c = core('camera_25d')
        im = Image.new('RGB', (64, 64), (100, 150, 200))
        with self.assertRaises(ValueError):
            c.crop_frame(im, (-1, 0, 65, 64), (64, 64))
        np.testing.assert_array_equal(np.asarray(c.crop_frame(im, (0, 0, 64, 64), (32, 32))), np.full((32, 32, 3), [100, 150, 200], np.uint8))

    def test_explicit_panel_mapping_tan_floor_not_crowd(self):
        s = core('stadium3d')
        with tempfile.TemporaryDirectory() as directory:
            sheet = Image.new('RGB', (50, 10))
            colors = {'far': (250, 0, 0), 'left': (0, 250, 0), 'floor': (180, 140, 80), 'right': (200, 0, 200), 'near': (0, 90, 240)}
            panels = {}
            for i, (name, color) in enumerate(colors.items()):
                box = [i * 10, 0, (i + 1) * 10, 10]
                ImageDraw.Draw(sheet).rectangle((box[0], box[1], box[2] - 1, box[3] - 1), fill=color)
                panels[name] = box
            path = Path(directory) / 'sheet.png'
            sheet.save(path)
            loaded = s.load_panels(path, panels)
            for name, color in colors.items():
                self.assertEqual(loaded[name].convert('RGB').getpixel((5, 5)), color)
            with self.assertRaises((ValueError, TypeError)):
                s.load_panels(path, {})

    def test_floor_strips_retain_visible_floor_crossing_near_plane(self):
        s = core('stadium3d')
        R, eye = s.look_at((0, 2, 0), (0, 1, -4))
        quad = [(-3, 0, 1), (3, 0, 1), (3, 0, -8), (-3, 0, -8)]
        tex = Image.new('RGBA', (64, 64), (180, 140, 80, 255))
        canvas = Image.new('RGBA', (64, 64), (0, 0, 0, 0))
        for part, crop in s.strips(quad, tex, n=16, axis=1):
            s.draw_quad(canvas, crop, part, R, eye, 52)
        self.assertGreater(np.count_nonzero(np.asarray(canvas)[..., 3]), 150)

    def test_billboard_always_faces_camera(self):
        s = core('stadium3d')
        for eye in ((0, 2, 8), (6, 3, 4), (-4, 2, 6)):
            R, E = s.look_at(eye, (0, 1, 0))
            quad = np.asarray(s.billboard((0, 1, 0), 2, .5, R))
            camera_points = (quad - E) @ R.T
            self.assertLess(np.ptp(camera_points[:, 2]), 1e-10)
            self.assertAlmostEqual(np.linalg.norm(quad[1] - quad[0]), 1)


class OutputRegressionTests(unittest.TestCase):
    def test_rgb_png_output(self):
        o = core('output')
        frames = [Image.new('RGB', (32, 32), (33, 91, 172))]
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'out.png'
            o.save_frames(frames, path)
            im = Image.open(path)
            self.assertEqual(im.mode, 'RGB')
            self.assertEqual(im.getpixel((0, 0)), (33, 91, 172))

    @unittest.skipUnless(shutil.which('ffmpeg'), 'ffmpeg executable absent; install to enable MP4 verification')
    def test_mp4_decodable_rgb_path(self):
        o = core('output')
        frames = [Image.new('RGB', (32, 32), (30 + i * 40, 90, 170)) for i in range(3)]
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'out.mp4'
            o.save_frames(frames, path, fps=10)
            self.assertGreater(path.stat().st_size, 0)
            result = subprocess.run(['ffmpeg', '-v', 'error', '-i', str(path), '-f', 'null', '-'], capture_output=True)
            self.assertEqual(result.returncode, 0, result.stderr)
