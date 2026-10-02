import copy
import json
import tempfile
import unittest
from pathlib import Path
import numpy as np
from PIL import Image
from _support import core, original, project, sprite, tree, SOURCES


class RigRegressionTests(unittest.TestCase):
    def test_parent_translation_inheritance(self):
        m = core('rig_tree').world_matrices(tree(), {'root': {'dx': 7, 'dy': -3}})
        np.testing.assert_allclose(project(m['arm'], (28, 24)), (35, 21))
        np.testing.assert_allclose(m['arm'], m['claw'])

    def test_parent_rotation_and_nested_inheritance(self):
        m = core('rig_tree').world_matrices(tree(), {'root': {'rot': 90}, 'arm': {'dx': 4}})
        np.testing.assert_allclose(project(m['arm'], (28, 24)), (24, 32), atol=1e-10)
        np.testing.assert_allclose(m['claw'], m['arm'])

    def test_cycle_rejected(self):
        parts = tree()
        parts['root']['parent'] = 'claw'
        with self.assertRaisesRegex(ValueError, 'cycle'):
            core('rig_tree').world_matrices(parts, {})

    def test_frame_parent_override_and_detach(self):
        r = core('rig_tree')
        layers = {'root': {'dx': 10}, 'catch': {'dy': 20}, 'arm': {'parent': 'catch'}}
        m = r.world_matrices(tree(), layers)
        np.testing.assert_allclose(project(m['claw'], (40, 30)), (40, 50))
        layers['arm']['parent'] = None
        m = r.world_matrices(tree(), layers)
        np.testing.assert_allclose(m['claw'], np.eye(3))

    def test_reparent_preserves_world_pose_and_descendants(self):
        r = core('rig_tree')
        parts = tree()
        layers = {'root': {'rot': 23, 'sx': 1.3}, 'arm': {'rot': -17, 'sy': .7, 'dx': 9}, 'catch': {'rot': -32, 'sx': .8, 'sy': 1.2, 'dy': 8}}
        saved = copy.deepcopy(layers)
        before = r.world_matrices(parts, layers)
        changed = r.reparent_layers(parts, layers, 'arm', 'catch')
        after = r.world_matrices(parts, changed)
        self.assertEqual(layers, saved, 'reparent must not mutate caller state')
        for name in ('arm', 'claw'):
            np.testing.assert_allclose(after[name], before[name], atol=1e-9)
        changed['catch']['dx'] = changed['catch'].get('dx', 0) + 6
        moved = r.world_matrices(parts, changed)
        delta = project(moved['claw'], (40, 30)) - project(after['claw'], (40, 30))
        self.assertGreater(np.linalg.norm(delta), 1)

    def test_detach_reattach_preserves_pose(self):
        r = core('rig_tree')
        parts, layers = tree(), {'root': {'dx': 8, 'rot': 16}, 'arm': {'sy': .8}}
        expected = r.world_matrices(parts, layers)
        detached = r.reparent_layers(parts, layers, 'arm', None)
        reattached = r.reparent_layers(parts, detached, 'arm', 'root')
        for result in (detached, reattached):
            np.testing.assert_allclose(r.world_matrices(parts, result)['claw'], expected['claw'], atol=1e-9)

    def test_joint_anchor_error_below_quarter_pixel(self):
        r = core('rig_tree')
        parts = tree()
        for rot in (-45, 0, 37):
            layers = {'root': {'rot': rot, 'dx': 2, 'dy': 7}}
            a = r.anchor_world(parts, layers, 'root', 'joint')
            b = r.anchor_world(parts, layers, 'arm', 'joint')
            self.assertLess(np.linalg.norm(np.asarray(a) - b), .25)

    def test_knuckle_extension_does_not_drift_anchor(self):
        r = core('rig_tree')
        for growth in (.02, .3, .6, 1):
            m = r.local_matrix((40, 30), {'sy': growth})
            np.testing.assert_allclose(project(m, (40, 30)), (40, 30))
            self.assertAlmostEqual(project(m, (40, 50))[1], 30 + 20 * growth)

    def test_signed_near_far_perspective_and_axis(self):
        r = core('rig_tree')
        for theta in (45, -45):
            m = r.turn_matrix(32, 24, theta, 130)
            np.testing.assert_allclose(project(m, (32, 24)), (32, 24))
            left = np.linalg.norm(project(m, (8, 44)) - project(m, (8, 24)))
            right = np.linalg.norm(project(m, (56, 44)) - project(m, (56, 24)))
            self.assertGreater(left, right) if theta > 0 else self.assertGreater(right, left)
        a = r.turn_matrix(32, 24, 45, 130)
        b = r.turn_matrix(32, 24, -45, 130)
        self.assertGreater(np.linalg.norm(project(a, (8, 44)) - project(b, (8, 44))), 1)

    def test_side_view_transition_anchor_alignment(self):
        r = core('rig_tree')
        front = r.turn_matrix(24, 12, 45, 130)
        side = r.local_matrix((50, 14), {'dx': -26, 'dy': -2})
        np.testing.assert_allclose(project(front, (24, 12)), project(side, (50, 14)), atol=.25)

    def test_render_z_crossing_and_transparent_png(self):
        r = core('rig_tree')
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)
            sprite(color=(255, 0, 0, 255)).save(path / 'a.png')
            sprite(color=(0, 0, 255, 255)).save(path / 'b.png')
            spec = {'base_dir': str(path), 'out_size': [64, 64], 'bg': [250, 250, 250, 255],
                    'parts': {'a': {'file': 'a.png', 'pivot': [0, 0], 'z': 0}, 'b': {'file': 'b.png', 'pivot': [0, 0], 'z': 1}},
                    'frames': [{'layers': {}, 'camera': [0, 0, 64, 64]}, {'layers': {'a': {'z': 2}}, 'camera': [0, 0, 64, 64]}]}
            frames, _ = r.render(spec, path / 'depth.gif')
            self.assertEqual(frames[0].getpixel((30, 30)), (0, 0, 255))
            self.assertEqual(frames[1].getpixel((30, 30)), (255, 0, 0))
            self.assertEqual(frames[0].getpixel((0, 0)), (250, 250, 250))

    def test_temporal_substeps_follow_motion_without_spatial_halo(self):
        r = core('rig_tree')
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)
            sprite(box=(8, 24, 12, 28), color=(255, 0, 0, 255)).save(path / 'a.png')
            spec = {'base_dir': str(path), 'out_size': [64, 64], 'bg': [255, 255, 255, 255],
                    'parts': {'a': {'file': 'a.png', 'pivot': [0, 0], 'z': 0}},
                    'frames': [{'layers': {}, 'substeps': [{'a': {'dx': 0}}, {'a': {'dx': 16}}], 'camera': [0, 0, 64, 64]}]}
            frames, _ = r.render(spec, path / 'blur.gif')
            im = frames[0]
            for x in (10, 26):
                self.assertEqual(im.getpixel((x, 26)), (255, 127, 127))
            self.assertEqual(im.getpixel((10, 20)), (255, 255, 255))
            self.assertEqual(im.getpixel((18, 26)), (255, 255, 255))

    def test_original_affine_and_perspective_golden(self):
        r, old = core('rig_tree'), original('claude', 'rig_tree.py')
        for theta in (-45, 0, 32):
            np.testing.assert_allclose(r.turn_matrix(24, 12, theta, 130), old.turn_matrix(24, 12, theta, 130))
            tr = {'rot': theta, 'dx': 3, 'dy': -2, 'sx': .7, 'sy': 1.3}
            np.testing.assert_allclose(r.local_matrix((24, 12), tr), old.local_matrix((24, 12), tr))
            im = sprite()
            np.testing.assert_array_equal(np.asarray(r.apply_homography(im, r.local_matrix((24, 12), tr))), np.asarray(old.apply_homography(im, old.local_matrix((24, 12), tr))))

    def test_original_rgba_scene_pixels_include_parent_and_substeps(self):
        r, old = core('rig_tree'), original('claude', 'rig_tree.py')
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)
            sprite(box=(8, 10, 30, 50), color=(200, 60, 40, 190)).save(path / 'body.png')
            sprite(box=(20, 15, 35, 28), color=(40, 100, 210, 140)).save(path / 'arm.png')
            first = {'body': {'rot': 9, 'dx': 2}, 'arm': {'rot': -12, 'dy': 3}}
            second = {'body': {'rot': 12, 'dx': 4}, 'arm': {'rot': -7, 'dy': 5}}
            spec = {'base_dir': str(path), 'out_size': [48, 48], 'bg': [240, 230, 220, 255],
                    'parts': {'body': {'file': 'body.png', 'pivot': [24, 24], 'z': 0},
                              'arm': {'file': 'arm.png', 'pivot': [25, 20], 'parent': 'body', 'z': 1}},
                    'frames': [{'layers': first, 'camera': [4, 4, 60, 60]},
                               {'layers': second, 'substeps': [first, second], 'camera': [4, 4, 60, 60]}]}
            expected, _ = old.render(spec, path / 'original.gif')
            actual, _ = r.render(spec, None)
            for a, b in zip(actual, expected):
                np.testing.assert_array_equal(np.asarray(a), np.asarray(b))

    def test_supplied_probe_logs_affine_only(self):
        r = core('rig_tree')
        for stem in ('cut37_parent_child_force_v3', 'claw_turn_knuckle_rig'):
            spec = json.loads((SOURCES / 'gpt' / (stem + '_spec.json')).read_text())
            expected = json.loads((SOURCES / 'gpt' / (stem + '_probe.json')).read_text())
            self.assertEqual(len(spec['frames']), len(expected))
            for frame, log in zip(spec['frames'], expected):
                matrices = r.world_matrices(spec['parts'], frame.get('layers', {}))
                for probe in spec['probes']:
                    for part in probe['parts']:
                        point = project(matrices[part], probe['point'])
                        actual = [round(float(v), 1) for v in point]
                        self.assertEqual(actual, log[probe['name'] + '@' + part])

    def test_contact_force_transmitted_without_independent_child_command(self):
        r = core('rig_tree')
        spec = json.loads((SOURCES / 'gpt' / 'cut37_parent_child_force_v3_spec.json').read_text())
        rows = []
        for frame in spec['frames'][17:]:
            matrices = r.world_matrices(spec['parts'], frame['layers'])
            a = project(matrices['gpt_catch_arm'], (245, 265))
            b = project(matrices['claude_arm_attack'], (245, 265))
            self.assertLess(np.linalg.norm(a-b), .25)
            np.testing.assert_allclose(matrices['claw_end_3'], matrices['claude_arm_attack'])
            rows.append(a)
        self.assertGreater(np.linalg.norm(rows[-1] - rows[0]), 3)


if __name__ == '__main__':
    unittest.main()
