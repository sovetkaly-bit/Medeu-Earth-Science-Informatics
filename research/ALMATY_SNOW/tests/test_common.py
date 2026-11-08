import unittest
import numpy as np
import pandas as pd
from src.common import assign_bands, season_of, snow_run_dates, theil_sen_mk


class T(unittest.TestCase):
    def test_bands(self):
        e = np.array([500.0, 600.0, 999.9, 1000.0, 3600.0, np.nan])
        b = assign_bands(e, [[600, 1000], [1000, 1500], [3500, 5000]])
        self.assertEqual(b.tolist(), [0, 1, 1, 2, 3, 0])

    def test_season(self):
        self.assertEqual(season_of(pd.Timestamp("2020-10-05")), 2020)
        self.assertEqual(season_of(pd.Timestamp("2021-02-05")), 2020)
        self.assertIsNone(season_of(pd.Timestamp("2021-07-01")))

    def test_run(self):
        dates = pd.date_range("2020-09-01", "2021-05-31")
        frac = np.zeros(len(dates))
        clear = np.ones(len(dates))
        on = (dates >= "2020-11-20") & (dates <= "2021-03-10")
        frac[on] = 0.9
        # one cloudy gap inside the snow period must not break the run
        gap = (dates >= "2020-12-10") & (dates <= "2020-12-20")
        clear[gap] = 0.0
        a, b = snow_run_dates(dates, frac, clear, 0.3, 0.5, 3, 10)
        self.assertEqual(a, pd.Timestamp("2020-11-20"))
        self.assertEqual(b, pd.Timestamp("2021-03-10"))

    def test_run_none(self):
        dates = pd.date_range("2020-09-01", "2020-12-31")
        a, b = snow_run_dates(dates, np.zeros(len(dates)), np.ones(len(dates)), 0.3, 0.5, 3, 10)
        self.assertIsNone(a)

    def test_trend(self):
        yrs = np.arange(2001, 2021)
        r = theil_sen_mk(yrs, 100 + 2.0 * (yrs - 2001))
        self.assertAlmostEqual(r["slope_per_10y"], 20.0, places=6)
        self.assertLess(r["p"], 0.001)
        self.assertIsNone(theil_sen_mk(yrs[:5], yrs[:5]))


if __name__ == "__main__":
    unittest.main()
