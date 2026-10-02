import unittest
import numpy as np
from PIL import Image
from _support import core
m = core('local_mesh')

class LocalMeshTests(unittest.TestCase):
    def setUp(self):
        rng = np.random.default_rng(12)
        self.im = Image.fromarray(rng.integers(0,256,(96,128,4),dtype=np.uint8))

    def test_identity_preserves_rgba(self):
        out = m.warp_local(self.im, lambda x,y:(x,y), step=13)
        np.testing.assert_array_equal(np.array(out), np.array(self.im))

    def test_local_motion_leaves_distant_occluder_unchanged(self):
        out = m.warp_local(self.im, lambda x,y:(x,y-5*m.ellipse_weight(x,y,30,30,16,16)),step=4)
        np.testing.assert_array_equal(np.array(out)[:,64:],np.array(self.im)[:,64:])
        self.assertFalse(np.array_equal(np.array(out)[20:40,20:40], np.array(self.im)[20:40,20:40]))

    def test_contact_plateau_has_identical_translation(self):
        shifts=[8*m.plateau_weight(x,y,(20,20,60,45),10) for x,y in [(25,25),(40,35),(59,44)]]
        self.assertEqual(shifts,[8,8,8])
        self.assertEqual(m.plateau_weight(80,30,(20,20,60,45),10),0)

    def test_camera_maps_unfinished_body_below_frame(self):
        _,bottom=m.camera_inverse(960,1080,1.36,(960,30),(960,130))
        self.assertLess(bottom,950)
        self.assertAlmostEqual(bottom,902.0588235294)

    def test_translation_sign_and_outside_alpha(self):
        out=np.array(m.warp_local(self.im,lambda x,y:(x-8,y),step=8))
        self.assertTrue((out[:,:8,3]==0).all())
        np.testing.assert_array_equal(out[:,8:],np.array(self.im)[:,:-8])

    def test_invalid_parameters(self):
        with self.assertRaises(ValueError): m.warp_local(self.im,lambda x,y:(x,y),step=0)
        with self.assertRaises(ValueError): m.camera_inverse(0,0,0)
        with self.assertRaises(ValueError): m.ellipse_weight(0,0,0,0,0,2)
