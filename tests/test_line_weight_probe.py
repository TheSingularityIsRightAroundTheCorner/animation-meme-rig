"""Line-weight probe on synthetic strokes: masses, growth to width, gap protection, CLI guard."""
import importlib.util
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
import numpy as np
from PIL import Image
from _support import SKILL

SCRIPT = SKILL / 'scripts' / 'line_weight_probe.py'
_spec = importlib.util.spec_from_file_location('line_weight_probe', SCRIPT)
probe = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(probe)


def card(width=160, height=120):
    rgba = np.zeros((height, width, 4), np.uint8)
    rgba[..., :3] = (240, 200, 190)
    rgba[..., 3] = 255
    return rgba


class LineWeightProbeTests(unittest.TestCase):
    def test_wide_dark_region_is_a_mass_not_a_stroke(self):
        rgba = card()
        rgba[10:110, 20:24, :3] = 10
        rgba[30:90, 80:140, :3] = 10
        line, mass, _ = probe.split_ink(rgba)
        self.assertTrue(line[60, 21])
        self.assertTrue(mass[60, 110])
        self.assertFalse(line[60, 110])

    def test_growth_reaches_requested_width(self):
        rgba = card()
        rgba[10:110, 50:54, :3] = 10
        line, _, inside = probe.split_ink(rgba)
        self.assertAlmostEqual(probe.stroke_width(line), 4, delta=1)
        self.assertEqual(int(probe.thicken(line, inside, 3)[60].sum()), 4 + 2 * 3)

    def test_gap_protection_keeps_close_strokes_apart(self):
        rgba = card()
        rgba[10:110, 40:44, :3] = 10
        rgba[10:110, 50:54, :3] = 10
        rgba[10:110, 120:124, :3] = 10
        line, _, inside = probe.split_ink(rgba)
        plain = probe.thicken(line, inside, 5)
        kept = probe.thicken(line, inside, 5, kappa=0.25)
        self.assertTrue(plain[60, 47])
        self.assertFalse(kept[60, 47])
        self.assertEqual(int(kept[60, 105:140].sum()), int(plain[60, 105:140].sum()))

    def test_cli_writes_sheet_and_refuses_to_overwrite_part(self):
        rgba = card()
        rgba[10:110, 50:54, :3] = 10
        with tempfile.TemporaryDirectory() as tmp:
            part, out = Path(tmp) / 'part.png', Path(tmp) / 'sheet.png'
            Image.fromarray(rgba).save(part)
            ok = subprocess.run([sys.executable, str(SCRIPT), str(part), '--out', str(out), '--scales', '0.25,0.5'],
                                capture_output=True, text=True)
            self.assertEqual(ok.returncode, 0, ok.stderr)
            self.assertTrue(out.is_file())
            refused = subprocess.run([sys.executable, str(SCRIPT), str(part), '--out', str(part)],
                                     capture_output=True, text=True)
            self.assertNotEqual(refused.returncode, 0)
            with Image.open(part) as image:
                self.assertEqual(np.asarray(image).tobytes(), rgba.tobytes())


if __name__ == '__main__':
    unittest.main()
