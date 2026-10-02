"""Camera/space regressions recorded before migrating any implementation."""
import copy
import json
import tempfile
import unittest
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw
from _support import core, original, SKILL


class CameraRegressionTests(unittest.TestCase):
    def test_measured_blue_guide_uses_alpha_and_returns_exclusive_xyxy(self):
        image = Image.new('RGBA', (100, 80), (0, 0, 255, 0))
        ImageDraw.Draw(image).rectangle((10, 15, 59, 44), fill=(0, 40, 230, 128))
        self.assertEqual(core('camera_25d').measure_frame(image, (100, 80)), (10, 15, 60, 45))

    def test_guide_canvas_mismatch_rejected(self):
        with self.assertRaisesRegex(ValueError, 'canvas'):
            core('camera_25d').measure_frame(Image.new('RGBA', (20, 10)), (40, 20))

    def test_missing_guide_color_rejected(self):
        with self.assertRaises(ValueError):
            core('camera_25d').measure_frame(Image.new('RGBA', (20, 10), 'white'), (20, 10))

    def test_xywh_to_xyxy_conversion_is_explicit(self):
        self.assertEqual(core('camera_25d').xywh_to_xyxy([5, 8, 20, 15]), (5, 8, 25, 23))
        with self.assertRaises(ValueError):
            core('camera_25d').xywh_to_xyxy([5, 8, -20, 15])

    def test_camera_endpoints_and_ease_spacing(self):
        camera = core('camera_25d')
        start, end = (20, 20, 60, 40), (0, 0, 100, 80)
        self.assertEqual(tuple(camera.camera_at(start, end, 0)), start)
        self.assertEqual(tuple(camera.camera_at(start, end, 1)), end)
        points = [camera.camera_at(start, end, i/13, easing='ease_out') for i in range(14)]
        delta = [np.linalg.norm(np.array(b)-a) for a,b in zip(points, points[1:])]
        self.assertTrue(all(a >= b for a,b in zip(delta, delta[1:])))
        self.assertTrue(all(d > 0 for d in delta[-3:]))

    def test_pose_swap_favors_incoming_pose(self):
        schedule = [{'at': 0, 'part': 'down'}, {'at': .70, 'part': 'mid'}, {'at': .85, 'part': 'up'}]
        camera = core('camera_25d')
        self.assertEqual(camera.pose_at(schedule, .69), 'down')
        self.assertEqual(camera.pose_at(schedule, .70), 'mid')
        self.assertEqual(camera.pose_at(schedule, 1), 'up')

    def test_out_of_bounds_crop_does_not_silently_create_black_border(self):
        image = Image.new('RGBA', (100, 80), 'white')
        with self.assertRaisesRegex(ValueError, 'bound|canvas'):
            core('camera_25d').crop_frame(image, (-1, 0, 99, 80), (50, 40))
        with self.assertRaises(ValueError):
            core('camera_25d').crop_frame(image, (20, 0, 10, 80), (50, 40))
        result = core('camera_25d').crop_frame(image, (0, 0, 100, 80), (50, 40))
        self.assertEqual(result.size, (50, 40))
        self.assertEqual(result.convert('RGB').getpixel((0, 0)), (255,255,255))

    def test_compiled_camera_uses_uniform_motion_duration_and_full_blur_states(self):
        shot = {'frame_start':[20,20,40,20], 'frame_end':[0,0,100,80], 'frames':14,
                'easing':'ease_out', 'frame_ms':50, 'hold_in':2, 'hold_out':1,
                'motion_blur':True, 'screen_effects':[{'part':'lines'}],
                'world_effects':[{'part':'smoke'}]}
        saved = copy.deepcopy(shot)
        result = core('camera_25d').compile_shot(shot, (100,80))
        self.assertEqual(shot, saved)
        self.assertEqual(len(result),17)
        self.assertEqual({f['ms'] for f in result}, {50})
        self.assertEqual(tuple(result[0]['camera']), (20,20,60,40))
        self.assertEqual(tuple(result[-1]['camera']), (0,0,100,80))
        self.assertTrue(any(len(f.get('camera_substeps', [])) >= 2 for f in result))
        self.assertEqual(result[4]['screen_effects'], [{'part':'lines'}])
        self.assertEqual(result[4]['world_effects'], [{'part':'smoke'}])


class ProjectionRegressionTests(unittest.TestCase):
    def test_projection_billboard_matches_original(self):
        new, old = core('stadium3d'), original('claude', 'stadium3d.py')
        r,e = new.look_at((4,2,7),(0,1,0))
        ro,eo = old.look_at((4,2,7),(0,1,0))
        np.testing.assert_allclose(r,ro)
        points = [(0,0,0),(1,2,0),(-2,1,1)]
        for a,b in zip(new.project(points,r,e,160,90,52),old.project(points,ro,eo,160,90,52)):
            np.testing.assert_allclose(a,b)
        np.testing.assert_allclose(new.billboard((0,1,0),2,.5,r),old.billboard((0,1,0),2,.5,ro))

    def test_invalid_camera_basis_rejected(self):
        camera = core('stadium3d')
        with self.assertRaises(ValueError): camera.look_at((0,0,0),(0,0,0))
        with self.assertRaises(ValueError): camera.look_at((0,0,0),(0,1,0))

    def test_slicing_keeps_visible_floor_when_far_corner_crosses_camera(self):
        stage = core('stadium3d')
        r,e = stage.look_at((0,1,0),(0,0,-3))
        quad = [(-2,0,-5),(2,0,-5),(2,0,2),(-2,0,2)]
        canvas = Image.new('RGBA',(160,90),(255,255,255,255))
        tex = Image.new('RGBA',(16,16),(160,70,30,255))
        # The archived renderer rejected this entire quad. The fixed renderer
        # must retain its visible portion even without the historical slices.
        legacy = original('claude', 'stadium3d.py')
        self.assertIsNone(legacy.draw_quad(canvas,tex,quad,r,e,52))
        self.assertIsNotNone(stage.draw_quad(canvas,tex,quad,r,e,52))
        self.assertTrue(np.any(np.asarray(canvas)[...,:3] != 255))
        canvas = Image.new('RGBA',(160,90),(255,255,255,255))
        count = 0
        for q,t in stage.strips(quad,tex,n=14,axis=1):
            count += stage.draw_quad(canvas,t,q,r,e,52) is not None
        self.assertGreater(count,0)
        self.assertLess(count,14)
        self.assertTrue(np.any(np.asarray(canvas)[...,:3] != 255))

    def test_room_render_accepts_portable_assets_and_keeps_visible_floor(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)
            Image.new('RGBA',(24,24),(170,100,50,255)).save(path/'sheet.png')
            Image.new('RGBA',(12,24),(20,40,200,255)).save(path/'pose.png')
            spec = {'panel_sheet':'sheet.png','panels':{key:[0,0,24,24] for key in ('near','far','left','right','floor')},
                    'pose_files':['pose.png']*3,'out_size':[80,45],'frames':3}
            frames = core('stadium3d').render_frames(spec,base_dir=path)
            self.assertEqual(len(frames),3)
            self.assertTrue(all(frame.size==(80,45) for frame in frames))
            self.assertTrue(all(np.any(np.asarray(frame)!=255) for frame in frames))

    def test_panel_sheet_path_and_config_are_explicit(self):
        stage = core('stadium3d')
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)/'sheet.png'
            image = Image.new('RGBA',(10,6),'blue')
            ImageDraw.Draw(image).rectangle((0,0,3,5),fill='red')
            image.save(path)
            panels = stage.load_panels(path,{'near':{'box':[0,0,4,6],'rotation':90},'far':[4,0,10,6]})
            self.assertEqual(panels['near'].size,(6,4))
            self.assertEqual(panels['far'].getpixel((0,0)),(0,0,255,255))


class GlobeScatterFloorRegressionTests(unittest.TestCase):
    def test_latest_globe_and_corrected_floor_profiles_preserved(self):
        globe = json.loads((SKILL/'presets/globe.json').read_text())
        self.assertEqual((globe['size'],globe['frames'],globe['fps']),(520,48,24))
        self.assertEqual((globe['ambient'],globe['rim'],globe['cloud_opacity'],globe['cloud_relative_speed']),(.38,.16,.82,1.12))
        room = json.loads((SKILL/'presets/stadium_floorfix.json').read_text())
        self.assertEqual(room['panels']['floor'],{'box':[320,680,870,960],'rotation':0})
        self.assertEqual(room['panels']['near'],{'box':[285,930,860,1245],'rotation':0})

    def test_globe_cloud_and_rim_exact_original(self):
        new, old = core('sphere'), original('claude','sphere.py')
        texture = Image.fromarray(np.arange(24*48*3,dtype=np.uint8).reshape(24,48,3))
        cloud = Image.new('RGBA',(24,12),(240,245,250,0))
        ImageDraw.Draw(cloud).rectangle((2,3,12,6),fill=(230,240,255,140))
        for spin in (0,.4,-1.3):
            kw = {'size':48,'spin':spin,'clouds':cloud,'cloud_spin':.12,'cloud_opacity':.7,'rim':.3}
            np.testing.assert_array_equal(np.asarray(new.render_globe(texture,**kw)),np.asarray(old.render_globe(texture,**kw)))

    def test_globe_profile_applies_only_relative_cloud_drift(self):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)
            tex=Image.new('RGB',(48,24),(180,100,40));tex.save(path/'land.png')
            cloud=Image.new('RGBA',(48,24),(255,255,255,0))
            ImageDraw.Draw(cloud).rectangle((3,2,17,21),fill=(245,245,255,180));cloud.save(path/'cloud.png')
            spec={'land':'land.png','cloud':'cloud.png','size':32,'frames':3,'cloud_relative_speed':1.12}
            frames=core('sphere').render_frames(spec,path)
            spin=2*np.pi/3
            expected=core('sphere').render_globe(tex,size=32,spin=spin,clouds=cloud,cloud_spin=spin*.12)
            np.testing.assert_array_equal(np.asarray(frames[1]),np.asarray(expected))

    def test_globe_zero_opacity_cloud_preserves_base(self):
        globe = core('sphere')
        tex = Image.new('RGB',(32,16),(180,100,40))
        clear = globe.render_globe(tex,size=32)
        clouds = globe.render_globe(tex,size=32,clouds=Image.new('RGBA',(16,8),'white'),cloud_opacity=0)
        np.testing.assert_array_equal(np.asarray(clear),np.asarray(clouds))

    def test_globe_zero_light_rejected(self):
        with self.assertRaises(ValueError):
            core('sphere').render_globe(Image.new('RGB',(8,4),'white'),light=(0,0,0))

    def test_scatter_matches_original_and_has_fast_substeps(self):
        new, old = core('scatter_exit'), original('claude','scatter_exit (1).py')
        kwargs = {'items':{'blade':(63,-4)},'drift_frames':5,'drift_px':10,'snap_frames':3,'exit_px':200}
        result = list(new.scatter_exit(**kwargs))
        self.assertEqual(result,list(old.scatter_exit(**kwargs)))
        self.assertTrue(all(f[2] is None for f in result[:5]))
        self.assertTrue(all(len(f[2])==6 for f in result[5:]))
        endpoint = result[-1][1]['blade']
        self.assertAlmostEqual(np.hypot(endpoint['dx'],endpoint['dy']),200)
        self.assertEqual(result[-1][2][-1],result[-1][1])

    def test_floor_stagger_and_integer_scroll_original_exact(self):
        new, old = core('floor3d'),original('claude','floor3d.py')
        for scroll in (0,.3,1):
            np.testing.assert_array_equal(np.asarray(new.draw_floor(160,90,scroll=scroll)),np.asarray(old.draw_floor(160,90,scroll=scroll)))
        np.testing.assert_array_equal(np.asarray(new.draw_floor(160,90,scroll=0)),np.asarray(new.draw_floor(160,90,scroll=1)))


if __name__ == '__main__':
    unittest.main()
