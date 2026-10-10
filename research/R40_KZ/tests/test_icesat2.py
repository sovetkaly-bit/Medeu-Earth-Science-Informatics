import unittest
import numpy as np
from src import icesat2 as I


class G:  # minimal grid stand-in
    x0, y1, res, w, h = 0.0, 3000.0, 30.0, 100, 100


class TestIcesat(unittest.TestCase):
    def test_sample_plane(self):
        yy, xx = np.mgrid[0:100, 0:100]
        z = 2.0 * xx * 30.0  # elevation grows with x
        x = np.array([1500.0, 900.0]); y = np.array([1500.0, 1200.0])
        v = I.sample(z, G, x, y)
        np.testing.assert_allclose(v, 2.0 * (x - 15.0), atol=1e-6)  # pixel centres at +15 m

    def test_track_pairs_spacing_and_beams(self):
        n = 6
        p = {"granule": np.array(["a"] * n), "beam": np.array(["gt1l"] * 3 + ["gt1r"] * 3), "dt": np.arange(n, dtype=float)}
        x = np.array([0, 100, 200, 0, 100, 400.0]); y = np.zeros(n)
        a, b, d = I.track_pairs(p, x, y)
        self.assertEqual(len(a), 3)  # (0,1),(1,2),(3,4); (4,5) is 300 m, (2,3) crosses beams
        np.testing.assert_allclose(d, 100.0)

    def test_quality_and_nmad(self):
        p = {"h_te": np.array([1.0, 5e38, 3.0]), "h_te_unc": np.array([1.0, 1.0, 9.0]), "n_te_ph": np.array([50, 50, 50.0]),
             "cloud": np.array([0, 0, 0.0]), "night": np.array([1, 1, 1.0])}
        self.assertEqual(I.quality_mask(p, unc_max=5.0).tolist(), [True, False, False])
        self.assertEqual(I.quality_mask(p, unc_max=15.0).tolist(), [True, False, True])
        self.assertAlmostEqual(I.nmad(np.array([0.0, 1.0, -1.0, 2.0, -2.0])), 1.4826 * 1.0)

    def test_smooth100_nan_edges(self):
        z = np.ones((10, 10)); z[5, 5] = np.nan
        s = I.smooth100(z)
        self.assertTrue(np.isnan(s[4:7, 4:7]).all())
        self.assertAlmostEqual(float(s[2, 2]), 1.0)


if __name__ == "__main__":
    unittest.main()
