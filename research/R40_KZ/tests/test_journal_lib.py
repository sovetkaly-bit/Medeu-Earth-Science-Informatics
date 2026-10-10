"""Offline tests of the journal display helpers (numpy/scipy/matplotlib only)."""
import math
import sys
import unittest
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src import carto_journal_lib as J  # noqa: E402


class TestJournalLib(unittest.TestCase):
    def test_upsample_shape_mask_and_alignment(self):
        z = np.arange(36, dtype="float64").reshape(6, 6)
        z[2, 2] = np.nan
        zu, bad = J.upsample_surface(z, 3)
        self.assertEqual(zu.shape, (18, 18))
        self.assertTrue(bad[6:9, 6:9].all())
        self.assertEqual(int(bad.sum()), 9)
        # linear ramp is reproduced; pixel-edge alignment: display cell 4 centre lies at source coordinate (4+0.5)/3-0.5
        ramp = np.tile(np.arange(8, dtype="float64"), (8, 1))
        ru, _ = J.upsample_surface(ramp, 3)
        self.assertAlmostEqual(float(ru[4, 4]), (4 + 0.5) / 3 - 0.5, places=3)

    def test_hillshade_multi_flat(self):
        h = J.hillshade_multi(np.zeros((9, 9)), 10.0)
        self.assertTrue(np.allclose(h, J.HS_FLAT))

    def test_relief_nodata_and_range(self):
        z = np.random.default_rng(0).normal(2000, 50, (20, 20)).cumsum(0)
        z[5:7, 5:7] = np.nan
        for kind in ("gray", "color"):
            rgb, info = J.relief(z, 30.0, k=2, kind=kind)
            self.assertEqual(rgb.shape, (40, 40, 3))
            self.assertTrue(np.isfinite(rgb).all())
            self.assertTrue(rgb.min() >= 0 and rgb.max() <= 1)
            self.assertEqual(int(info["bad"].sum()), 16)

    def test_tint_monotonic_stops(self):
        t = J.tint(np.array([500.0, 2300.0, 4400.0]))
        self.assertEqual(t.shape, (3, 3))
        self.assertGreater(t[2].sum(), t[1].sum())

    def test_aspect(self):
        self.assertAlmostEqual(J.aspect((0, 200, 0, 100)), 0.5)


if __name__ == "__main__":
    unittest.main()
