from __future__ import annotations

import unittest

import pandas as pd

import refresh_mu_subregime_report as report


class SummarizeReturnsTests(unittest.TestCase):
    def test_summarize_returns_tracks_outlier_sensitivity(self) -> None:
        values = pd.Series([0.10, 0.20, -0.30, 0.80], dtype=float)
        summary = report.summarize_returns(values)

        self.assertEqual(summary["count"], 4)
        self.assertAlmostEqual(summary["avg_future_return_60"], 0.20)
        self.assertAlmostEqual(summary["median_future_return_60"], 0.15)
        self.assertAlmostEqual(summary["hit_rate"], 0.75)
        self.assertAlmostEqual(summary["avg_future_return_60_ex_best"], 0.0)
        self.assertAlmostEqual(summary["max_future_return_60"], 0.80)


class AssessChallengerCaseTests(unittest.TestCase):
    def test_assess_challenger_case_rejects_dirty_bucket(self) -> None:
        verdict, note = report.assess_challenger_case(
            {
                "count": 12,
                "avg_future_return_60": 0.12,
                "hit_rate": 0.50,
                "avg_future_return_60_ex_best": 0.08,
            },
            {"count": 3, "avg_future_return_60": 0.15, "hit_rate": 1.0},
            {"count": 40, "avg_future_return_60": 0.06, "hit_rate": 0.55},
        )

        self.assertEqual(verdict, "not_clean_enough")
        self.assertIn("below 60%", note)

    def test_assess_challenger_case_flags_outlier_sensitivity(self) -> None:
        verdict, _ = report.assess_challenger_case(
            {
                "count": 12,
                "avg_future_return_60": 0.20,
                "hit_rate": 0.75,
                "avg_future_return_60_ex_best": 0.04,
            },
            {"count": 0, "avg_future_return_60": 0.0, "hit_rate": 0.0},
            {"count": 40, "avg_future_return_60": 0.06, "hit_rate": 0.55},
        )

        self.assertEqual(verdict, "outlier_sensitive")


if __name__ == "__main__":
    unittest.main()
