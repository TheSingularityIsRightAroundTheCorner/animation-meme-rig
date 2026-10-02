"""Less common documented failures; geometric fixtures only, never replacement art."""
import ast
import hashlib
import json
import math
import tempfile
import unittest
from pathlib import Path
import numpy as np
from PIL import Image
from _support import core, SOURCES, SKILL, sprite, tree


class DocumentedEdgeTests(unittest.TestCase):


    def test_explicit_layer_roles_and_numeric_sequence(self):
        names = ['glass_in_scr.png', 'orange_over_scr.png', 'eye_fx.png', 'claw_p10.png', 'body_base.png', 'claw_p2.png']
        self.assertEqual(core('effects').layer_order(names), ['body_base.png', 'claw_p2.png', 'claw_p10.png', 'eye_fx.png', 'glass_in_scr.png', 'orange_over_scr.png'])

    def test_time_visibility_keeps_glass_absent_before_entrance(self):
        r = core('rig_tree')
        parts = {'body': {'pivot': [0, 0], 'z': 0}, 'glass': {'pivot': [0, 0], 'z': 1}}
        images = {'body': Image.new('RGBA', (64, 64), 'red'), 'glass': Image.new('RGBA', (64, 64), 'blue')}
        a, _ = r.compose_frame(parts, images, {'glass': {'visible': False}})
        b, _ = r.compose_frame(parts, images, {'glass': {'visible': True}})
        self.assertEqual(a.getpixel((0, 0)), (255, 0, 0, 255))
        self.assertEqual(b.getpixel((0, 0)), (0, 0, 255, 255))



    def test_source_hand_perspective_calibration_is_preserved(self):
        # Freeze documented chosen art-specific values, not defaults for every hand.
        parsed = ast.parse((SOURCES / 'claude' / 'build_hand_turn_final (1).py').read_text())
        values = {}
        for node in parsed.body:
            if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
                if node.targets[0].id in ('FOCAL', 'THETA_END'):
                    values[node.targets[0].id] = ast.literal_eval(node.value)
        self.assertEqual(values, {'FOCAL': 130.0, 'THETA_END': 45.0})
        m = core('rig_tree').turn_matrix(0, 0, values['THETA_END'], values['FOCAL'])
        left = (m @ [-47, 0, 1]); right = (m @ [47, 0, 1])
        self.assertGreater(abs(left[0] / left[2]), abs(right[0] / right[2]) * 1.5)

    def test_source_crouch_sink_budget_camera_does_not_cancel(self):
        # This cut stays example-only; test its numeric choreography without loading art.
        parsed = ast.parse((SOURCES / 'claude' / 'build_cut87_spec (1).py').read_text())
        names = {'HEAD_TOTAL', 'BODY_DY', 'HEAD_DY', 'CAM_FOLLOW'}
        selected = [n for n in parsed.body if isinstance(n, ast.Assign) and len(n.targets)==1 and isinstance(n.targets[0], ast.Name) and n.targets[0].id in names]
        env = {}
        exec(compile(ast.Module(body=selected, type_ignores=[]), '<source constants>', 'exec'), env)
        self.assertEqual(env['BODY_DY'] + env['HEAD_DY'], 37)
        self.assertEqual(env['CAM_FOLLOW'], 0)
        camera = core('camera_25d')
        self.assertEqual(camera.camera_at([0, 0, 64, 64], [0, 0, 64, 64], 1), camera.camera_at([0, 0, 64, 64], [0, 0, 64, 64], 0))
