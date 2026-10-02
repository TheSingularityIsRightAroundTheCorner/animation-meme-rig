"""Secondary animation failure/compatibility cases captured before extraction."""
import math
import random
import unittest
import numpy as np
from PIL import Image, ImageFilter
from _support import core, source_functions, sprite

BREATH=[(1,0,-5,0.,110),(1,0,0,0.,210),(1,-14,-4,-1.2,55),(2,-26,-14,-2.8,55),(2,-23,-30,-2.5,110),(2,-23,-23,-2.5,210),(2,-10,-26,-1.2,55),(1,4,-9,.4,55)]


class SecondaryRegressionTests(unittest.TestCase):
    def test_breath_primary_holds_while_hair_settles(self):
        profile={'breath':BREATH,'neck':[30,20],'crown':[30,5],
                 'parts':{'body1':'b1','body2':'b2','head':'h','hair':'f'}}
        first=core('secondary').breath_layers(profile,0)
        second=core('secondary').breath_layers(profile,1)
        self.assertEqual(first[:2],second[:2])
        self.assertNotEqual(first[2]['dy'],second[2]['dy'])
        profile['phase']=4
        self.assertEqual(core('secondary').breath_layers(profile,0)[0]['part'],'b2')

    def test_steam_motion_matches_source_default(self):
        original=source_functions('claude','build_pant_steam_v3.py',['steam_state'],
            {'math':math,'BREATH':BREATH,'WOBBLE':11,'STEAM_RISE':155,'STEAM_GROW':.26,'PEAK_OPACITY':.85})
        for step in (-4,0,1,4,7):
            self.assertEqual(core('secondary').steam_state(step,phase=1.7,lead=.7),original.steam_state(step,phase=1.7,lead=.7))

    def test_panel_mask_and_secondary_pillow_rotation_preserved(self):
        original=source_functions('claude','build_pant_steam_v3.py',['panel_mask','place'],
            {'Image':Image,'W':64,'H':64,'LINE_X0':10.,'LINE_SLOPE':.4,'LINE_HALF':2})
        new=core('secondary')
        for side in ('left','right'):
            np.testing.assert_array_equal(np.asarray(new.panel_mask((64,64),side,line_x0=10,slope=.4,half=2)),np.asarray(original.panel_mask(side)))
        a,b=Image.new('RGBA',(64,64)),Image.new('RGBA',(64,64))
        kwargs={'dy':-2,'rot':12,'pivot':(32,20),'scale':1.1,'opacity':.7}
        new.place(a,sprite(),**kwargs);original.place(b,sprite(),**kwargs)
        np.testing.assert_array_equal(np.asarray(a),np.asarray(b))

    def test_steam_mask_and_composition_do_not_obscure_character(self):
        secondary=core('secondary')
        canvas=Image.new('RGBA',(64,64),'white')
        art=Image.new('RGBA',(64,64),(200,200,200,160))
        mask=secondary.panel_mask((64,64),'left',line_x0=32,slope=0,half=0)
        state={'dx':0,'dy':0,'scale':1,'opacity':.85}
        secondary.draw_steam(canvas,art,mask,state,random.Random(7),jitter=0,jitter_y=0)
        self.assertEqual(canvas.getpixel((50,10)),(255,255,255,255))
        self.assertNotEqual(canvas.getpixel((10,10)),(255,255,255,255))
        canvas.alpha_composite(sprite(box=(5,5,20,20),color=(20,40,60,255)))
        self.assertEqual(canvas.getpixel((10,10)),(20,40,60,255))

    def test_glint_preserves_full_brightness_lenses_in_dark_scene(self):
        secondary=core('secondary')
        base=Image.new('RGBA',(16,16),(100,80,60,255))
        lens=Image.new('RGBA',(16,16),(255,255,255,255))
        mask=Image.new('L',(16,16),0);mask.paste(255,(5,5,10,10))
        spark=Image.new('RGBA',(3,3),'white')
        config={'dark_floor':.46,'lens_height':5,'spark_at':[8,7]}
        image=secondary.render_glint(base,lens,mask,spark,config,1,1)
        self.assertEqual(image.getpixel((7,7)),(255,255,255))
        self.assertEqual(image.getpixel((0,0)),(46,36,27))
        tiny=secondary.render_glint(base,lens,mask,spark,config,1,1,spark_scale=.0001,spark_alpha=1)
        self.assertEqual(tiny.size,(16,16))


if __name__=='__main__':unittest.main()
