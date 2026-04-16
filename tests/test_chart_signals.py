from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import chart_signals as cs
import numpy as np
import pandas as pd


class ChartSignalsPayloadTests(unittest.TestCase):
    def test_build_chart_rows_builds_live_features_with_vix_pipeline(self) -> None:
        live_features = pd.DataFrame(
            [
                {
                    "date": pd.Timestamp("2026-04-15"),
                    "open": 100.0,
                    "high": 102.0,
                    "low": 99.0,
                    "close": 101.0,
                    "baseline_feature": 1.0,
                    "vix_close_lag1": 22.0,
                }
            ]
        )
        splits = {
            "test": mock.Mock(frame=pd.DataFrame({"date": [pd.Timestamp("2026-03-31")]})),
        }
        model_artifacts = {
            "model_family": "logistic",
            "threshold": 0.5,
            "train_frame": pd.DataFrame({"baseline_feature": [1.0], "vix_close_lag1": [20.0]}),
            "feature_names": ["baseline_feature", "vix_close_lag1"],
            "default_interactions": [],
        }

        with mock.patch.object(cs.tr, "set_seed"):
            with mock.patch.object(cs.tr, "get_env_int", return_value=cs.tr.SEED):
                with mock.patch.object(cs, "download_asset_prices", return_value="raw_prices"):
                    with mock.patch.object(cs, "add_price_features", return_value="price_features"):
                        with mock.patch.object(cs, "add_relative_strength_features", return_value="relative_features"):
                            with mock.patch.object(cs, "add_context_features", return_value="context_features"):
                                with mock.patch.object(cs, "download_vix_prices", return_value="vix_prices", create=True) as download_vix_prices:
                                    with mock.patch.object(cs, "add_vix_features", return_value=live_features, create=True) as add_vix_features:
                                        with mock.patch.object(cs, "load_splits", return_value=splits):
                                            with mock.patch.object(cs, "build_feature_names", return_value=["baseline_feature", "vix_close_lag1"]):
                                                with mock.patch.object(cs, "fit_model", return_value=model_artifacts):
                                                    with mock.patch.object(cs, "build_history_probabilities", return_value=np.array([0.2, 0.4], dtype=np.float32)):
                                                        with mock.patch.object(cs, "get_rule_top_pct", return_value=20.0):
                                                            score_latest_row = mock.Mock(
                                                                return_value=(
                                                                    np.array([[1.0]], dtype=np.float32),
                                                                    {"baseline_feature": 1.0, "vix_close_lag1": 22.0},
                                                                )
                                                            )
                                                            with mock.patch.object(cs, "score_latest_row", score_latest_row):
                                                                with mock.patch.object(cs, "predict_probabilities", return_value=np.array([0.7], dtype=np.float32)):
                                                                    with mock.patch.object(cs, "classify_signal", return_value=("bullish", {"confidence_gap": 0.2})):
                                                                        with mock.patch.object(cs, "apply_buy_point_overlay", return_value=("bullish", {"buy_point_ok": True, "buy_point_warnings": []})):
                                                                            with mock.patch.object(cs, "summarize_rule", return_value={"selected": True, "cutoff": 0.6, "rule_name": "top_20pct_reference", "percentile_rank": 0.9}):
                                                                                with mock.patch.object(cs, "build_model_rationale", return_value=["reason"]):
                                                                                    with mock.patch.object(cs, "build_rule_rationale", return_value="rule rationale"):
                                                                                        rows, meta = cs.build_chart_rows(lookback_days=5)

        download_vix_prices.assert_called_once_with()
        add_vix_features.assert_called_once_with("context_features", "vix_prices")
        pd.testing.assert_frame_equal(score_latest_row.call_args.args[3], live_features)
        self.assertEqual(rows[0]["signal"], "bullish")
        self.assertEqual(meta["latest_date"], "2026-04-15")

    def test_build_chart_payload_exposes_algorithm_metadata(self) -> None:
        rows = [
            {
                "date": "2026-04-14",
                "close": 445.09,
                "signal": "no_entry",
                "raw_model_signal": "weak_bullish",
                "buy_point_ok": False,
                "buy_point_warnings": "RSI too extended",
                "probability": 0.49,
                "confidence_gap": 0.004,
                "rule_selected": False,
                "rule_name": "top_20pct_reference",
                "rule_cutoff": 0.5002,
                "model_rationale": "14-day RSI is extended",
                "rule_rationale": "Below historical top 20% cutoff",
                "ret_20": -0.0333,
                "ret_60": 0.0514,
                "drawdown_20": -0.0309,
                "sma_gap_20": 0.0417,
                "rsi_14": 70.91,
            }
        ]
        meta = {
            "latest_date": "2026-04-14",
            "lookback_days": 1260,
            "signal_colors": {"no_entry": "#9ca3af"},
            "rule_top_pct": 20.0,
        }

        with mock.patch.object(cs.ac, "get_asset_key", return_value="gld"):
            with mock.patch.object(cs.ac, "get_asset_symbol", return_value="GLD"):
                with mock.patch.object(
                    cs.ac,
                    "load_asset_config",
                    return_value={
                        "asset_key": "gld",
                        "symbol": "GLD",
                        "live_model_family": "hard_gate_two_expert_mixed",
                        "live_label_mode": "future-return-top-bottom-10pct",
                        "default_chart_signal_mode": "execution",
                    },
                ):
                    payload = cs.build_chart_payload(rows, meta)

        self.assertEqual(payload["variant"], "signal")
        self.assertEqual(payload["title"], "GLD hard_gate_two_expert_mixed")
        self.assertEqual(
            payload["subtitle"],
            "Generated date: 2026-04-14 · Latest date: 2026-04-14 · Lookback: 1260",
        )
        self.assertEqual(payload["algorithm_name"], "hard_gate_two_expert_mixed")
        self.assertEqual(payload["label_mode"], "future-return-top-bottom-10pct")
        self.assertEqual(payload["default_chart_signal_mode"], "execution")
        self.assertEqual(payload["generated_date"], "2026-04-14")
        self.assertEqual(payload["reference_rule"], "top_20pct_reference")
        self.assertEqual(payload["legend"], {"no_entry": "#9ca3af"})
        self.assertEqual(payload["rows"], rows)

    def test_sync_latest_row_from_latest_prediction_payload(self) -> None:
        rows = [
            {
                "date": "2026-04-14",
                "close": 440.11,
                "signal": "no_entry",
                "raw_model_signal": "weak_bullish",
                "probability": 0.4012,
                "threshold": 0.4555,
            },
            {
                "date": "2026-04-15",
                "close": 445.09,
                "signal": "weak_bullish",
                "raw_model_signal": "bullish",
                "probability": 0.6501,
                "threshold": 0.4101,
                "buy_point_ok": False,
                "buy_point_warnings": "old warning",
                "confidence_gap": 0.24,
                "rule_selected": False,
                "rule_cutoff": 0.6555,
                "rule_name": "top_20pct_reference",
                "percentile_rank": 0.88,
                "model_rationale": "old rationale",
                "rule_rationale": "old rule rationale",
                "ret_20": -0.05,
                "ret_60": 0.02,
                "drawdown_20": -0.08,
                "sma_gap_20": 0.03,
                "volume_vs_20": 1.1,
                "rsi_14": 61.2,
            },
        ]
        payload = {
            "latest_raw_date": "2026-04-16",
            "latest_close": 447.126,
            "signal_summary": {
                "signal": "bullish",
                "raw_model_signal": "strong_bullish",
                "predicted_probability": 0.71234,
                "decision_threshold": 0.48888,
                "confidence_gap": 0.22345,
            },
            "buy_point_summary": {
                "buy_point_ok": True,
                "buy_point_warnings": ["RSI cooled off", "drawdown reset"],
            },
            "rule_summary": {
                "selected": True,
                "cutoff": 0.70123,
                "rule_name": "top_20pct_reference",
                "percentile_rank": 0.95555,
            },
            "rationale_summary": {
                "model_reasons": ["reason one", "reason two"],
                "rule_reason": "Entered the historical top 20% bucket",
            },
            "latest_feature_snapshot": {
                "ret_20": -0.01234,
                "ret_60": 0.12345,
                "drawdown_20": -0.09876,
                "sma_gap_20": 0.03456,
                "sma_gap_60": -0.22222,
                "volume_vs_20": 1.23456,
                "rsi_14": 48.7654,
            },
        }

        with tempfile.TemporaryDirectory() as tmp:
            prediction_path = Path(tmp) / "latest_prediction.json"
            prediction_path.write_text(json.dumps(payload), encoding="utf-8")

            with mock.patch.object(cs.ac, "get_latest_prediction_path", return_value=prediction_path):
                synced_rows = cs.synchronize_latest_signal_row(rows)

        self.assertEqual(synced_rows[0], rows[0])
        self.assertEqual(synced_rows[-1]["date"], "2026-04-16")
        self.assertEqual(synced_rows[-1]["signal"], "bullish")
        self.assertEqual(synced_rows[-1]["raw_model_signal"], "strong_bullish")
        self.assertTrue(bool(synced_rows[-1]["buy_point_ok"]))
        self.assertEqual(synced_rows[-1]["buy_point_warnings"], "RSI cooled off | drawdown reset")
        self.assertEqual(synced_rows[-1]["probability"], 0.7123)
        self.assertEqual(synced_rows[-1]["threshold"], 0.4889)
        self.assertEqual(synced_rows[-1]["confidence_gap"], 0.2235)
        self.assertEqual(synced_rows[-1]["close"], 447.13)
        self.assertTrue(bool(synced_rows[-1]["rule_selected"]))
        self.assertEqual(synced_rows[-1]["rule_cutoff"], 0.7012)
        self.assertEqual(synced_rows[-1]["rule_name"], "top_20pct_reference")
        self.assertEqual(synced_rows[-1]["percentile_rank"], 0.9556)
        self.assertEqual(synced_rows[-1]["model_rationale"], "reason one | reason two")
        self.assertEqual(synced_rows[-1]["rule_rationale"], "Entered the historical top 20% bucket")
        self.assertEqual(synced_rows[-1]["ret_20"], -0.0123)
        self.assertEqual(synced_rows[-1]["ret_60"], 0.1235)
        self.assertEqual(synced_rows[-1]["drawdown_20"], -0.0988)
        self.assertEqual(synced_rows[-1]["sma_gap_20"], 0.0346)
        self.assertEqual(synced_rows[-1]["sma_gap_60"], -0.2222)
        self.assertEqual(synced_rows[-1]["volume_vs_20"], 1.2346)
        self.assertEqual(synced_rows[-1]["rsi_14"], 48.77)

    def test_main_writes_synchronized_rows_and_chart_payload_rows(self) -> None:
        chart_rows = [
            {
                "date": "2026-04-14",
                "close": 440.11,
                "signal": "no_entry",
                "raw_model_signal": "weak_bullish",
                "probability": 0.4012,
                "threshold": 0.4555,
            },
            {
                "date": "2026-04-15",
                "close": 445.09,
                "signal": "weak_bullish",
                "raw_model_signal": "bullish",
                "probability": 0.6501,
                "threshold": 0.4101,
            },
        ]
        meta = {
            "latest_date": "2026-04-15",
            "lookback_days": 2,
            "signal_colors": {"no_entry": "#9ca3af"},
            "rule_top_pct": 20.0,
        }
        payload = {
            "latest_raw_date": "2026-04-16",
            "latest_close": 447.12,
            "signal_summary": {
                "signal": "bullish",
                "raw_model_signal": "strong_bullish",
                "predicted_probability": 0.7123,
                "decision_threshold": 0.4889,
                "confidence_gap": 0.2234,
            },
            "buy_point_summary": {
                "buy_point_ok": True,
                "buy_point_warnings": ["RSI cooled off"],
            },
            "rule_summary": {
                "selected": True,
                "cutoff": 0.7012,
                "rule_name": "top_20pct_reference",
                "percentile_rank": 0.9555,
            },
            "rationale_summary": {
                "model_reasons": ["reason one", "reason two"],
                "rule_reason": "Entered the historical top 20% bucket",
            },
            "latest_feature_snapshot": {
                "ret_20": -0.0123,
                "ret_60": 0.1234,
                "drawdown_20": -0.0987,
                "sma_gap_20": 0.0345,
                "sma_gap_60": -0.2222,
                "volume_vs_20": 1.2345,
                "rsi_14": 48.7654,
            },
        }

        with tempfile.TemporaryDirectory() as tmp:
            prediction_path = Path(tmp) / "latest_prediction.json"
            rows_output_path = Path(tmp) / "signal_rows.tsv"
            chart_output_path = Path(tmp) / "signal_chart.html"
            prediction_path.write_text(json.dumps(payload), encoding="utf-8")

            with mock.patch.object(cs, "OUTPUT_PATH", str(chart_output_path)):
                with mock.patch.object(cs, "ROWS_OUTPUT_PATH", str(rows_output_path)):
                    with mock.patch.object(cs, "build_chart_rows", return_value=(chart_rows, meta)):
                        with mock.patch.object(cs.ac, "get_latest_prediction_path", return_value=prediction_path):
                            with mock.patch.object(cs, "build_html", return_value="<html></html>") as build_html:
                                cs.main()
                written_rows = cs.pd.read_csv(rows_output_path, sep="\t")
                self.assertEqual(str(written_rows.iloc[-1]["date"]), "2026-04-16")
                self.assertEqual(str(written_rows.iloc[-1]["signal"]), "bullish")
                self.assertEqual(str(written_rows.iloc[-1]["raw_model_signal"]), "strong_bullish")
                self.assertTrue(bool(written_rows.iloc[-1]["buy_point_ok"]))
                self.assertEqual(str(written_rows.iloc[-1]["buy_point_warnings"]), "RSI cooled off")
                self.assertEqual(round(float(written_rows.iloc[-1]["probability"]), 4), 0.7123)
                self.assertEqual(round(float(written_rows.iloc[-1]["threshold"]), 4), 0.4889)
                self.assertEqual(round(float(written_rows.iloc[-1]["confidence_gap"]), 4), 0.2234)
                self.assertEqual(round(float(written_rows.iloc[-1]["close"]), 2), 447.12)
                self.assertTrue(bool(written_rows.iloc[-1]["rule_selected"]))
                self.assertEqual(round(float(written_rows.iloc[-1]["rule_cutoff"]), 4), 0.7012)
                self.assertEqual(str(written_rows.iloc[-1]["rule_name"]), "top_20pct_reference")
                self.assertEqual(round(float(written_rows.iloc[-1]["percentile_rank"]), 4), 0.9555)
                self.assertEqual(str(written_rows.iloc[-1]["model_rationale"]), "reason one | reason two")
                self.assertEqual(str(written_rows.iloc[-1]["rule_rationale"]), "Entered the historical top 20% bucket")
                self.assertEqual(round(float(written_rows.iloc[-1]["ret_20"]), 4), -0.0123)
                self.assertEqual(round(float(written_rows.iloc[-1]["ret_60"]), 4), 0.1234)
                self.assertEqual(round(float(written_rows.iloc[-1]["drawdown_20"]), 4), -0.0987)
                self.assertEqual(round(float(written_rows.iloc[-1]["sma_gap_20"]), 4), 0.0345)
                self.assertEqual(round(float(written_rows.iloc[-1]["sma_gap_60"]), 4), -0.2222)
                self.assertEqual(round(float(written_rows.iloc[-1]["volume_vs_20"]), 4), 1.2345)
                self.assertEqual(round(float(written_rows.iloc[-1]["rsi_14"]), 2), 48.77)
                expected_rows = cs.synchronize_latest_signal_row(chart_rows, payload)
                build_html.assert_called_once_with(expected_rows, meta)


if __name__ == "__main__":
    unittest.main()
