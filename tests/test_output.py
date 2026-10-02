import json
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path
import numpy as np
from PIL import Image
from _support import core


class OutputRegressionTests(unittest.TestCase):
    def test_global_palette_includes_late_effect_colors(self):
        frames = [Image.new('RGB', (32, 32), c) for c in [(180, 20, 20), (20, 180, 20), (20, 20, 180)]]
        quantized = core('output').quantize_frames(frames)
        palettes = [im.getpalette() for im in quantized]
        self.assertTrue(all(p == palettes[0] for p in palettes))
        for actual, expected in zip(quantized, frames):
            np.testing.assert_array_equal(np.asarray(actual.convert('RGB')), np.asarray(expected))

    def test_palette_does_not_regress_to_48_colors(self):
        row = np.arange(255, dtype=np.uint8)
        a = np.repeat(row[None, :, None], 3, axis=2)
        frame = Image.fromarray(np.repeat(a, 8, axis=0))
        q = core('output').quantize_frames([frame])[0]
        self.assertGreater(len(q.getcolors()), 200)

    def test_png_sequence_preserves_alpha_and_all_frames(self):
        frames = [Image.new('RGBA', (16, 16), c) for c in [(255, 0, 0, 80), (0, 255, 0, 120)]]
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / 'frames'
            core('output').save_frames(frames, path, fps=25)
            files = sorted(path.glob('*.png'))
            self.assertEqual(len(files), 2)
            for file, frame in zip(files, frames):
                np.testing.assert_array_equal(np.asarray(Image.open(file)), np.asarray(frame))

    def test_gif_preserves_holds_and_late_colors(self):
        frames = [Image.new('RGB', (16, 16), c) for c in ['red', 'green', 'blue']]
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / 'out.gif'
            core('output').save_frames(frames, path, durations=[100, 200, 300])
            with Image.open(path) as im:
                self.assertEqual(im.n_frames, 3)
                for i, ms in enumerate([100, 200, 300]):
                    im.seek(i)
                    self.assertEqual(im.info['duration'], ms)
                    self.assertEqual(im.convert('RGB').getpixel((0, 0)), frames[i].getpixel((0, 0)))

    @unittest.skipUnless(shutil.which('ffmpeg') and shutil.which('ffprobe'), 'ffmpeg/ffprobe optional')
    def test_mp4_is_rgb_playable_and_authored_duration_retained(self):
        frames = [Image.new('RGB', (32, 32), c) for c in ['red', 'green', 'blue']]
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / 'out.mp4'
            core('output').save_frames(frames, path, fps=10, durations=[100, 200, 300])
            probe = subprocess.run(['ffprobe', '-v', 'error', '-show_streams', '-of', 'json', str(path)], capture_output=True, text=True, check=True)
            stream = json.loads(probe.stdout)['streams'][0]
            self.assertEqual((stream['width'], stream['height']), (32, 32))
            self.assertAlmostEqual(float(stream['duration']), .6, delta=.11)
            self.assertEqual(int(stream['nb_frames']), 6)

    def test_invalid_output_does_not_silently_encode_mp4(self):
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaises(ValueError):
                core('output').save_frames([Image.new('RGB', (16, 16))], Path(d) / 'out.bad')
