import unittest
import numpy as np
from src.timeseries import Acc, grid


class T(unittest.TestCase):
    def test_acc(self):
        a = Acc((2, 2))
        scl = np.array([[11, 4], [9, 5]], np.uint8)
        red = np.full((2, 2), 0.1, np.float32); nir = np.full((2, 2), 0.3, np.float32)
        a.add(scl, red, nir, 7)
        self.assertEqual(a.valid.tolist(), [[1, 1], [0, 1]])
        self.assertEqual(a.snow.tolist(), [[1, 0], [0, 0]])
        self.assertEqual(a.nd_n.tolist(), [[0, 1], [0, 1]])
        self.assertAlmostEqual(a.nd_sum[0, 1], 0.5)

    def test_grid(self):
        b, w, h = grid(120.0)
        self.assertGreater(w, 100); self.assertGreater(h, 100)


if __name__ == "__main__":
    unittest.main()
