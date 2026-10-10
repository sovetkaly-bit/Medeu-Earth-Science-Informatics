"""Offline tests of the pure cartography helpers (numpy only)."""
import math
import sys
import unittest
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src import carto_lib as L  # noqa: E402


class TestCartoLib(unittest.TestCase):
    def test_hillshade_flat_is_sin_altitude(self):
        h = L.hillshade(np.zeros((8, 8)), 30.0, 315, 45)
        self.assertTrue(np.allclose(h, math.sin(math.radians(45))))

    def test_hillshade_nan_propagates(self):
        z = np.zeros((8, 8)); z[3, 3] = np.nan
        h = L.hillshade(z, 30.0)
        self.assertTrue(np.isnan(h[3, 3]))

    def test_hillshade_sun_facing_slope_brighter(self):
        # elevation rises towards the south-east => NW-facing slope, lit by sun from NW (315 deg)
        yy, xx = np.mgrid[0:20, 0:20]
        nw_facing = (xx + yy) * 10.0
        se_facing = -(xx + yy) * 10.0
        self.assertGreater(np.nanmean(L.hillshade(nw_facing, 30.0)[2:-2, 2:-2]), np.nanmean(L.hillshade(se_facing, 30.0)[2:-2, 2:-2]))

    def test_nice_length(self):
        self.assertEqual(L.nice_length(25000), 5000)
        self.assertEqual(L.nice_length(7000), 1000)
        self.assertEqual(L.nice_length(900), 100)
        self.assertEqual(L.length_label(5000), "5 km")
        self.assertEqual(L.length_label(500), "500 m")

    def test_convergence(self):
        self.assertAlmostEqual(L.meridian_convergence_deg(75.0, 43.0, 75.0), 0.0, places=9)
        self.assertGreater(L.meridian_convergence_deg(77.0, 43.1, 75.0), 1.0)
        self.assertLess(L.meridian_convergence_deg(-111.6, 40.6, -111.0), 0.0)
        self.assertEqual(L.utm_central_meridian(32643), 75.0)
        self.assertEqual(L.utm_central_meridian(32612), -111.0)

    def test_class_shares_and_compare(self):
        dec = np.array([[0, 1, 2], [255, 1, 1]], dtype="uint8")
        s = L.class_shares(dec)
        self.assertEqual(s["n_px"], 5)
        self.assertAlmostEqual(s["ABOVE_pct"], 60.0)
        ref = {"n_px": 5, "BELOW_pct": 20.0, "ABOVE_pct": 60.0, "ABSTAIN_pct": 20.0}
        self.assertEqual(L.compare_shares(s, ref)[0], "OK")
        ref["ABOVE_pct"] = 61.0
        self.assertEqual(L.compare_shares(s, ref)[0], "FLAG_DISCREPANCY")
        ref["ABOVE_pct"] = 60.0; ref["n_px"] = 6
        self.assertEqual(L.compare_shares(s, ref)[0], "FLAG_DISCREPANCY")

    def test_class_shares_mask(self):
        dec = np.array([[0, 1], [2, 1]], dtype="uint8")
        m = np.array([[True, False], [True, False]])
        s = L.class_shares(dec, m)
        self.assertEqual(s["n_px"], 2)
        self.assertAlmostEqual(s["BELOW_pct"], 50.0)

    def test_slope_diff_and_disagreement(self):
        a = np.array([1.0, 10.0, np.nan, 20.0]); b = np.array([2.0, 14.0, 5.0, np.nan])
        st = L.slope_diff_stats(a, b)
        self.assertEqual(st["common_px"], 2)
        self.assertAlmostEqual(st["mean_diff_deg"], -2.5)
        dis, n = L.class_disagreement(a, b, 12.0)
        self.assertEqual(n, 2)
        self.assertAlmostEqual(dis, 50.0)

    def test_sample_bilinear(self):
        arr = np.arange(16, dtype=float).reshape(4, 4)
        # cell centre of (row 1, col 2): x = x0 + 2.5*res, y = y1 - 1.5*res
        v = L.sample_bilinear(arr, 0.0, 40.0, 10.0, np.array([25.0]), np.array([25.0]))
        self.assertAlmostEqual(float(v[0]), arr[1, 2])
        out = L.sample_bilinear(arr, 0.0, 40.0, 10.0, np.array([-100.0]), np.array([25.0]))
        self.assertTrue(np.isnan(out[0]))


if __name__ == "__main__":
    unittest.main()
