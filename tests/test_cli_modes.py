"""End-to-end mode dispatch from an unrelated cwd using caller-supplied fixtures."""
import copy
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

import numpy as np
from PIL import Image, ImageDraw
from _support import ROOT, SKILL, sprite


class CLIModeIntegrationTests(unittest.TestCase):
    def run_scene(self, root, spec, count, size, durations):
        path=root/'scene.json'
        spec=copy.deepcopy(spec)
        spec.update(version=1,output='rendered')
        path.write_text(json.dumps(spec),encoding='utf-8')
        env=os.environ.copy()
        # Subprocess cwd is '/', so dependency lookup must not rely on relative paths.
        paths=[str(Path(p).resolve()) for p in env.get('PYTHONPATH','').split(os.pathsep) if p]
        runtime=ROOT/'skill_migration/runtime'
        if runtime.is_dir():paths.insert(0,str(runtime.resolve()))
        if paths:env['PYTHONPATH']=os.pathsep.join(paths)
        result=subprocess.run([sys.executable,str(SKILL/'scripts/render.py'),str(path)],
                              cwd='/',env=env,capture_output=True,text=True,timeout=30)
        self.assertEqual(result.returncode,0,result.stderr)
        self.assertIn('mode='+spec['mode'],result.stdout)
        output=root/'rendered';files=sorted(output.glob('*.png'))
        self.assertEqual(len(files),count,result.stdout)
        self.assertEqual([p.name for p in files],[f'{i:05d}.png' for i in range(count)])
        timing=json.loads((output/'timing.json').read_text())
        np.testing.assert_allclose(timing['durations_ms'],durations,rtol=0,atol=1e-10)
        images=[]
        for file in files:
            with Image.open(file) as image:
                self.assertEqual(image.size,size)
                self.assertEqual(image.mode,'RGB')
                images.append(image.copy())
        return images

    def test_punch_cli_outputs_every_frame_with_timing(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            Image.new('RGBA',(32,24),(160,170,180,255)).save(root/'body.png')
            sprite((16,16),(3,3,7,7),(220,30,20,255)).save(root/'left.png')
            sprite((16,16),(10,9,14,13),(30,50,220,255)).save(root/'right.png')
            lines=Image.new('RGBA',(32,24),(0,0,0,0))
            ImageDraw.Draw(lines).line((2,0,2,23),fill=(0,0,0,255));lines.save(root/'lines.png')
            spec={'mode':'punch','canvas':[32,24],'fps':20,
                  'assets':{'body':'body.png','fists':['left.png','right.png'],'speedline':'lines.png'},
                  'fists':[{'side':'L','centroid':[5,5]},{'side':'R','centroid':[12,11]}],
                  'shoulders':{'L':[12,10],'R':[20,10]},
                  'punch':{'count':2,'step_frames':1,'duration_frames':2,'perspective_scale':2},
                  'motion_blur':{'substeps':2,'shutter':.5},'camera':{'zoom_end':1},
                  'body':{'max_horizontal_brace_px':0,'max_vertical_brace_px':0},
                  'speedline':{'enabled':True,'pulse_interval_sec':.5,'visible_envelope_frames':[1],'z_order':'topmost'}}
            images=self.run_scene(root,spec,9,(32,24),[50]*9)
            self.assertEqual(images[0].getpixel((2,12)),(0,0,0))
            self.assertEqual(images[-1].getpixel((25,12)),(160,170,180))

    def test_mesh_cli_hard_pose_swaps_and_absolute_beat_duration(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            sprite((32,24),(3,5,10,20),(220,30,20,255)).save(root/'pose_a.png')
            sprite((32,24),(21,5,28,20),(20,30,220,255)).save(root/'pose_b.png')
            spec={'mode':'mesh','canvas':[32,24],'fps':8,'bpm':120,'beats_per_pose':1,
                  'assets':{'poses':['pose_a.png','pose_b.png']},'sequence':[[1,'none',0],[2,'none',0]]}
            images=self.run_scene(root,spec,8,(32,24),[125]*8)
            self.assertEqual(images[0].getpixel((6,12)),(220,30,20))
            self.assertEqual(images[4].getpixel((6,12)),(255,255,255))
            self.assertEqual(images[4].getpixel((25,12)),(20,30,220))

    def test_globe_cli_latest_lighting_profile_and_frame_time(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            tex=Image.new('RGB',(64,32),(180,100,40))
            ImageDraw.Draw(tex).rectangle((0,0,20,31),fill=(30,160,80));tex.save(root/'land.png')
            clouds=Image.new('RGBA',(64,32),(255,255,255,0))
            ImageDraw.Draw(clouds).rectangle((4,4,15,13),fill=(240,245,255,160));clouds.save(root/'cloud.png')
            spec=json.loads((SKILL/'presets/globe.json').read_text())
            spec.update(land='land.png',cloud='cloud.png',size=32,frames=4)
            images=self.run_scene(root,spec,4,(32,32),[1000/24]*4)
            self.assertEqual(images[0].getpixel((0,0)),(18,20,28))
            self.assertFalse(np.array_equal(np.asarray(images[0]),np.asarray(images[1])))

    def test_mesh_cli_applies_song_offset_to_frame_count_and_pose_cut(self):
        for offset_ms in (88.5, -88.5):
            with self.subTest(offset_ms=offset_ms), tempfile.TemporaryDirectory() as directory:
                root=Path(directory)
                colors=[(220,30,20),(20,30,220)]
                for name,color in zip(('pose_a.png','pose_b.png'),colors):
                    Image.new('RGBA',(16,16),(*color,255)).save(root/name)
                spec={'mode':'mesh','canvas':[16,16],'fps':30,'bpm':189.9,'beats_per_pose':1,
                      'offset_ms':offset_ms,'assets':{'poses':['pose_a.png','pose_b.png']},
                      'sequence':[[1,'none',0],[2,'none',0]]}
                end=round(offset_ms*30/1000+2*60/189.9*30)
                cut=round(offset_ms*30/1000+60/189.9*30)
                images=self.run_scene(root,spec,end,(16,16),[1000/30]*end)
                self.assertEqual([f.getpixel((8,8)) for f in images],
                                 [colors[0]]*cut+[colors[1]]*(end-cut))

    def test_room_cli_historical_floorfix_declared_crops(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            spec=json.loads((SKILL/'presets/stadium_floorfix.json').read_text())
            spec.update(panel_sheet='sheet.png',pose_files=['pose.png']*3,out_size=[48,27],frames=3)
            sheet=Image.new('RGBA',(60,80),(240,240,240,255))
            colors={'far':(210,40,40,255),'left':(40,210,40,255),'right':(210,40,210,255),
                    'near':(40,80,210,255),'floor':(180,140,80,255)}
            for key in ('far','left','right','near','floor'):
                box=[round(v*.05) for v in spec['panels'][key]['box']]
                spec['panels'][key]['box']=box
                ImageDraw.Draw(sheet).rectangle((box[0],box[1],box[2]-1,box[3]-1),fill=colors[key])
            sheet.save(root/'sheet.png')
            sprite((16,32),(5,2,10,30),(30,40,60,255)).save(root/'pose.png')
            images=self.run_scene(root,spec,3,(48,27),[70]*3)
            self.assertTrue(all(np.any(np.asarray(image)!=255) for image in images))
            tan=np.array([180,140,80])
            self.assertTrue(any(np.any(np.all(np.asarray(image)==tan,axis=2)) for image in images),'declared floor crop must remain visible; this does not certify the historical crop against real artwork')

    def test_modern_pant_cli_preserves_source_pose_holds_and_variable_ms(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            original=json.loads((SKILL/'presets/pant_steam_v3.json').read_text())
            cycle=original['actors'][0]['profile']['breath']
            Image.new('RGBA',(64,64),(245,245,245,255)).save(root/'background.png')
            sprite((64,64),(20,35,43,61),(80,100,130,255)).save(root/'body1.png')
            sprite((64,64),(20,35,43,61),(110,130,160,255)).save(root/'body2.png')
            sprite((64,64),(23,15,40,34),(180,120,90,255)).save(root/'head.png')
            sprite((64,64),(22,9,41,15),(40,30,20,255)).save(root/'hair.png')
            sprite((64,64),(45,8,53,50),(220,220,220,90)).save(root/'steam.png')
            names={key:key for key in ('body1','body2','head','hair')}
            spec={'mode':'pant','background':'background.png','out_size':[32,32],'breaths':1,'seed':7,
                  'front_haze':False,'panel':{'line_x0':0,'slope':0,'half':0},
                  'actors':[{'profile':{'breath':cycle,'neck':[32,34],'crown':[32,9],'phase':0,'parts':names},
                             'files':{key:key+'.png' for key in names},'steam':'steam.png','side':'right'}]}
            images=self.run_scene(root,spec,8,(32,32),[row[4] for row in cycle])
            self.assertEqual([row[4] for row in cycle],[110,210,55,55,110,210,55,55])
            self.assertEqual(images[0].getpixel((16,24)),images[1].getpixel((16,24)))
            self.assertFalse(np.array_equal(np.asarray(images[0]),np.asarray(images[1])),'secondary hair/steam should settle through main hold')


if __name__=='__main__':unittest.main()
