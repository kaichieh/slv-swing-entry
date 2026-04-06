from __future__ import annotations

import unittest
from unittest import mock

import numpy as np

import predict_latest as pl


class PredictLatestLiveRuleTests(unittest.TestCase):
    def test_get_rule_top_pct_prefers_asset_config(self) -> None:
        with mock.patch.object(pl.ac, "load_asset_config", return_value={"live_reference_top_pct": 7.5}):
            self.assertEqual(pl.get_rule_top_pct(), 7.5)

    def test_get_rule_top_pct_uses_default_when_missing(self) -> None:
        with mock.patch.object(pl.ac, "load_asset_config", return_value={}):
            self.assertEqual(pl.get_rule_top_pct(), pl.RULE_TOP_PCT)

    def test_summarize_rule_uses_requested_percentile(self) -> None:
        history = np.array([0.10, 0.20, 0.30, 0.40], dtype=np.float64)
        summary = pl.summarize_rule(0.40, history, top_pct=25.0)
        self.assertEqual(summary["rule_name"], "top_25pct_reference")
        self.assertTrue(summary["selected"])

    def test_build_rule_rationale_uses_rule_name_percentile(self) -> None:
        rule_summary = {
            "rule_name": "top_7.5pct_reference",
            "selected": False,
        }
        text = pl.build_rule_rationale(0.51, 0.50, rule_summary)
        self.assertIn("7.5%", text)


if __name__ == "__main__":
    unittest.main()
