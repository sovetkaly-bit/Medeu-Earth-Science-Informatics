"""Offline self-tests on synthetic terrain: python -m unittest discover -s tests (run from research/R40_KZ)."""
import unittest
import numpy as np
from scipy import ndimage as ndi
from src import terrain as T, decision as D


def fractal_dem(n=240, seed=0, relief=600.0, h=0.8):
    rng = np.random.default_rng(seed)
    f = np.fft.fftfreq(n)[:, None] ** 2 + np.fft.fftfreq(n)[None, :] ** 2
    f[0, 0] = 1
    spec = (rng.standard_normal((n, n)) + 1j * rng.standard_normal((n, n))) / f ** ((h + 1) / 2)
    z = np.real(np.fft.ifft2(spec))
    z = (z - z.min()) / (z.max() - z.min()) * relief
    return z


class TestSlope(unittest.TestCase):
    def test_plane_slope_all_algorithms(self):
        y, x = np.mgrid[0:50, 0:50]
        z = 30.0 * x * np.tan(np.radians(20))  # 20 deg slope, 30 m cells
        for m in T.ALGORITHMS:
            s = T.slope_deg(z, 30.0, m)
            self.assertAlmostEqual(float(np.nanmean(s)), 20.0, places=3, msg=m)
            self.assertTrue(np.isnan(s[0, 0]))

    def test_nodata_propagates(self):
        z = fractal_dem(60)
        z[30, 30] = np.nan
        s = T.slope_deg(z, 30.0)
        self.assertTrue(np.isnan(s[29:32, 29:32]).all())
        self.assertTrue(np.isfinite(s[10, 10]))

    def test_block_mean_and_upsample(self):
        z = np.arange(36.0).reshape(6, 6)
        b = T.block_mean(z, 3)
        self.assertEqual(b.shape, (2, 2))
        self.assertAlmostEqual(b[0, 0], z[:3, :3].mean())
        self.assertEqual(T.upsample(b, 3).shape, (6, 6))
        z[0, 0] = np.nan
        self.assertTrue(np.isnan(T.block_mean(z, 3)[0, 0]))

    def test_local_std_constant(self):
        s = T.local_std(np.full((20, 20), 5.0), 3)
        self.assertAlmostEqual(float(np.nanmax(s)), 0.0, places=4)


class TestDecision(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tables = {}
        for i, seed in enumerate((1, 2, 3)):
            ref30 = fractal_dem(240, seed)                       # "truth" terrain at 30 m
            rf = 10.0
            fine = np.kron(ref30, np.ones((3, 3)))                # fake 10 m reference
            fine = fine + ndi.gaussian_filter(np.random.default_rng(seed).standard_normal(fine.shape), 3) * 1.0
            fine = fine[: 240 * 3, : 240 * 3]
            rng = np.random.default_rng(100 + seed)
            z = {}
            for name, sd in (("cop-dem-glo-30", 4.0), ("nasadem", 6.0), ("alos-dem", 5.0)):
                z[name] = ref30 + ndi.gaussian_filter(rng.standard_normal(ref30.shape), 1.5) * sd * 2
            cls.tables[f"s{i}"] = {"z": z, "fine": fine, "rf": rf}

    def build(self, t=15.0, **kw):
        return {s: D.build_table(s, v["z"], v["fine"], v["rf"], t, **kw) for s, v in self.tables.items()}

    def test_error_depends_on_distance(self):
        tabs = self.build()
        tab = tabs["s0"]
        near = tab["err"][tab["dist"] < 1.0].mean()
        far = tab["err"][tab["dist"] > 8.0].mean() if (tab["dist"] > 8.0).any() else 0.0
        self.assertGreater(near, far)

    def test_aurc_sanity(self):
        tabs = self.build()
        p = D.cv_scores(tabs, "loso")
        rows, ci = D.evaluate(tabs, p, n_boot=20)
        r = {(x["site"], x["method"]): x for x in rows}
        pooled = {m: r[("POOLED", m)]["AURC"] for m in D.METHODS}
        base = r[("POOLED", "random")]["error_rate_full_coverage"]
        self.assertAlmostEqual(pooled["random"], base, delta=0.02)
        self.assertLess(pooled["distance"], pooled["random"])
        self.assertLess(pooled["combined"], pooled["random"])
        oracle = D.aurc(np.concatenate([tabs[s]["err"] for s in tabs]), np.concatenate([tabs[s]["err"] for s in tabs]))
        self.assertLessEqual(oracle, pooled["combined"] + 1e-9)

    def test_no_reference_leak_in_features(self):
        a = self.build()["s0"]
        # perturbing the reference must not change any decision-time feature
        v = self.tables["s0"]
        b = D.build_table("s0", v["z"], v["fine"] + 50 * np.random.default_rng(0).standard_normal(v["fine"].shape), v["rf"], 15.0)
        n = min(len(a["dist"]), len(b["dist"]))
        common = a["mask"] & b["mask"]
        fa = np.full(a["shape"], np.nan); fa[a["mask"]] = a["dist"]
        fb = np.full(b["shape"], np.nan); fb[b["mask"]] = b["dist"]
        np.testing.assert_allclose(fa[common], fb[common])

    def test_support_stress_non_divisible_shapes(self):
        for sup in (60, 90):
            tabs = self.build(support_m=sup)
            self.assertTrue(all(len(t["err"]) > 100 for t in tabs.values()), sup)

    def test_apply_to_site_and_vote_method(self):
        tabs = self.build()
        p = D.cv_scores(tabs, "loso")
        pool = D.pool(tabs)
        mdl = D.fit_logit(D._X(pool), pool["err"])
        v = self.tables["s0"]
        r = D.__dict__.get("apply") or None
        from src import experiment as E
        res = E.apply_to_site(v["z"], 30.0, 15.0, sorted(v["z"]), "cop-dem-glo-30", mdl, 0.5, -1.0)
        self.assertIsNotNone(res)
        self.assertTrue(set(np.unique(res["dec_combined"])) <= {0, 1, 2, 255})
        u = D.scores_for(pool, np.concatenate([p[s] for s in tabs]))
        self.assertIn("dem_slope_spread", u)

    def test_logit_recovers_signal(self):
        rng = np.random.default_rng(0)
        X = rng.standard_normal((5000, 3))
        y = (rng.random(5000) < 1 / (1 + np.exp(-(1.5 * X[:, 0] - 0.5)))).astype(float)
        m = D.fit_logit(X, y)
        p = D.predict_logit(m, X)
        self.assertGreater(np.corrcoef(p, y)[0, 1], 0.4)

    def test_choose_tau_and_decide(self):
        rng = np.random.default_rng(0)
        u = rng.random(2000); err = (rng.random(2000) < u * 0.5).astype(float)
        tau = D.choose_tau(u, err, 0.10)
        d = D.decide((rng.random(2000) > .5).astype(float), u, tau)
        self.assertTrue(set(np.unique(d)) <= {0, 1, 2})
        acc = u <= tau
        if acc.any():
            self.assertLessEqual(err[acc].mean(), 0.11)


if __name__ == "__main__":
    unittest.main()
