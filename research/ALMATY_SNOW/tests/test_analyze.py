import unittest
import numpy as np
import pandas as pd
from src.analyze import season_table, monthly_table


class T(unittest.TestCase):
    def setUp(self):
        dates = pd.date_range("2019-09-01", "2020-05-31")
        snow = ((dates >= "2019-12-01") & (dates <= "2020-03-01"))
        self.df = pd.DataFrame({"date": dates.strftime("%Y-%m-%d"), "band": 1, "band_px": 100,
                                "clear_px": 80, "snow_px": np.where(snow, 72, 0)})

    def test_season(self):
        t = season_table(self.df)
        self.assertEqual(len(t), 1)
        r = t.iloc[0]
        self.assertEqual(r["onset_date"], "2019-12-01")
        self.assertEqual(r["end_date"], "2020-03-01")
        self.assertTrue(bool(r["accepted"]))
        self.assertEqual(int(r["span_days"]), 91)

    def test_monthly(self):
        m = monthly_table(self.df)
        jan = m[(m.year == 2020) & (m.month == 1)].iloc[0]
        self.assertAlmostEqual(jan["snow_freq_of_clear"], 0.9)


if __name__ == "__main__":
    unittest.main()
