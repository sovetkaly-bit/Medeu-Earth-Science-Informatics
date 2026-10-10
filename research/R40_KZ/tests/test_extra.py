import unittest
import numpy as np
from src import decision as D
from src import extra_checks as X


class TestExtra(unittest.TestCase):
    def test_aurc_fast_matches_reference(self):
        rng = np.random.default_rng(0)
        u = rng.random(2000); err = (rng.random(2000) < 0.1 + 0.3 * u).astype(float)
        self.assertAlmostEqual(X.aurc_fast(u, err), D.aurc(u, err, np.random.default_rng(1)), places=10)

    def test_identical_methods_have_zero_difference(self):
        rng = np.random.default_rng(1)
        n = 3000
        u = rng.random(n); err = (rng.random(n) < 0.05 + 0.2 * u).astype(float)
        site = np.repeat(["a", "b", "c"], n // 3)
        block = np.concatenate([np.repeat(np.arange(10), n // 30) + 1000 * i for i in range(3)])
        for strat in (True, False):
            bs = X.boot({"m1": u, "m2": u.copy()}, err, block, site, n_boot=20, seed=2, stratified=strat)
            self.assertTrue(np.allclose(bs["m1"]["pooled"], bs["m2"]["pooled"]))

    def test_informative_score_beats_random(self):
        rng = np.random.default_rng(2)
        n = 4000
        u = rng.random(n); err = (rng.random(n) < 0.02 + 0.3 * u ** 3).astype(float)
        self.assertLess(X.aurc_fast(u, err), X.aurc_fast(rng.random(n), err))


if __name__ == "__main__":
    unittest.main()
