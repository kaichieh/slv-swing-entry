from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import pandas as pd

import refresh_active_status as ras


class RefreshActiveStatusSlvNvdaTests(unittest.TestCase):
    def test_build_slv_promotes_gdx_hard_gate_breakthrough(self) -> None:
        slv_config = {
            "live_operator_line_id": "custom_slv_live_line",
            "live_model_family": "custom_hard_gate_family",
            "live_label_mode": "future-return-top-bottom-9pct",
            "benchmark_symbol": "GDX",
        }
        with tempfile.TemporaryDirectory() as tmp:
            asset_dir = Path(tmp)
            cache_dir = asset_dir / ".cache"
            cache_dir.mkdir()

            payload = {
                "latest_raw_date": "2026-04-15",
                "live_operator_line_id": "custom_slv_live_line",
                "signal_summary": {
                    "signal": "bullish",
                    "predicted_probability": 0.9607,
                    "decision_threshold": 0.9399,
                },
                "model_summary": {
                    "model_family": "custom_hard_gate_family",
                    "label_mode": "future-return-top-bottom-9pct",
                    "reference_percentile_rule": "top_15pct",
                },
                "live_provenance": {
                    "benchmark_symbol": "GDX",
                    "outer_gate_feature": "price_ratio_benchmark_z_20",
                    "operator_line_id": "custom_slv_live_line",
                },
                "model_extra_features": ["price_ratio_benchmark_z_20"],
            }
            (cache_dir / "latest_prediction.json").write_text(json.dumps(payload), encoding="utf-8")
            pd.DataFrame(
                [
                    {"date": "2026-04-14", "signal": "no_entry"},
                    {
                        "date": "2026-04-15",
                        "signal": "bullish",
                        "probability": 0.9607,
                        "threshold": 0.9399,
                    },
                ]
            ).to_csv(cache_dir / "signal_rows.tsv", sep="\t", index=False)

            with mock.patch.object(ras.ac, "get_latest_prediction_path", return_value=cache_dir / "latest_prediction.json"):
                with mock.patch.object(ras.ac, "load_asset_config", return_value=slv_config):
                    frame = ras.build_slv(asset_dir)

        row = frame.loc[frame["preferred"] == True].iloc[0]
        self.assertEqual(row["line_id"], "custom_slv_live_line")
        self.assertEqual(row["role"], "primary")
        self.assertTrue(bool(row["preferred"]))
        self.assertIn("GDX", str(row["usage_note"]))

    def test_slv_live_cache_matches_preferred_line_uses_config_and_benchmark_provenance(self) -> None:
        payload = {
            "live_operator_line_id": "custom_slv_live_line",
            "model_summary": {
                "model_family": "custom_hard_gate_family",
                "label_mode": "future-return-top-bottom-9pct",
            },
            "live_provenance": {
                "benchmark_symbol": "GDX",
                "outer_gate_feature": "price_ratio_benchmark_z_20",
                "operator_line_id": "custom_slv_live_line",
            },
        }
        slv_config = {
            "live_operator_line_id": "custom_slv_live_line",
            "live_model_family": "custom_hard_gate_family",
            "live_label_mode": "future-return-top-bottom-9pct",
            "benchmark_symbol": "GDX",
        }

        self.assertTrue(ras.slv_live_cache_matches_preferred_line(payload, slv_config))

    def test_slv_live_cache_rejects_when_benchmark_provenance_is_missing(self) -> None:
        payload = {
            "live_operator_line_id": "hard_gate_two_expert_gdx_live",
            "model_summary": {
                "model_family": "hard_gate_two_expert",
                "label_mode": "future-return-top-bottom-15pct",
            },
            "live_provenance": {
                "operator_line_id": "hard_gate_two_expert_gdx_live",
            },
        }
        slv_config = {
            "live_operator_line_id": "hard_gate_two_expert_gdx_live",
            "live_model_family": "hard_gate_two_expert",
            "live_label_mode": "future-return-top-bottom-15pct",
            "benchmark_symbol": "GDX",
        }

        self.assertFalse(ras.slv_live_cache_matches_preferred_line(payload, slv_config))

    def test_build_slv_raises_when_live_cache_provenance_is_not_the_adopted_hard_gate_path(self) -> None:
        slv_config = {
            "live_operator_line_id": "hard_gate_two_expert_gdx_live",
            "live_model_family": "hard_gate_two_expert",
            "live_label_mode": "future-return-top-bottom-15pct",
            "benchmark_symbol": "GDX",
        }
        with tempfile.TemporaryDirectory() as tmp:
            asset_dir = Path(tmp)
            cache_dir = asset_dir / ".cache"
            cache_dir.mkdir()

            payload = {
                "latest_raw_date": "2026-04-15",
                "live_operator_line_id": "baseline_live_cache",
                "signal_summary": {
                    "signal": "bullish",
                    "predicted_probability": 0.9607,
                    "decision_threshold": 0.9399,
                },
                "model_summary": {
                    "model_family": "logistic",
                    "label_mode": "drop-neutral",
                    "reference_percentile_rule": "top_20pct",
                },
                "live_provenance": {
                    "benchmark_symbol": "GDX",
                    "outer_gate_feature": "price_ratio_benchmark_z_20",
                    "operator_line_id": "baseline_live_cache",
                },
                "model_extra_features": ["ret_60"],
            }
            (cache_dir / "latest_prediction.json").write_text(json.dumps(payload), encoding="utf-8")
            pd.DataFrame(
                [
                    {"date": "2026-04-14", "signal": "no_entry"},
                    {"date": "2026-04-15", "signal": "bullish"},
                ]
            ).to_csv(cache_dir / "signal_rows.tsv", sep="\t", index=False)

            with mock.patch.object(ras.ac, "get_latest_prediction_path", return_value=cache_dir / "latest_prediction.json"):
                with mock.patch.object(ras.ac, "load_asset_config", return_value=slv_config):
                    with self.assertRaisesRegex(ValueError, "SLV preferred line .*cannot be validated"):
                        ras.build_slv(asset_dir)

    def test_build_slv_raises_when_latest_signal_row_drifts_from_live_payload(self) -> None:
        slv_config = {
            "live_operator_line_id": "custom_slv_live_line",
            "live_model_family": "custom_hard_gate_family",
            "live_label_mode": "future-return-top-bottom-9pct",
            "benchmark_symbol": "GDX",
        }
        with tempfile.TemporaryDirectory() as tmp:
            asset_dir = Path(tmp)
            cache_dir = asset_dir / ".cache"
            cache_dir.mkdir()

            payload = {
                "latest_raw_date": "2026-04-15",
                "latest_close": 30.55,
                "live_operator_line_id": "custom_slv_live_line",
                "signal_summary": {
                    "signal": "bullish",
                    "raw_model_signal": "bullish",
                    "predicted_probability": 0.9607,
                    "decision_threshold": 0.9399,
                    "confidence_gap": 0.0208,
                },
                "buy_point_summary": {
                    "buy_point_ok": True,
                    "buy_point_warnings": [],
                },
                "rule_summary": {
                    "selected": True,
                    "cutoff": 0.9501,
                    "rule_name": "top_15pct_reference",
                    "percentile_rank": 0.9912,
                },
                "rationale_summary": {
                    "model_reasons": ["fresh rationale"],
                    "rule_reason": "fresh rule rationale",
                },
                "latest_feature_snapshot": {
                    "ret_20": -0.0312,
                    "ret_60": 0.0543,
                    "drawdown_20": -0.0811,
                    "sma_gap_20": 0.0112,
                    "sma_gap_60": -0.0444,
                    "volume_vs_20": 1.1111,
                    "rsi_14": 49.11,
                },
                "model_summary": {
                    "model_family": "custom_hard_gate_family",
                    "label_mode": "future-return-top-bottom-9pct",
                    "reference_percentile_rule": "top_15pct",
                },
                "live_provenance": {
                    "benchmark_symbol": "GDX",
                    "outer_gate_feature": "price_ratio_benchmark_z_20",
                    "operator_line_id": "custom_slv_live_line",
                },
                "model_extra_features": ["price_ratio_benchmark_z_20"],
            }
            (cache_dir / "latest_prediction.json").write_text(json.dumps(payload), encoding="utf-8")
            pd.DataFrame(
                [
                    {"date": "2026-04-14", "signal": "no_entry", "probability": 0.1111, "close": 29.95},
                    {
                        "date": "2026-04-15",
                        "close": 30.55,
                        "signal": "bullish",
                        "raw_model_signal": "bullish",
                        "buy_point_ok": True,
                        "buy_point_warnings": "",
                        "probability": 0.9607,
                        "threshold": 0.9399,
                        "confidence_gap": 0.0101,
                        "rule_selected": True,
                        "rule_cutoff": 0.9111,
                        "rule_name": "top_15pct_reference",
                        "percentile_rank": 0.9555,
                        "model_rationale": "stale rationale",
                        "rule_rationale": "stale rule rationale",
                        "ret_20": -0.0111,
                        "ret_60": 0.0222,
                        "drawdown_20": -0.0444,
                        "sma_gap_20": 0.0999,
                        "sma_gap_60": -0.1111,
                        "volume_vs_20": 0.8888,
                        "rsi_14": 61.55,
                    },
                ]
            ).to_csv(cache_dir / "signal_rows.tsv", sep="\t", index=False)

            with mock.patch.object(ras.ac, "get_latest_prediction_path", return_value=cache_dir / "latest_prediction.json"):
                with mock.patch.object(ras.ac, "load_asset_config", return_value=slv_config):
                    with self.assertRaisesRegex(ValueError, "Latest signal cache drift detected for slv"):
                        ras.build_slv(asset_dir)

    def test_build_nvda_prefers_ret_60_sma_gap_60_atr_pct_20(self) -> None:
        pref = pd.DataFrame(
            [
                {"model_name": "binary_top12_5", "cutoff": 0.41},
                {"model_name": "ret_60_sma_gap_60_atr_pct_20", "cutoff": 0.45},
            ]
        )
        usage = pd.DataFrame(
            [
                {
                    "model_name": "binary_top12_5",
                    "recent_selected_count": 3,
                    "latest_date": "2026-04-15",
                    "latest_score": 0.44,
                    "latest_selected": False,
                    "cutoff": 0.41,
                    "last_selected_date": "2026-04-11",
                },
                {
                    "model_name": "ret_60_sma_gap_60_atr_pct_20",
                    "recent_selected_count": 4,
                    "latest_date": "2026-04-15",
                    "latest_score": 0.62,
                    "latest_selected": True,
                    "cutoff": 0.45,
                    "last_selected_date": "2026-04-15",
                },
            ]
        )

        with mock.patch.object(ras, "read_tsv", side_effect=[pref, usage]):
            with mock.patch.object(ras.ac, "get_latest_prediction_path", return_value=Path("unused") / ".cache" / "missing.json"):
                frame = ras.build_nvda(Path("unused"))

        preferred = frame.loc[frame["preferred"] == True].iloc[0]
        self.assertEqual(preferred["line_id"], "ret_60_sma_gap_60_atr_pct_20")
        self.assertEqual(preferred["role"], "primary")
        self.assertEqual(preferred["status"], "watchlist_ready")

    def test_build_nvda_refreshes_preferred_row_from_validated_live_cache_even_when_summary_has_it(self) -> None:
        pref = pd.DataFrame(
            [
                {"model_name": "binary_top12_5", "cutoff": 0.41},
                {"model_name": "ret_60_sma_gap_60_atr_pct_20", "cutoff": 0.45},
            ]
        )
        usage = pd.DataFrame(
            [
                {
                    "model_name": "binary_top12_5",
                    "recent_selected_count": 3,
                    "latest_date": "2026-04-15",
                    "latest_score": 0.44,
                    "latest_selected": False,
                    "cutoff": 0.41,
                    "last_selected_date": "2026-04-11",
                },
                {
                    "model_name": "ret_60_sma_gap_60_atr_pct_20",
                    "recent_selected_count": 99,
                    "latest_date": "2026-03-17",
                    "latest_score": 0.12,
                    "latest_selected": False,
                    "cutoff": 0.45,
                    "last_selected_date": "2026-03-17",
                },
            ]
        )
        signal_rows = pd.DataFrame(
            [
                {"date": "2026-04-13", "signal": "weak_bullish"},
                {"date": "2026-04-14", "signal": "no_entry"},
                {
                    "date": "2026-04-15",
                    "signal": "bullish",
                    "probability": 0.6502,
                    "threshold": 0.41,
                },
            ]
        )
        with tempfile.TemporaryDirectory() as tmp:
            asset_dir = Path(tmp)
            cache_dir = asset_dir / ".cache"
            cache_dir.mkdir()
            prediction_path = cache_dir / "latest_prediction.json"
            prediction_path.write_text(
                json.dumps(
                    {
                        "latest_raw_date": "2026-04-15",
                        "live_operator_line_id": "ret_60_sma_gap_60_atr_pct_20",
                        "signal_summary": {
                            "signal": "bullish",
                            "predicted_probability": 0.6502,
                            "decision_threshold": 0.41,
                        },
                        "model_extra_features": ["ret_60", "sma_gap_60", "atr_pct_20"],
                        "model_summary": {
                            "model_extra_features": ["ret_60", "sma_gap_60", "atr_pct_20"],
                        },
                    }
                ),
                encoding="utf-8",
            )

            with mock.patch.object(ras, "read_tsv", side_effect=[pref, usage]):
                with mock.patch.object(ras.ac, "get_latest_prediction_path", return_value=prediction_path):
                    with mock.patch.object(ras, "read_signal_rows_from_cache", return_value=signal_rows):
                        frame = ras.build_nvda(asset_dir)

        preferred = frame.loc[frame["preferred"] == True].iloc[0]
        self.assertEqual(preferred["latest_date"], "2026-04-15")
        self.assertEqual(preferred["latest_value"], 0.6502)
        self.assertTrue(bool(preferred["latest_selected"]))
        self.assertEqual(preferred["recent_selected_count"], 2)
        self.assertEqual(preferred["last_selected_date"], "2026-04-15")

    def test_build_nvda_synthesizes_preferred_live_row_when_cache_proves_operator(self) -> None:
        pref = pd.DataFrame(
            [
                {"model_name": "binary_top12_5", "cutoff": 0.41},
                {"model_name": "binary_top10", "cutoff": 0.43},
            ]
        )
        usage = pd.DataFrame(
            [
                {
                    "model_name": "binary_top12_5",
                    "recent_selected_count": 3,
                    "latest_date": "2026-04-15",
                    "latest_score": 0.44,
                    "latest_selected": False,
                    "cutoff": 0.41,
                    "last_selected_date": "2026-04-11",
                },
                {
                    "model_name": "binary_top10",
                    "recent_selected_count": 2,
                    "latest_date": "2026-04-15",
                    "latest_score": 0.42,
                    "latest_selected": False,
                    "cutoff": 0.43,
                    "last_selected_date": "2026-04-09",
                },
            ]
        )
        signal_rows = pd.DataFrame(
            [
                {"date": "2026-04-13", "signal": "weak_bullish"},
                {"date": "2026-04-14", "signal": "no_entry"},
                {
                    "date": "2026-04-15",
                    "signal": "no_entry",
                    "probability": 0.4502,
                    "threshold": 0.41,
                },
            ]
        )
        with tempfile.TemporaryDirectory() as tmp:
            asset_dir = Path(tmp)
            cache_dir = asset_dir / ".cache"
            cache_dir.mkdir()
            prediction_path = cache_dir / "latest_prediction.json"
            prediction_path.write_text(
                json.dumps(
                    {
                        "latest_raw_date": "2026-04-15",
                        "live_operator_line_id": "ret_60_sma_gap_60_atr_pct_20",
                        "signal_summary": {
                            "signal": "no_entry",
                            "predicted_probability": 0.4502,
                            "decision_threshold": 0.41,
                        },
                        "model_extra_features": ["ret_60", "sma_gap_60", "atr_pct_20"],
                        "model_summary": {
                            "model_extra_features": ["ret_60", "sma_gap_60", "atr_pct_20"],
                        },
                    }
                ),
                encoding="utf-8",
            )

            with mock.patch.object(ras, "read_tsv", side_effect=[pref, usage]):
                with mock.patch.object(ras.ac, "get_latest_prediction_path", return_value=prediction_path):
                    with mock.patch.object(ras, "read_signal_rows_from_cache", return_value=signal_rows):
                        frame = ras.build_nvda(asset_dir)

        preferred = frame.loc[frame["preferred"] == True].iloc[0]
        self.assertEqual(preferred["line_id"], "ret_60_sma_gap_60_atr_pct_20")
        self.assertEqual(preferred["role"], "primary")
        self.assertEqual(preferred["status"], "watchlist_ready")
        self.assertEqual(preferred["recent_selected_count"], 1)
        self.assertEqual(preferred["last_selected_date"], "2026-04-13")
        self.assertFalse(bool(preferred["latest_selected"]))

    def test_nvda_live_cache_rejects_mismatched_explicit_provenance_even_if_features_match(self) -> None:
        payload = {
            "live_operator_line_id": "binary_top12_5",
            "model_extra_features": ["ret_60", "sma_gap_60", "atr_pct_20"],
            "model_summary": {
                "model_extra_features": ["ret_60", "sma_gap_60", "atr_pct_20"],
            },
        }

        self.assertFalse(ras.nvda_live_cache_matches_preferred_line(payload, "ret_60_sma_gap_60_atr_pct_20"))

    def test_build_nvda_raises_when_summary_omits_preferred_and_cache_has_no_provenance(self) -> None:
        pref = pd.DataFrame(
            [
                {"model_name": "binary_top12_5", "cutoff": 0.41},
                {"model_name": "binary_top10", "cutoff": 0.43},
            ]
        )
        usage = pd.DataFrame(
            [
                {
                    "model_name": "binary_top12_5",
                    "recent_selected_count": 3,
                    "latest_date": "2026-04-15",
                    "latest_score": 0.44,
                    "latest_selected": False,
                    "cutoff": 0.41,
                    "last_selected_date": "2026-04-11",
                },
                {
                    "model_name": "binary_top10",
                    "recent_selected_count": 2,
                    "latest_date": "2026-04-15",
                    "latest_score": 0.42,
                    "latest_selected": False,
                    "cutoff": 0.43,
                    "last_selected_date": "2026-04-09",
                },
            ]
        )
        with tempfile.TemporaryDirectory() as tmp:
            asset_dir = Path(tmp)
            cache_dir = asset_dir / ".cache"
            cache_dir.mkdir()
            prediction_path = cache_dir / "latest_prediction.json"
            prediction_path.write_text(
                json.dumps(
                    {
                        "latest_raw_date": "2026-04-15",
                        "signal_summary": {
                            "signal": "no_entry",
                            "predicted_probability": 0.4502,
                            "decision_threshold": 0.41,
                        },
                        "model_extra_features": [],
                        "model_summary": {"model_extra_features": []},
                    }
                ),
                encoding="utf-8",
            )

            with mock.patch.object(ras, "read_tsv", side_effect=[pref, usage]):
                with mock.patch.object(ras.ac, "get_latest_prediction_path", return_value=prediction_path):
                    with self.assertRaisesRegex(ValueError, "NVDA preferred line .*cannot be validated"):
                        ras.build_nvda(asset_dir)


if __name__ == "__main__":
    unittest.main()
