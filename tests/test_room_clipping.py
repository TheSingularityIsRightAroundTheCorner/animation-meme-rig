"""Visible wall portions must survive crossing the camera's near plane."""
from pathlib import Path
import tempfile
import unittest

import numpy as np
from PIL import Image
from _support import core, original


class RoomClippingRegressionTests(unittest.TestCase):
    def setUp(self):
        self.room = core('stadium3d')
        self.rotation, self.eye = self.room.look_at((0, 0, 0), (0, 0, -1))

    def draw(self, quad, texture=None):
        canvas = Image.new('RGBA', (96, 64))
        texture = texture or Image.new('RGBA', (32, 32), (40, 100, 210, 255))
        self.room.draw_quad(canvas, texture, quad, self.rotation, self.eye, 52)
        return np.asarray(canvas)

    def test_wall_crossing_near_plane_keeps_its_visible_portion(self):
        quad = [(1, 2, 1), (1, 2, -4), (1, -2, -4), (1, -2, 1)]
        image = self.draw(quad)
        np.testing.assert_array_equal(image[32, 90], (40, 100, 210, 255))
        self.assertEqual(image[32, 20, 3], 0, 'the wall must not wrap behind the eye')

    def test_corner_on_camera_plane_is_finite_and_still_visible(self):
        image = self.draw([(1, 2, 0), (1, 2, -4), (1, -2, -4), (1, -2, 0)])
        np.testing.assert_array_equal(image[32, 90], (40, 100, 210, 255))

    def test_one_visible_corner_matches_independent_ray_plane_intersections(self):
        quad = np.array([[-.3, .3, 2], [.3, .3, .5], [.3, -.3, -1], [-.3, -.3, .5]])
        image = self.draw(quad)
        origin, u, v = quad[0], quad[1]-quad[0], quad[3]-quad[0]
        focal = 32 / np.tan(np.deg2rad(52) / 2)
        visible = 0
        for y in range(3, 64, 5):
            for x in range(3, 96, 5):
                ray = np.array([(x+.5-48)/focal, -(y+.5-32)/focal, -1])
                a, b, depth = np.linalg.solve(np.column_stack((u, v, -ray)), -origin)
                if .04 < a < .96 and .04 < b < .96 and depth > .06:
                    visible += 1
                    self.assertEqual(image[y, x, 3], 255, (x, y, a, b, depth))
                elif a < -.04 or a > 1.04 or b < -.04 or b > 1.04 or depth < -.01:
                    self.assertEqual(image[y, x, 3], 0, (x, y, a, b, depth))
        self.assertGreater(visible, 4)

    def test_clipped_wall_preserves_texture_direction_and_alpha(self):
        texture = np.zeros((32, 32, 4), np.uint8)
        texture[..., 0] = np.arange(32, dtype=np.uint8)[None, :] * 7
        texture[..., 1] = np.arange(32, dtype=np.uint8)[:, None] * 7
        texture[..., 3] = 128
        image = self.draw([(1, 2, 1), (1, 2, -4), (1, -2, -4), (1, -2, 1)], Image.fromarray(texture))
        self.assertEqual(image[32, 90, 3], 128)
        self.assertGreater(image[32, 70, 0], image[32, 90, 0])
        self.assertGreater(image[45, 90, 1], image[20, 90, 1])

    def test_fully_front_quad_keeps_original_pixels(self):
        old = original('claude', 'stadium3d.py')
        data = np.random.default_rng(37).integers(0, 256, (32, 32, 4), dtype=np.uint8)
        texture = Image.fromarray(data)
        quad = [(-1, 1, -4), (1, 1, -3), (1, -1, -3), (-1, -1, -4)]
        canvas = Image.new('RGBA', (96, 64))
        old.draw_quad(canvas, texture, quad, self.rotation, self.eye, 52)
        np.testing.assert_array_equal(self.draw(quad, texture), canvas)

    def test_fully_behind_wall_remains_invisible(self):
        image = self.draw([(-1, 1, 2), (1, 1, 2), (1, -1, 2), (-1, -1, 2)])
        self.assertFalse(image.any())

    def test_closed_view_of_room_needs_no_slicing_to_keep_both_side_walls(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            colors = {'far': (220, 40, 40), 'left': (40, 200, 50), 'right': (40, 60, 220),
                      'near': (210, 200, 40), 'floor': (180, 140, 80)}
            sheet = Image.new('RGB', (50, 10))
            panels = {}
            for i, (key, color) in enumerate(colors.items()):
                box = [i*10, 0, (i+1)*10, 10]
                sheet.paste(color, box); panels[key] = {'box': box}
            sheet.save(root/'sheet.png')
            Image.new('RGBA', (8, 8)).save(root/'pose.png')
            camera = {'eye': [.9, 2.5, 3.4], 'target': [-.5, 1.9, -11], 'fov': 44}
            spec = {'panel_sheet': 'sheet.png', 'panels': panels, 'pose_files': ['pose.png'],
                    'room': {'width': 16, 'depth': 24, 'height': 9}, 'out_size': [192, 108],
                    'frames': 2, 'camera_start': camera, 'camera_end': camera,
                    'camera_bob': 0, 'slices': 1, 'background': [255, 0, 255, 255]}
            for frame in self.room.render_frames(spec, root):
                rgb = np.asarray(frame)
                for name in ('left', 'right'):
                    self.assertGreater(np.all(rgb == colors[name], axis=2).sum(), 100, name)
                self.assertLess(np.all(rgb == (255, 0, 255), axis=2).sum(), 20)


if __name__ == '__main__':
    unittest.main()
