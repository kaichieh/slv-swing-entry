import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import pandas as pd

import refresh_active_status as ras


class RefreshActiveStatusTslaTests(unittest.TestCase):
    def test_build_tsla_prefers_live_xgboost_line_when_configured(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmpdir = Path(tmp)
            prediction_path = tmpdir / "tsla_latest_prediction_test.json"
            prediction_payload = {
                "live_operator_line_id": "xgboost_tb30_distance_live",
                "signal_summary": {
                    "signal": "bullish",
                    "predicted_probability": 0.8123,
                    "decision_threshold": 0.7,
                    "raw_model_signal": "bullish",
                },
                "latest_raw_date": "2026-04-15",
                "latest_close": 244.12,
                "model_extra_features": ["distance_to_252_high"],
                "model_summary": {
                    "model_family": "xgboost",
                    "label_mode": "future-return-top-bottom-30pct",
                    "reference_percentile_rule": "top_30pct",
                    "model_extra_features": ["distance_to_252_high"],
                    "xgboost_params": {
                        "n_estimators": 150,
                        "max_depth": 2,
                        "learning_rate": 0.05,
                    },
                },
            }
            prediction_path.write_text(json.dumps(prediction_payload), encoding="utf-8")

            signal_rows = pd.DataFrame(
                [
                    {"date": "2026-04-10", "signal": "no_entry"},
                    {"date": "2026-04-14", "signal": "weak_bullish"},
                    {
                        "date": "2026-04-15",
                        "signal": "bullish",
                        "raw_model_signal": "bullish",
                        "probability": 0.8123,
                        "threshold": 0.7,
                        "close": 244.12,
                    },
                ]
            )

            with patch.object(ras.ac, "get_live_model_family", return_value="xgboost"):
                with patch.object(ras.ac, "get_latest_prediction_path", return_value=prediction_path):
                    with patch.object(ras, "read_signal_rows_from_cache", return_value=signal_rows):
                        frame = ras.build_tsla(tmpdir)

        row = frame.loc[frame["preferred"] == True].iloc[0]
        self.assertEqual(row["line_id"], "xgboost_tb30_distance_live")
        self.assertEqual(row["role"], "execution_preference")
        self.assertTrue(bool(row["preferred"]))
        self.assertEqual(row["recent_selected_count"], 2)
        self.assertEqual(row["last_selected_date"], "2026-04-15")
        self.assertEqual(row["status"], "active")

    def test_build_tsla_raises_when_live_xgboost_provenance_does_not_match_config(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmpdir = Path(tmp)
            prediction_path = tmpdir / "tsla_latest_prediction_test.json"
            prediction_path.write_text(
                json.dumps(
                    {
                        "live_operator_line_id": "wrong_line_id",
                        "signal_summary": {
                            "signal": "bullish",
                            "predicted_probability": 0.8123,
                            "decision_threshold": 0.7,
                            "raw_model_signal": "bullish",
                        },
                        "latest_raw_date": "2026-04-15",
                        "latest_close": 244.12,
                        "model_extra_features": ["distance_to_252_high"],
                        "model_summary": {
                            "model_family": "xgboost",
                            "label_mode": "future-return-top-bottom-30pct",
                            "reference_percentile_rule": "top_30pct",
                            "model_extra_features": ["distance_to_252_high"],
                            "xgboost_params": {
                                "n_estimators": 200,
                                "max_depth": 2,
                                "learning_rate": 0.05,
                            },
                        },
                    }
                ),
                encoding="utf-8",
            )

            signal_rows = pd.DataFrame(
                [
                    {"date": "2026-04-10", "signal": "no_entry"},
                    {"date": "2026-04-15", "signal": "bullish", "probability": 0.8123, "threshold": 0.7, "close": 244.12},
                ]
            )

            with patch.object(ras.ac, "get_live_model_family", return_value="xgboost"):
                with patch.object(ras.ac, "get_latest_prediction_path", return_value=prediction_path):
                    with patch.object(ras, "read_signal_rows_from_cache", return_value=signal_rows):
                        with self.assertRaisesRegex(ValueError, "TSLA preferred line .*cannot be validated"):
                            ras.build_tsla(tmpdir)

    def test_build_tsla_raises_when_live_xgboost_cache_omits_explicit_operator_line_id(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmpdir = Path(tmp)
            prediction_path = tmpdir / "tsla_latest_prediction_test.json"
            prediction_path.write_text(
                json.dumps(
                    {
                        "signal_summary": {
                            "signal": "bullish",
                            "predicted_probability": 0.8123,
                            "decision_threshold": 0.7,
                            "raw_model_signal": "bullish",
                            "confidence_gap": 0.1123,
                        },
                        "buy_point_summary": {
                            "buy_point_ok": True,
                            "buy_point_warnings": [],
                        },
                        "rule_summary": {
                            "selected": True,
                            "cutoff": 0.8011,
                            "rule_name": "top_30pct_reference",
                            "percentile_rank": 0.9555,
                        },
                        "rationale_summary": {
                            "model_reasons": ["reason"],
                            "rule_reason": "rule rationale",
                        },
                        "latest_raw_date": "2026-04-15",
                        "latest_close": 244.12,
                        "model_extra_features": ["distance_to_252_high"],
                        "latest_feature_snapshot": {
                            "ret_20": -0.0444,
                            "ret_60": 0.1666,
                            "drawdown_20": -0.0999,
                            "sma_gap_20": 0.0222,
                            "sma_gap_60": 0.0555,
                            "volume_vs_20": 1.4444,
                            "rsi_14": 41.23,
                        },
                        "model_summary": {
                            "model_family": "xgboost",
                            "label_mode": "future-return-top-bottom-30pct",
                            "reference_percentile_rule": "top_30pct",
                            "model_extra_features": ["distance_to_252_high"],
                            "xgboost_params": {
                                "n_estimators": 150,
                                "max_depth": 2,
                                "learning_rate": 0.05,
                            },
                        },
                    }
                ),
                encoding="utf-8",
            )

            signal_rows = pd.DataFrame(
                [
                    {"date": "2026-04-10", "signal": "no_entry"},
                    {
                        "date": "2026-04-15",
                        "close": 244.12,
                        "signal": "bullish",
                        "raw_model_signal": "bullish",
                        "buy_point_ok": True,
                        "buy_point_warnings": "",
                        "probability": 0.8123,
                        "threshold": 0.7,
                        "confidence_gap": 0.1123,
                        "rule_selected": True,
                        "rule_cutoff": 0.8011,
                        "rule_name": "top_30pct_reference",
                        "percentile_rank": 0.9555,
                        "model_rationale": "reason",
                        "rule_rationale": "rule rationale",
                        "ret_20": -0.0444,
                        "ret_60": 0.1666,
                        "drawdown_20": -0.0999,
                        "sma_gap_20": 0.0222,
                        "sma_gap_60": 0.0555,
                        "volume_vs_20": 1.4444,
                        "rsi_14": 41.23,
                    },
                ]
            )

            with patch.object(ras.ac, "get_live_model_family", return_value="xgboost"):
                with patch.object(ras.ac, "get_latest_prediction_path", return_value=prediction_path):
                    with patch.object(ras, "read_signal_rows_from_cache", return_value=signal_rows):
                        with self.assertRaisesRegex(ValueError, "TSLA preferred line .*cannot be validated"):
                            ras.build_tsla(tmpdir)

    def test_build_tsla_raises_when_latest_signal_row_drifts_from_live_payload(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmpdir = Path(tmp)
            prediction_path = tmpdir / "tsla_latest_prediction_test.json"
            prediction_path.write_text(
                json.dumps(
                    {
                        "live_operator_line_id": "xgboost_tb30_distance_live",
                        "signal_summary": {
                            "signal": "bullish",
                            "predicted_probability": 0.8123,
                            "decision_threshold": 0.7,
                            "raw_model_signal": "bullish",
                            "confidence_gap": 0.1123,
                        },
                        "buy_point_summary": {
                            "buy_point_ok": True,
                            "buy_point_warnings": [],
                        },
                        "rule_summary": {
                            "selected": True,
                            "cutoff": 0.8011,
                            "rule_name": "top_30pct_reference",
                            "percentile_rank": 0.9555,
                        },
                        "rationale_summary": {
                            "model_reasons": ["fresh rationale"],
                            "rule_reason": "fresh rule rationale",
                        },
                        "latest_raw_date": "2026-04-15",
                        "latest_close": 244.12,
                        "model_extra_features": ["distance_to_252_high"],
                        "latest_feature_snapshot": {
                            "ret_20": -0.0444,
                            "ret_60": 0.1666,
                            "drawdown_20": -0.0999,
                            "sma_gap_20": 0.0222,
                            "sma_gap_60": 0.0555,
                            "volume_vs_20": 1.4444,
                            "rsi_14": 41.23,
                        },
                        "model_summary": {
                            "model_family": "xgboost",
                            "label_mode": "future-return-top-bottom-30pct",
                            "reference_percentile_rule": "top_30pct",
                            "model_extra_features": ["distance_to_252_high"],
                            "xgboost_params": {
                                "n_estimators": 150,
                                "max_depth": 2,
                                "learning_rate": 0.05,
                            },
                        },
                    }
                ),
                encoding="utf-8",
            )

            signal_rows = pd.DataFrame(
                [
                    {"date": "2026-04-10", "signal": "no_entry"},
                    {
                        "date": "2026-04-15",
                        "close": 244.12,
                        "signal": "bullish",
                        "raw_model_signal": "bullish",
                        "buy_point_ok": True,
                        "buy_point_warnings": "",
                        "probability": 0.8123,
                        "threshold": 0.7,
                        "confidence_gap": 0.0123,
                        "rule_selected": True,
                        "rule_cutoff": 0.7555,
                        "rule_name": "top_30pct_reference",
                        "percentile_rank": 0.8111,
                        "model_rationale": "stale rationale",
                        "rule_rationale": "stale rule rationale",
                        "ret_20": -0.0111,
                        "ret_60": 0.1222,
                        "drawdown_20": -0.0444,
                        "sma_gap_20": 0.0999,
                        "sma_gap_60": 0.1111,
                        "volume_vs_20": 0.8888,
                        "rsi_14": 58.88,
                    },
                ]
            )

            with patch.object(ras.ac, "get_live_model_family", return_value="xgboost"):
                with patch.object(ras.ac, "get_latest_prediction_path", return_value=prediction_path):
                    with patch.object(ras, "read_signal_rows_from_cache", return_value=signal_rows):
                        with self.assertRaisesRegex(ValueError, "Latest signal cache drift detected for tsla"):
                            ras.build_tsla(tmpdir)


if __name__ == "__main__":
    unittest.main()
