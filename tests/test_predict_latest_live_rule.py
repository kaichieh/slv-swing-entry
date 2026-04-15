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

    def test_get_live_model_family_defaults_to_logistic(self) -> None:
        with mock.patch.object(pl.ac, "get_live_model_family", return_value="logistic"):
            self.assertEqual(pl.get_live_model_family(), "logistic")

    def test_get_live_model_family_rejects_unknown_value(self) -> None:
        with mock.patch.object(pl.ac, "get_live_model_family", return_value="svm"):
            with self.assertRaisesRegex(ValueError, "Unsupported live_model_family"):
                pl.get_live_model_family()

    def test_get_live_model_family_accepts_hard_gate_two_expert_mixed(self) -> None:
        with mock.patch.object(pl.ac, "get_live_model_family", return_value="hard_gate_two_expert_mixed"):
            self.assertEqual(pl.get_live_model_family(), "hard_gate_two_expert_mixed")

    def test_fit_model_uses_xgboost_path_when_configured(self) -> None:
        fake_splits = {"train": mock.Mock(), "validation": mock.Mock(), "test": mock.Mock()}
        expected = {"model_family": "xgboost", "threshold": 0.7}
        with mock.patch.object(pl, "get_live_model_family", return_value="xgboost"):
            with mock.patch.object(pl, "fit_xgboost_model", return_value=expected) as fit_xgboost:
                result = pl.fit_model(fake_splits, ["distance_to_252_high"])

        self.assertIs(result, expected)
        fit_xgboost.assert_called_once_with(fake_splits, ["distance_to_252_high"])

    def test_fit_model_uses_hard_gate_two_expert_mixed_path_when_configured(self) -> None:
        fake_splits = {"train": mock.Mock(), "validation": mock.Mock(), "test": mock.Mock()}
        fake_prices = mock.Mock()
        expected = {"model_family": "hard_gate_two_expert_mixed", "threshold": 0.51}
        with mock.patch.object(pl, "get_live_model_family", return_value="hard_gate_two_expert_mixed"):
            with mock.patch.object(pl, "fit_hard_gate_two_expert_mixed_model", return_value=expected) as fit_mixed:
                result = pl.fit_model(fake_splits, ["distance_to_252_high"], raw_prices=fake_prices)

        self.assertIs(result, expected)
        fit_mixed.assert_called_once_with(fake_prices)

    def test_predict_probabilities_uses_xgboost_classifier_predict_proba(self) -> None:
        model = mock.Mock()
        model.predict_proba.return_value = np.array([[0.4, 0.6], [0.3, 0.7]], dtype=np.float32)
        artifacts = {"model_family": "xgboost", "model": model}

        with mock.patch.object(pl, "require_xgboost", return_value=mock.Mock(DMatrix=None)):
            probabilities = pl.predict_probabilities(artifacts, np.ones((2, 1), dtype=np.float32))

        np.testing.assert_allclose(probabilities, np.array([0.6, 0.7], dtype=np.float32))


if __name__ == "__main__":
    unittest.main()
