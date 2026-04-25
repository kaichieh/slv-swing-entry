from __future__ import annotations

import json
import sys
import tempfile
import types
import unittest
from contextlib import ExitStack
from pathlib import Path
from typing import cast
from unittest import mock

import numpy as np
import pandas as pd

import predict_latest as pl
import train as tr


class PredictLatestLiveRuleTests(unittest.TestCase):
    def test_apply_buy_point_overlay_blocks_gld_under_term_panic(self) -> None:
        with mock.patch.object(
            pl.ac,
            "load_asset_config",
            return_value={
                "asset_key": "gld",
                "live_model_family": "hard_gate_two_expert_mixed",
                "live_operator_line_id": "gld_mixed_vix_vxv_term_panic_live",
                "live_term_panic_feature": "vix_vxv_ratio_pct_63_rolling_max_3",
                "live_term_panic_threshold": 0.9,
            },
        ):
            signal, details = pl.apply_buy_point_overlay(
                "bullish",
                {"vix_vxv_ratio_pct_63_rolling_max_3": 0.96},
                asset_key="gld",
            )

        details = cast(dict[str, object], details)
        self.assertEqual(signal, "no_entry")
        self.assertFalse(details["buy_point_ok"])
        warnings = cast(list[str], details["buy_point_warnings"])
        self.assertIn("term panic", warnings[0])

    def test_apply_buy_point_overlay_skips_gld_term_panic_for_baseline_line(self) -> None:
        with mock.patch.object(
            pl.ac,
            "load_asset_config",
            return_value={
                "asset_key": "gld",
                "live_operator_line_id": "gld_current_live_mixed_live",
                "live_term_panic_feature": "vix_vxv_ratio_pct_63_rolling_max_3",
                "live_term_panic_threshold": 0.9,
            },
        ):
            signal, details = pl.apply_buy_point_overlay(
                "bullish",
                {
                    "vix_vxv_ratio_pct_63_rolling_max_3": 0.96,
                    "rsi_14": 40.0,
                    "drawdown_20": -0.1,
                    "ret_20": 0.0,
                    "sma_gap_20": 0.0,
                },
                asset_key="gld",
            )

        details = cast(dict[str, object], details)
        self.assertEqual(signal, "bullish")
        self.assertTrue(details["buy_point_ok"])

    def test_apply_buy_point_overlay_promotes_clean_dip_to_early_entry(self) -> None:
        with mock.patch.object(
            pl.ac,
            "load_asset_config",
            return_value={
                "asset_key": "nvda",
                "live_dip_entry_overlay": {
                    "enabled": True,
                    "signal": "early_entry",
                    "max_rsi_14": 45.0,
                    "max_drawdown_20": -0.08,
                    "max_ret_20": 0.02,
                    "max_sma_gap_20": 0.01,
                    "max_close_location_20": 0.25,
                    "max_distance_from_60d_low": 0.08,
                },
            },
        ):
            signal, details = pl.apply_buy_point_overlay(
                "weak_bullish",
                {
                    "rsi_14": 28.0,
                    "drawdown_20": -0.12,
                    "ret_20": -0.08,
                    "sma_gap_20": -0.05,
                    "close_location_20": 0.04,
                    "distance_from_60d_low": 0.01,
                },
                asset_key="nvda",
                probability=0.49,
                model_threshold=0.48,
            )

        details = cast(dict[str, object], details)
        self.assertEqual(signal, "early_entry")
        self.assertTrue(details["buy_point_ok"])
        self.assertTrue(details["dip_entry_active"])

    def test_apply_buy_point_overlay_requires_model_threshold_for_dip_entry(self) -> None:
        with mock.patch.object(
            pl.ac,
            "load_asset_config",
            return_value={
                "asset_key": "mu",
                "live_dip_entry_overlay": {
                    "enabled": True,
                    "signal": "early_entry",
                    "max_rsi_14": 45.0,
                    "max_drawdown_20": -0.08,
                    "max_ret_20": 0.02,
                    "max_sma_gap_20": 0.01,
                    "max_close_location_20": 0.25,
                    "max_distance_from_60d_low": 0.12,
                },
            },
        ):
            signal, details = pl.apply_buy_point_overlay(
                "weak_bullish",
                {
                    "rsi_14": 32.0,
                    "drawdown_20": -0.22,
                    "ret_20": -0.18,
                    "sma_gap_20": -0.12,
                    "close_location_20": 0.03,
                    "distance_from_60d_low": 0.09,
                },
                asset_key="mu",
                probability=0.43,
                model_threshold=0.44,
            )

        details = cast(dict[str, object], details)
        self.assertEqual(signal, "weak_bullish")
        self.assertFalse(details["dip_entry_active"])

    def test_fit_hard_gate_two_expert_model_preserves_winner_features_without_selected_extras(self) -> None:
        frame = pd.DataFrame(
            {
                "date": [pd.Timestamp("2026-03-01"), pd.Timestamp("2026-03-02")],
                tr.TARGET_COLUMN: [1.0, 0.0],
                "price_ratio_benchmark_z_20": [0.4, -0.2],
                "ret_60": [0.1, 0.2],
                "sma_gap_60": [0.05, -0.03],
                "distance_to_252_high": [-0.1, -0.2],
                "rs_vs_benchmark_60": [0.2, 0.1],
                "atr_pct_20_percentile": [0.8, 0.6],
                "vix_close_lag1": [22.0, 24.0],
            }
        )
        fake_rb = types.SimpleNamespace()
        fake_rb.build_labeled_frame = mock.Mock(return_value=frame)
        fake_rb.select_threshold_with_steps = mock.Mock(return_value=0.55)
        fake_rb.split_frame = mock.Mock(
            return_value={
                "train": frame.iloc[[0]].reset_index(drop=True),
                "validation": frame.iloc[[0]].reset_index(drop=True),
                "test": frame.iloc[[1]].reset_index(drop=True),
            }
        )

        def train_model_side_effect(_frame, _expert, **kwargs):
            extra_features = list(kwargs["extra_features"])
            return None, {
                "feature_names": extra_features,
                "validation_probabilities": np.array([0.7], dtype=np.float32),
                "test_probabilities": np.array([0.6], dtype=np.float32),
            }

        fake_rb.train_model = mock.Mock(side_effect=train_model_side_effect)
        fake_winner = types.SimpleNamespace(
            LEFT_EXPERT="gdx_relative_dual",
            RIGHT_EXPERT="gdx_context",
            OUTER_GATE_FEATURE="price_ratio_benchmark_z_20",
            OUTER_GATE_THRESHOLD=0.141332,
        )

        with mock.patch.dict(sys.modules, {"research_batch": fake_rb, "research_slv_topbottom15_gdx_hard_gate_two_expert": fake_winner}):
            with mock.patch.dict("os.environ", {}, clear=False):
                artifacts = pl.fit_hard_gate_two_expert_model(raw_prices=mock.sentinel.raw_prices)

        left_call = fake_rb.train_model.call_args_list[0]
        right_call = fake_rb.train_model.call_args_list[1]
        self.assertEqual(
            left_call.kwargs["extra_features"],
            (
                "ret_60",
                "sma_gap_60",
                "distance_to_252_high",
                "rs_vs_benchmark_60",
                "price_ratio_benchmark_z_20",
            ),
        )
        self.assertEqual(
            right_call.kwargs["extra_features"],
            (
                "ret_60",
                "sma_gap_60",
                "distance_to_252_high",
                "rs_vs_benchmark_60",
                "price_ratio_benchmark_z_20",
                "atr_pct_20_percentile",
            ),
        )
        self.assertEqual(artifacts["feature_names"][-1], "atr_pct_20_percentile")

    def test_fit_hard_gate_two_expert_mixed_model_appends_selected_experimental_features_when_available(self) -> None:
        frame = pd.DataFrame(
            {
                "date": [pd.Timestamp("2026-03-01"), pd.Timestamp("2026-03-02")],
                tr.TARGET_COLUMN: [1.0, 0.0],
                "above_200dma_flag": [1.0, 0.0],
                "ret_60": [0.1, 0.2],
                "distance_to_252_high": [-0.1, -0.2],
                "vix_close_lag1": [22.0, 24.0],
            }
        )
        fake_rb = types.SimpleNamespace()
        fake_rb.build_labeled_frame = mock.Mock(return_value=frame)
        fake_rb.select_threshold_with_steps = mock.Mock(return_value=0.55)
        fake_rb.split_frame = mock.Mock(
            return_value={
                "train": frame.iloc[[0]].reset_index(drop=True),
                "validation": frame.iloc[[0]].reset_index(drop=True),
                "test": frame.iloc[[1]].reset_index(drop=True),
            }
        )

        def train_model_side_effect(_frame, _expert, **kwargs):
            extra_features = list(kwargs["extra_features"])
            return None, {
                "feature_names": extra_features,
                "validation_probabilities": np.array([0.7], dtype=np.float32),
                "test_probabilities": np.array([0.6], dtype=np.float32),
            }

        fake_rb.train_model = mock.Mock(side_effect=train_model_side_effect)
        fake_winner = types.SimpleNamespace(
            LEFT_EXPERT="gld_left",
            RIGHT_EXPERT="gld_right",
            LEFT_EXTRA_FEATURES=("ret_60",),
            RIGHT_EXTRA_FEATURES=("distance_to_252_high", "ret_60"),
            OUTER_GATE_FEATURE="above_200dma_flag",
            OUTER_GATE_THRESHOLD=0.5,
        )

        with mock.patch.dict(
            sys.modules,
            {"research_batch": fake_rb, "research_gld_topbottom10_hard_gate_two_expert_mixed": fake_winner},
        ):
            with mock.patch.dict(
                "os.environ",
                {"AR_EXTRA_BASE_FEATURES": "vix_close_lag1,ret_60,missing_extra"},
                clear=False,
            ):
                with mock.patch.object(pl, "download_vix_prices", return_value="vix_prices", create=True):
                    with mock.patch.object(pl, "add_vix_features", return_value=frame, create=True):
                        pl.fit_hard_gate_two_expert_mixed_model(raw_prices=mock.sentinel.raw_prices)

        left_call = fake_rb.train_model.call_args_list[0]
        right_call = fake_rb.train_model.call_args_list[1]
        self.assertEqual(left_call.kwargs["extra_features"], ("ret_60", "vix_close_lag1"))
        self.assertEqual(right_call.kwargs["extra_features"], ("distance_to_252_high", "ret_60", "vix_close_lag1"))

    def test_fit_hard_gate_two_expert_mixed_model_merges_vix_frame_when_selected(self) -> None:
        frame = pd.DataFrame(
            {
                "date": [pd.Timestamp("2026-03-01"), pd.Timestamp("2026-03-02")],
                tr.TARGET_COLUMN: [1.0, 0.0],
                "above_200dma_flag": [1.0, 0.0],
                "ret_60": [0.1, 0.2],
                "distance_to_252_high": [-0.1, -0.2],
            }
        )
        enriched = frame.assign(vix_close_lag1=[22.0, 24.0])
        fake_rb = types.SimpleNamespace()
        fake_rb.build_labeled_frame = mock.Mock(return_value=frame)
        fake_rb.select_threshold_with_steps = mock.Mock(return_value=0.55)
        fake_rb.split_frame = mock.Mock(
            return_value={
                "train": enriched.iloc[[0]].reset_index(drop=True),
                "validation": enriched.iloc[[0]].reset_index(drop=True),
                "test": enriched.iloc[[1]].reset_index(drop=True),
            }
        )
        fake_rb.train_model = mock.Mock(
            side_effect=[
                (None, {"feature_names": ["ret_60", "vix_close_lag1"], "validation_probabilities": np.array([0.7], dtype=np.float32), "test_probabilities": np.array([0.6], dtype=np.float32)}),
                (None, {"feature_names": ["distance_to_252_high", "ret_60", "vix_close_lag1"], "validation_probabilities": np.array([0.7], dtype=np.float32), "test_probabilities": np.array([0.6], dtype=np.float32)}),
            ]
        )
        fake_winner = types.SimpleNamespace(
            LEFT_EXPERT="gld_left",
            RIGHT_EXPERT="gld_right",
            LEFT_EXTRA_FEATURES=("ret_60",),
            RIGHT_EXTRA_FEATURES=("distance_to_252_high", "ret_60"),
            OUTER_GATE_FEATURE="above_200dma_flag",
            OUTER_GATE_THRESHOLD=0.5,
        )

        with mock.patch.dict(sys.modules, {"research_batch": fake_rb, "research_gld_topbottom10_hard_gate_two_expert_mixed": fake_winner}):
            with mock.patch.dict("os.environ", {"AR_EXTRA_BASE_FEATURES": "vix_close_lag1"}, clear=False):
                with mock.patch.object(pl, "download_vix_prices", return_value="vix_prices", create=True) as download_vix_prices:
                    with mock.patch.object(pl, "add_vix_features", return_value=enriched, create=True) as add_vix_features:
                        pl.fit_hard_gate_two_expert_mixed_model(raw_prices=mock.sentinel.raw_prices)

        download_vix_prices.assert_called_once_with()
        add_vix_features.assert_called_once_with(frame, "vix_prices")

    def test_fit_hard_gate_two_expert_mixed_model_skips_vix_merge_when_unselected(self) -> None:
        frame = pd.DataFrame(
            {
                "date": [pd.Timestamp("2026-03-01"), pd.Timestamp("2026-03-02")],
                tr.TARGET_COLUMN: [1.0, 0.0],
                "above_200dma_flag": [1.0, 0.0],
                "ret_60": [0.1, 0.2],
                "distance_to_252_high": [-0.1, -0.2],
            }
        )
        fake_rb = types.SimpleNamespace()
        fake_rb.build_labeled_frame = mock.Mock(return_value=frame)
        fake_rb.select_threshold_with_steps = mock.Mock(return_value=0.55)
        fake_rb.split_frame = mock.Mock(
            return_value={
                "train": frame.iloc[[0]].reset_index(drop=True),
                "validation": frame.iloc[[0]].reset_index(drop=True),
                "test": frame.iloc[[1]].reset_index(drop=True),
            }
        )
        fake_rb.train_model = mock.Mock(
            side_effect=[
                (None, {"feature_names": ["ret_60"], "validation_probabilities": np.array([0.7], dtype=np.float32), "test_probabilities": np.array([0.6], dtype=np.float32)}),
                (None, {"feature_names": ["distance_to_252_high", "ret_60"], "validation_probabilities": np.array([0.7], dtype=np.float32), "test_probabilities": np.array([0.6], dtype=np.float32)}),
            ]
        )
        fake_winner = types.SimpleNamespace(
            LEFT_EXPERT="gld_left",
            RIGHT_EXPERT="gld_right",
            LEFT_EXTRA_FEATURES=("ret_60",),
            RIGHT_EXTRA_FEATURES=("distance_to_252_high", "ret_60"),
            OUTER_GATE_FEATURE="above_200dma_flag",
            OUTER_GATE_THRESHOLD=0.5,
        )

        with mock.patch.dict(sys.modules, {"research_batch": fake_rb, "research_gld_topbottom10_hard_gate_two_expert_mixed": fake_winner}):
            with mock.patch.dict("os.environ", {"AR_EXTRA_BASE_FEATURES": "ret_60"}, clear=False):
                with mock.patch.object(pl, "download_vix_prices", create=True) as download_vix_prices:
                    with mock.patch.object(pl, "add_vix_features", create=True) as add_vix_features:
                        pl.fit_hard_gate_two_expert_mixed_model(raw_prices=mock.sentinel.raw_prices)

        download_vix_prices.assert_not_called()
        add_vix_features.assert_not_called()

    def test_fit_hard_gate_two_expert_model_appends_selected_experimental_features_when_available(self) -> None:
        frame = pd.DataFrame(
            {
                "date": [pd.Timestamp("2026-03-01"), pd.Timestamp("2026-03-02")],
                tr.TARGET_COLUMN: [1.0, 0.0],
                "price_ratio_benchmark_z_20": [0.4, -0.2],
                "ret_60": [0.1, 0.2],
                "sma_gap_60": [0.05, -0.03],
                "distance_to_252_high": [-0.1, -0.2],
                "rs_vs_benchmark_60": [0.2, 0.1],
                "atr_pct_20_percentile": [0.8, 0.6],
                "vix_close_lag1": [22.0, 24.0],
            }
        )
        fake_rb = types.SimpleNamespace()
        fake_rb.build_labeled_frame = mock.Mock(return_value=frame)
        fake_rb.select_threshold_with_steps = mock.Mock(return_value=0.55)
        fake_rb.split_frame = mock.Mock(
            return_value={
                "train": frame.iloc[[0]].reset_index(drop=True),
                "validation": frame.iloc[[0]].reset_index(drop=True),
                "test": frame.iloc[[1]].reset_index(drop=True),
            }
        )

        def train_model_side_effect(_frame, _expert, **kwargs):
            extra_features = list(kwargs["extra_features"])
            return None, {
                "feature_names": extra_features,
                "validation_probabilities": np.array([0.7], dtype=np.float32),
                "test_probabilities": np.array([0.6], dtype=np.float32),
            }

        fake_rb.train_model = mock.Mock(side_effect=train_model_side_effect)
        fake_winner = types.SimpleNamespace(
            LEFT_EXPERT="gdx_relative_dual",
            RIGHT_EXPERT="gdx_context",
            OUTER_GATE_FEATURE="price_ratio_benchmark_z_20",
            OUTER_GATE_THRESHOLD=0.141332,
        )

        with mock.patch.dict(sys.modules, {"research_batch": fake_rb, "research_slv_topbottom15_gdx_hard_gate_two_expert": fake_winner}):
            with mock.patch.dict(
                "os.environ",
                {"AR_EXTRA_BASE_FEATURES": "vix_close_lag1,ret_60,missing_extra"},
                clear=False,
            ):
                pl.fit_hard_gate_two_expert_model(raw_prices=mock.sentinel.raw_prices)

        left_call = fake_rb.train_model.call_args_list[0]
        right_call = fake_rb.train_model.call_args_list[1]
        self.assertEqual(
            left_call.kwargs["extra_features"],
            (
                "ret_60",
                "sma_gap_60",
                "distance_to_252_high",
                "rs_vs_benchmark_60",
                "price_ratio_benchmark_z_20",
                "vix_close_lag1",
            ),
        )
        self.assertEqual(
            right_call.kwargs["extra_features"],
            (
                "ret_60",
                "sma_gap_60",
                "distance_to_252_high",
                "rs_vs_benchmark_60",
                "price_ratio_benchmark_z_20",
                "atr_pct_20_percentile",
                "vix_close_lag1",
            ),
        )

    def test_main_builds_live_features_with_vix_pipeline_before_scoring(self) -> None:
        latest_live = pd.DataFrame(
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
            "live_label_mode": "drop-neutral",
        }

        with tempfile.TemporaryDirectory() as tmp:
            prediction_path = Path(tmp) / "latest_prediction.json"
            with ExitStack() as stack:
                stack.enter_context(mock.patch.object(pl.tr, "set_seed"))
                stack.enter_context(mock.patch.object(pl.tr, "get_env_int", return_value=pl.tr.SEED))
                stack.enter_context(mock.patch.object(pl.tr, "FEATURE_COLUMNS", ["baseline_feature"]))
                stack.enter_context(mock.patch.object(pl, "download_asset_prices", return_value="raw_prices"))
                stack.enter_context(mock.patch.object(pl, "add_price_features", return_value="price_features"))
                stack.enter_context(mock.patch.object(pl, "add_relative_strength_features", return_value="relative_features"))
                stack.enter_context(mock.patch.object(pl, "add_context_features", return_value="context_features"))
                download_vix_prices = stack.enter_context(
                    mock.patch.object(pl, "download_vix_prices", return_value="vix_prices", create=True)
                )
                add_vix_features = stack.enter_context(
                    mock.patch.object(pl, "add_vix_features", return_value=latest_live, create=True)
                )
                stack.enter_context(mock.patch.object(pl.tr, "load_splits", return_value=splits))
                stack.enter_context(
                    mock.patch.object(pl, "build_feature_names", return_value=["baseline_feature", "vix_close_lag1"])
                )
                stack.enter_context(mock.patch.object(pl, "fit_model", return_value=model_artifacts))
                score_latest_row = stack.enter_context(
                    mock.patch.object(
                        pl,
                        "score_latest_row",
                        return_value=(
                            np.array([[1.0]], dtype=np.float32),
                            {"baseline_feature": 1.0, "vix_close_lag1": 22.0},
                        ),
                    )
                )
                stack.enter_context(mock.patch.object(pl, "predict_probabilities", return_value=np.array([0.7], dtype=np.float32)))
                stack.enter_context(
                    mock.patch.object(pl, "build_history_probabilities", return_value=np.array([0.2, 0.4, 0.6], dtype=np.float32))
                )
                stack.enter_context(mock.patch.object(pl, "classify_signal", return_value=("bullish", {"confidence_gap": 0.2})))
                stack.enter_context(mock.patch.object(pl, "apply_buy_point_overlay", return_value=("bullish", {"buy_point_ok": True})))
                stack.enter_context(mock.patch.object(pl, "get_rule_top_pct", return_value=20.0))
                stack.enter_context(mock.patch.object(pl, "summarize_rule", return_value={"rule_name": "top_20pct_reference", "selected": True}))
                stack.enter_context(mock.patch.object(pl, "build_model_rationale", return_value=["reason"]))
                stack.enter_context(mock.patch.object(pl, "build_rule_rationale", return_value="rule rationale"))
                stack.enter_context(mock.patch.object(pl.ac, "load_asset_config", return_value={"asset_key": "nvda"}))
                stack.enter_context(mock.patch.object(pl.ac, "get_asset_symbol", return_value="NVDA"))
                stack.enter_context(mock.patch.object(pl.ac, "get_latest_prediction_path", return_value=prediction_path))

                pl.main()

        download_vix_prices.assert_called_once_with()
        self.assertEqual(add_vix_features.call_count, 1)
        self.assertEqual(add_vix_features.call_args.args, ("context_features", "vix_prices"))
        pd.testing.assert_frame_equal(score_latest_row.call_args.args[3], latest_live)

    def test_main_skips_vix_pipeline_when_selected_features_do_not_need_it(self) -> None:
        latest_live = pd.DataFrame([
            {"date": pd.Timestamp("2026-04-15"), "open": 100.0, "high": 102.0, "low": 99.0, "close": 101.0, "baseline_feature": 1.0}
        ])
        splits = {"test": mock.Mock(frame=pd.DataFrame({"date": [pd.Timestamp("2026-03-31")]}))}
        model_artifacts = {
            "model_family": "logistic",
            "threshold": 0.5,
            "train_frame": pd.DataFrame({"baseline_feature": [1.0]}),
            "feature_names": ["baseline_feature"],
            "default_interactions": [],
            "live_label_mode": "drop-neutral",
        }

        with tempfile.TemporaryDirectory() as tmp:
            prediction_path = Path(tmp) / "latest_prediction.json"
            with ExitStack() as stack:
                stack.enter_context(mock.patch.object(pl.tr, "set_seed"))
                stack.enter_context(mock.patch.object(pl.tr, "get_env_int", return_value=pl.tr.SEED))
                stack.enter_context(mock.patch.object(pl.tr, "FEATURE_COLUMNS", ["baseline_feature"]))
                stack.enter_context(mock.patch.object(pl, "download_asset_prices", return_value="raw_prices"))
                stack.enter_context(mock.patch.object(pl, "add_price_features", return_value="price_features"))
                stack.enter_context(mock.patch.object(pl, "add_relative_strength_features", return_value="relative_features"))
                stack.enter_context(mock.patch.object(pl, "add_context_features", return_value=latest_live))
                download_vix_prices = stack.enter_context(mock.patch.object(pl, "download_vix_prices", create=True))
                add_vix_features = stack.enter_context(mock.patch.object(pl, "add_vix_features", create=True))
                stack.enter_context(mock.patch.object(pl.tr, "load_splits", return_value=splits))
                stack.enter_context(mock.patch.object(pl, "build_feature_names", return_value=["baseline_feature"]))
                stack.enter_context(mock.patch.object(pl, "fit_model", return_value=model_artifacts))
                score_latest_row = stack.enter_context(mock.patch.object(pl, "score_latest_row", return_value=(np.array([[1.0]], dtype=np.float32), {"baseline_feature": 1.0})))
                stack.enter_context(mock.patch.object(pl, "predict_probabilities", return_value=np.array([0.7], dtype=np.float32)))
                stack.enter_context(mock.patch.object(pl, "build_history_probabilities", return_value=np.array([0.2, 0.4, 0.6], dtype=np.float32)))
                stack.enter_context(mock.patch.object(pl, "classify_signal", return_value=("bullish", {"confidence_gap": 0.2})))
                stack.enter_context(mock.patch.object(pl, "apply_buy_point_overlay", return_value=("bullish", {"buy_point_ok": True})))
                stack.enter_context(mock.patch.object(pl, "get_rule_top_pct", return_value=20.0))
                stack.enter_context(mock.patch.object(pl, "summarize_rule", return_value={"rule_name": "top_20pct_reference", "selected": True}))
                stack.enter_context(mock.patch.object(pl, "build_model_rationale", return_value=["reason"]))
                stack.enter_context(mock.patch.object(pl, "build_rule_rationale", return_value="rule rationale"))
                stack.enter_context(mock.patch.object(pl.ac, "load_asset_config", return_value={"asset_key": "nvda"}))
                stack.enter_context(mock.patch.object(pl.ac, "get_asset_symbol", return_value="NVDA"))
                stack.enter_context(mock.patch.object(pl.ac, "get_latest_prediction_path", return_value=prediction_path))
                pl.main()

        download_vix_prices.assert_not_called()
        add_vix_features.assert_not_called()
        pd.testing.assert_frame_equal(score_latest_row.call_args.args[3], latest_live)

    def test_main_builds_term_structure_features_for_gld_mixed_live_path(self) -> None:
        latest_live = pd.DataFrame([
            {"date": pd.Timestamp("2026-04-15"), "open": 100.0, "high": 102.0, "low": 99.0, "close": 101.0, "baseline_feature": 1.0}
        ])
        live_with_vix = latest_live.assign(vix_close_lag1=20.0)
        live_with_term = live_with_vix.assign(vix_vxv_ratio_pct_63_rolling_max_3=0.96)
        splits = {"test": mock.Mock(frame=pd.DataFrame({"date": [pd.Timestamp("2026-03-31")]}))}
        model_artifacts = {
            "model_family": pl.HARD_GATE_TWO_EXPERT_MIXED,
            "threshold": 0.5,
            "train_frame": pd.DataFrame({"baseline_feature": [1.0]}),
            "feature_names": ["baseline_feature"],
            "default_interactions": [],
            "live_label_mode": "future-return-top-bottom-10pct",
        }

        with tempfile.TemporaryDirectory() as tmp:
            prediction_path = Path(tmp) / "latest_prediction.json"
            with ExitStack() as stack:
                stack.enter_context(mock.patch.object(pl.tr, "set_seed"))
                stack.enter_context(mock.patch.object(pl.tr, "get_env_int", return_value=pl.tr.SEED))
                stack.enter_context(mock.patch.object(pl.tr, "FEATURE_COLUMNS", ["baseline_feature"]))
                stack.enter_context(mock.patch.object(pl, "download_asset_prices", return_value="raw_prices"))
                stack.enter_context(mock.patch.object(pl, "add_price_features", return_value="price_features"))
                stack.enter_context(mock.patch.object(pl, "add_relative_strength_features", return_value="relative_features"))
                stack.enter_context(mock.patch.object(pl, "add_context_features", return_value=latest_live))
                download_vix_prices = stack.enter_context(mock.patch.object(pl, "download_vix_prices", return_value="vix_prices", create=True))
                add_vix_features = stack.enter_context(mock.patch.object(pl, "add_vix_features", return_value=live_with_vix, create=True))
                download_vix3m_prices = stack.enter_context(mock.patch.object(pl, "download_vix3m_prices", return_value="vix3m_prices", create=True))
                add_vix_term_structure_features = stack.enter_context(mock.patch.object(pl, "add_vix_term_structure_features", return_value=live_with_term, create=True))
                stack.enter_context(mock.patch.object(pl.tr, "load_splits", return_value=splits))
                stack.enter_context(mock.patch.object(pl, "build_feature_names", return_value=["baseline_feature"]))
                stack.enter_context(mock.patch.object(pl, "fit_model", return_value=model_artifacts))
                score_latest_row = stack.enter_context(mock.patch.object(pl, "score_latest_row", return_value=(np.array([[1.0]], dtype=np.float32), {"baseline_feature": 1.0, "vix_vxv_ratio_pct_63_rolling_max_3": 0.96})))
                stack.enter_context(mock.patch.object(pl, "predict_probabilities", return_value=np.array([0.7], dtype=np.float32)))
                stack.enter_context(mock.patch.object(pl, "build_history_probabilities", return_value=np.array([0.2, 0.4, 0.6], dtype=np.float32)))
                stack.enter_context(mock.patch.object(pl, "classify_signal", return_value=("bullish", {"confidence_gap": 0.2})))
                stack.enter_context(mock.patch.object(pl, "get_rule_top_pct", return_value=20.0))
                stack.enter_context(mock.patch.object(pl, "summarize_rule", return_value={"rule_name": "top_20pct_reference", "selected": True}))
                stack.enter_context(mock.patch.object(pl, "build_model_rationale", return_value=["reason"]))
                stack.enter_context(mock.patch.object(pl, "build_rule_rationale", return_value="rule rationale"))
                stack.enter_context(
                    mock.patch.object(
                        pl.ac,
                        "load_asset_config",
                        return_value={
                            "asset_key": "gld",
                            "live_model_family": pl.HARD_GATE_TWO_EXPERT_MIXED,
                            "live_operator_line_id": "gld_mixed_vix_vxv_term_panic_live",
                            "live_term_panic_feature": "vix_vxv_ratio_pct_63_rolling_max_3",
                            "live_term_panic_threshold": 0.9,
                        },
                    )
                )
                stack.enter_context(mock.patch.object(pl.ac, "get_asset_symbol", return_value="GLD"))
                stack.enter_context(mock.patch.object(pl.ac, "get_latest_prediction_path", return_value=prediction_path))
                pl.main()

        self.assertGreaterEqual(download_vix_prices.call_count, 1)
        add_vix_features.assert_called_with(latest_live, "vix_prices")
        download_vix3m_prices.assert_called_once_with()
        add_vix_term_structure_features.assert_called_once_with(live_with_vix, "vix3m_prices")
        pd.testing.assert_frame_equal(score_latest_row.call_args.args[3], live_with_term)

    def test_main_skips_term_structure_features_for_gld_baseline_live_line(self) -> None:
        latest_live = pd.DataFrame([
            {"date": pd.Timestamp("2026-04-15"), "open": 100.0, "high": 102.0, "low": 99.0, "close": 101.0, "baseline_feature": 1.0}
        ])
        splits = {"test": mock.Mock(frame=pd.DataFrame({"date": [pd.Timestamp("2026-03-31")]}))}
        model_artifacts = {
            "model_family": pl.HARD_GATE_TWO_EXPERT_MIXED,
            "threshold": 0.5,
            "train_frame": pd.DataFrame({"baseline_feature": [1.0]}),
            "feature_names": ["baseline_feature"],
            "default_interactions": [],
            "live_label_mode": "future-return-top-bottom-10pct",
        }

        with tempfile.TemporaryDirectory() as tmp:
            prediction_path = Path(tmp) / "latest_prediction.json"
            with ExitStack() as stack:
                stack.enter_context(mock.patch.object(pl.tr, "set_seed"))
                stack.enter_context(mock.patch.object(pl.tr, "get_env_int", return_value=pl.tr.SEED))
                stack.enter_context(mock.patch.object(pl.tr, "FEATURE_COLUMNS", ["baseline_feature"]))
                stack.enter_context(mock.patch.object(pl, "download_asset_prices", return_value="raw_prices"))
                stack.enter_context(mock.patch.object(pl, "add_price_features", return_value="price_features"))
                stack.enter_context(mock.patch.object(pl, "add_relative_strength_features", return_value="relative_features"))
                stack.enter_context(mock.patch.object(pl, "add_context_features", return_value=latest_live))
                download_vix_prices = stack.enter_context(mock.patch.object(pl, "download_vix_prices", return_value="vix_prices", create=True))
                add_vix_features = stack.enter_context(mock.patch.object(pl, "add_vix_features", return_value=latest_live, create=True))
                download_vix3m_prices = stack.enter_context(mock.patch.object(pl, "download_vix3m_prices", return_value="vix3m_prices", create=True))
                add_vix_term_structure_features = stack.enter_context(mock.patch.object(pl, "add_vix_term_structure_features", return_value=latest_live, create=True))
                stack.enter_context(mock.patch.object(pl.tr, "load_splits", return_value=splits))
                stack.enter_context(mock.patch.object(pl, "build_feature_names", return_value=["baseline_feature"]))
                stack.enter_context(mock.patch.object(pl, "fit_model", return_value=model_artifacts))
                score_latest_row = stack.enter_context(mock.patch.object(pl, "score_latest_row", return_value=(np.array([[1.0]], dtype=np.float32), {"baseline_feature": 1.0})))
                stack.enter_context(mock.patch.object(pl, "predict_probabilities", return_value=np.array([0.7], dtype=np.float32)))
                stack.enter_context(mock.patch.object(pl, "build_history_probabilities", return_value=np.array([0.2, 0.4, 0.6], dtype=np.float32)))
                stack.enter_context(mock.patch.object(pl, "classify_signal", return_value=("bullish", {"confidence_gap": 0.2})))
                stack.enter_context(mock.patch.object(pl, "apply_buy_point_overlay", return_value=("bullish", {"buy_point_ok": True})))
                stack.enter_context(mock.patch.object(pl, "get_rule_top_pct", return_value=20.0))
                stack.enter_context(mock.patch.object(pl, "summarize_rule", return_value={"rule_name": "top_20pct_reference", "selected": True}))
                stack.enter_context(mock.patch.object(pl, "build_model_rationale", return_value=["reason"]))
                stack.enter_context(mock.patch.object(pl, "build_rule_rationale", return_value="rule rationale"))
                stack.enter_context(mock.patch.object(pl.ac, "load_asset_config", return_value={"asset_key": "gld", "live_model_family": pl.HARD_GATE_TWO_EXPERT_MIXED, "live_operator_line_id": "gld_current_live_mixed_live"}))
                stack.enter_context(mock.patch.object(pl.ac, "get_asset_symbol", return_value="GLD"))
                stack.enter_context(mock.patch.object(pl.ac, "get_latest_prediction_path", return_value=prediction_path))
                pl.main()

        download_vix_prices.assert_not_called()
        add_vix_features.assert_not_called()
        download_vix3m_prices.assert_not_called()
        add_vix_term_structure_features.assert_not_called()
        pd.testing.assert_frame_equal(score_latest_row.call_args.args[3], latest_live)

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

    def test_get_live_model_family_accepts_hard_gate_two_expert(self) -> None:
        with mock.patch.object(pl.ac, "get_live_model_family", return_value="hard_gate_two_expert"):
            self.assertEqual(pl.get_live_model_family(), "hard_gate_two_expert")

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

    def test_fit_model_uses_hard_gate_two_expert_path_when_configured(self) -> None:
        fake_splits = {"train": mock.Mock(), "validation": mock.Mock(), "test": mock.Mock()}
        fake_prices = mock.Mock()
        expected = {"model_family": "hard_gate_two_expert", "threshold": 0.63}
        with mock.patch.object(pl, "get_live_model_family", return_value="hard_gate_two_expert"):
            with mock.patch.object(pl, "fit_hard_gate_two_expert_model", return_value=expected) as fit_hard_gate:
                result = pl.fit_model(fake_splits, ["distance_to_252_high"], raw_prices=fake_prices)

        self.assertIs(result, expected)
        fit_hard_gate.assert_called_once_with(fake_prices)

    def test_predict_probabilities_uses_xgboost_classifier_predict_proba(self) -> None:
        model = mock.Mock()
        model.predict_proba.return_value = np.array([[0.4, 0.6], [0.3, 0.7]], dtype=np.float32)
        artifacts = {"model_family": "xgboost", "model": model}

        with mock.patch.object(pl, "require_xgboost", return_value=mock.Mock(DMatrix=None)):
            probabilities = pl.predict_probabilities(artifacts, np.ones((2, 1), dtype=np.float32))

        np.testing.assert_allclose(probabilities, np.array([0.6, 0.7], dtype=np.float32))

    def test_main_writes_configured_live_operator_line_id_when_actual_live_path_matches(self) -> None:
        latest_live = pd.DataFrame(
            [
                {
                    "date": pd.Timestamp("2026-04-15"),
                    "open": 100.0,
                    "high": 102.0,
                    "low": 99.0,
                    "close": 101.0,
                }
            ]
        )
        splits = {
            "test": mock.Mock(frame=pd.DataFrame({"date": [pd.Timestamp("2026-03-31")]})),
        }
        model_artifacts = {
            "model_family": "logistic",
            "threshold": 0.5,
            "train_frame": pd.DataFrame({"baseline_feature": [1.0]}),
            "feature_names": ["baseline_feature", "ret_60", "sma_gap_60", "atr_pct_20"],
            "default_interactions": [],
            "live_label_mode": "drop-neutral",
        }
        with tempfile.TemporaryDirectory() as tmp:
            prediction_path = Path(tmp) / "latest_prediction.json"
            with ExitStack() as stack:
                stack.enter_context(mock.patch.object(pl.tr, "set_seed"))
                stack.enter_context(mock.patch.object(pl.tr, "get_env_int", return_value=pl.tr.SEED))
                stack.enter_context(mock.patch.object(pl.tr, "FEATURE_COLUMNS", ["baseline_feature"]))
                stack.enter_context(mock.patch.object(pl, "download_asset_prices", return_value="raw_prices"))
                stack.enter_context(mock.patch.object(pl, "add_price_features", return_value="price_features"))
                stack.enter_context(mock.patch.object(pl, "add_relative_strength_features", return_value="relative_features"))
                stack.enter_context(mock.patch.object(pl, "add_context_features", return_value=latest_live))
                stack.enter_context(mock.patch.object(pl, "download_vix_prices", return_value="vix_prices", create=True))
                stack.enter_context(mock.patch.object(pl, "add_vix_features", return_value=latest_live, create=True))
                stack.enter_context(mock.patch.object(pl.tr, "load_splits", return_value=splits))
                stack.enter_context(
                    mock.patch.object(
                        pl,
                        "build_feature_names",
                        return_value=["baseline_feature", "ret_60", "sma_gap_60", "atr_pct_20"],
                    )
                )
                stack.enter_context(mock.patch.object(pl, "fit_model", return_value=model_artifacts))
                stack.enter_context(
                    mock.patch.object(
                        pl,
                        "score_latest_row",
                        return_value=(
                            np.array([[1.0]], dtype=np.float32),
                            {"ret_60": 0.1, "sma_gap_60": -0.05, "atr_pct_20": 0.02},
                        ),
                    )
                )
                stack.enter_context(mock.patch.object(pl, "predict_probabilities", return_value=np.array([0.7], dtype=np.float32)))
                stack.enter_context(
                    mock.patch.object(pl, "build_history_probabilities", return_value=np.array([0.2, 0.4, 0.6], dtype=np.float32))
                )
                stack.enter_context(mock.patch.object(pl, "classify_signal", return_value=("bullish", {"confidence_gap": 0.2})))
                stack.enter_context(mock.patch.object(pl, "apply_buy_point_overlay", return_value=("bullish", {"buy_point_ok": True})))
                stack.enter_context(mock.patch.object(pl, "get_rule_top_pct", return_value=20.0))
                stack.enter_context(mock.patch.object(pl, "summarize_rule", return_value={"rule_name": "top_20pct_reference", "selected": True}))
                stack.enter_context(mock.patch.object(pl, "build_model_rationale", return_value=["reason"]))
                stack.enter_context(mock.patch.object(pl, "build_rule_rationale", return_value="rule rationale"))
                stack.enter_context(
                    mock.patch.object(
                        pl.ac,
                        "load_asset_config",
                        return_value={"asset_key": "nvda", "live_operator_line_id": "ret_60_sma_gap_60_atr_pct_20"},
                    )
                )
                stack.enter_context(mock.patch.object(pl.ac, "get_asset_symbol", return_value="NVDA"))
                stack.enter_context(mock.patch.object(pl.ac, "get_latest_prediction_path", return_value=prediction_path))
                pl.main()

            payload = json.loads(prediction_path.read_text(encoding="utf-8"))

        self.assertEqual(payload["live_operator_line_id"], "ret_60_sma_gap_60_atr_pct_20")

    def test_main_omits_live_operator_line_id_when_actual_live_path_differs_from_config(self) -> None:
        latest_live = pd.DataFrame(
            [
                {
                    "date": pd.Timestamp("2026-04-15"),
                    "open": 100.0,
                    "high": 102.0,
                    "low": 99.0,
                    "close": 101.0,
                }
            ]
        )
        splits = {
            "test": mock.Mock(frame=pd.DataFrame({"date": [pd.Timestamp("2026-03-31")]})),
        }
        model_artifacts = {
            "model_family": "logistic",
            "threshold": 0.5,
            "train_frame": pd.DataFrame({"baseline_feature": [1.0]}),
            "feature_names": ["baseline_feature", "ret_60", "sma_gap_60"],
            "default_interactions": [],
            "live_label_mode": "drop-neutral",
        }
        with tempfile.TemporaryDirectory() as tmp:
            prediction_path = Path(tmp) / "latest_prediction.json"
            with ExitStack() as stack:
                stack.enter_context(mock.patch.object(pl.tr, "set_seed"))
                stack.enter_context(mock.patch.object(pl.tr, "get_env_int", return_value=pl.tr.SEED))
                stack.enter_context(mock.patch.object(pl.tr, "FEATURE_COLUMNS", ["baseline_feature"]))
                stack.enter_context(mock.patch.object(pl, "download_asset_prices", return_value="raw_prices"))
                stack.enter_context(mock.patch.object(pl, "add_price_features", return_value="price_features"))
                stack.enter_context(mock.patch.object(pl, "add_relative_strength_features", return_value="relative_features"))
                stack.enter_context(mock.patch.object(pl, "add_context_features", return_value=latest_live))
                stack.enter_context(mock.patch.object(pl, "download_vix_prices", return_value="vix_prices", create=True))
                stack.enter_context(mock.patch.object(pl, "add_vix_features", return_value=latest_live, create=True))
                stack.enter_context(mock.patch.object(pl.tr, "load_splits", return_value=splits))
                stack.enter_context(
                    mock.patch.object(
                        pl,
                        "build_feature_names",
                        return_value=["baseline_feature", "ret_60", "sma_gap_60"],
                    )
                )
                stack.enter_context(mock.patch.object(pl, "fit_model", return_value=model_artifacts))
                stack.enter_context(
                    mock.patch.object(
                        pl,
                        "score_latest_row",
                        return_value=(
                            np.array([[1.0]], dtype=np.float32),
                            {"ret_60": 0.1, "sma_gap_60": -0.05},
                        ),
                    )
                )
                stack.enter_context(mock.patch.object(pl, "predict_probabilities", return_value=np.array([0.7], dtype=np.float32)))
                stack.enter_context(
                    mock.patch.object(pl, "build_history_probabilities", return_value=np.array([0.2, 0.4, 0.6], dtype=np.float32))
                )
                stack.enter_context(mock.patch.object(pl, "classify_signal", return_value=("bullish", {"confidence_gap": 0.2})))
                stack.enter_context(mock.patch.object(pl, "apply_buy_point_overlay", return_value=("bullish", {"buy_point_ok": True})))
                stack.enter_context(mock.patch.object(pl, "get_rule_top_pct", return_value=20.0))
                stack.enter_context(mock.patch.object(pl, "summarize_rule", return_value={"rule_name": "top_20pct_reference", "selected": True}))
                stack.enter_context(mock.patch.object(pl, "build_model_rationale", return_value=["reason"]))
                stack.enter_context(mock.patch.object(pl, "build_rule_rationale", return_value="rule rationale"))
                stack.enter_context(
                    mock.patch.object(
                        pl.ac,
                        "load_asset_config",
                        return_value={"asset_key": "nvda", "live_operator_line_id": "ret_60_sma_gap_60_atr_pct_20"},
                    )
                )
                stack.enter_context(mock.patch.object(pl.ac, "get_asset_symbol", return_value="NVDA"))
                stack.enter_context(mock.patch.object(pl.ac, "get_latest_prediction_path", return_value=prediction_path))
                pl.main()

            payload = json.loads(prediction_path.read_text(encoding="utf-8"))

        self.assertNotIn("live_operator_line_id", payload)

    def test_main_writes_explicit_slv_live_operator_line_for_hard_gate_two_expert_path(self) -> None:
        latest_live = pd.DataFrame(
            [
                {
                    "date": pd.Timestamp("2026-04-15"),
                    "open": 100.0,
                    "high": 102.0,
                    "low": 99.0,
                    "close": 101.0,
                }
            ]
        )
        splits = {
            "test": mock.Mock(frame=pd.DataFrame({"date": [pd.Timestamp("2026-03-31")]})),
        }
        model_artifacts = {
            "model_family": "hard_gate_two_expert",
            "threshold": 0.5,
            "train_frame": pd.DataFrame({"baseline_feature": [1.0]}),
            "left_expert": "gdx_relative_dual",
            "right_expert": "gdx_context",
            "outer_gate_feature": "price_ratio_benchmark_z_20",
            "outer_gate_threshold": 0.141332,
            "feature_names": [
                "baseline_feature",
                "ret_60",
                "sma_gap_60",
                "distance_to_252_high",
                "rs_vs_benchmark_60",
                "price_ratio_benchmark_z_20",
                "atr_pct_20_percentile",
            ],
            "default_interactions": [],
            "live_label_mode": "future-return-top-bottom-15pct",
        }
        with tempfile.TemporaryDirectory() as tmp:
            prediction_path = Path(tmp) / "latest_prediction.json"
            with ExitStack() as stack:
                stack.enter_context(mock.patch.object(pl.tr, "set_seed"))
                stack.enter_context(mock.patch.object(pl.tr, "get_env_int", return_value=pl.tr.SEED))
                stack.enter_context(mock.patch.object(pl.tr, "FEATURE_COLUMNS", ["baseline_feature"]))
                stack.enter_context(mock.patch.object(pl, "download_asset_prices", return_value="raw_prices"))
                stack.enter_context(mock.patch.object(pl, "add_price_features", return_value="price_features"))
                stack.enter_context(mock.patch.object(pl, "add_relative_strength_features", return_value="relative_features"))
                stack.enter_context(mock.patch.object(pl, "add_context_features", return_value=latest_live))
                stack.enter_context(mock.patch.object(pl, "download_vix_prices", return_value="vix_prices", create=True))
                stack.enter_context(mock.patch.object(pl, "add_vix_features", return_value=latest_live, create=True))
                stack.enter_context(mock.patch.object(pl.tr, "load_splits", return_value=splits))
                stack.enter_context(
                    mock.patch.object(
                        pl,
                        "build_feature_names",
                        return_value=[
                            "baseline_feature",
                            "ret_60",
                            "sma_gap_60",
                            "distance_to_252_high",
                            "rs_vs_benchmark_60",
                            "price_ratio_benchmark_z_20",
                            "atr_pct_20_percentile",
                        ],
                    )
                )
                stack.enter_context(mock.patch.object(pl, "fit_model", return_value=model_artifacts))
                stack.enter_context(
                    mock.patch.object(
                        pl,
                        "score_latest_row",
                        return_value=(
                            latest_live.copy(),
                            {
                                "ret_60": 0.1,
                                "sma_gap_60": -0.05,
                                "distance_to_252_high": -0.1,
                                "rs_vs_benchmark_60": 0.2,
                                "price_ratio_benchmark_z_20": 0.3,
                                "atr_pct_20_percentile": 0.4,
                            },
                        ),
                    )
                )
                stack.enter_context(mock.patch.object(pl, "predict_probabilities", return_value=np.array([0.7], dtype=np.float32)))
                stack.enter_context(
                    mock.patch.object(pl, "build_history_probabilities", return_value=np.array([0.2, 0.4, 0.6], dtype=np.float32))
                )
                stack.enter_context(mock.patch.object(pl, "classify_signal", return_value=("bullish", {"confidence_gap": 0.2})))
                stack.enter_context(mock.patch.object(pl, "apply_buy_point_overlay", return_value=("bullish", {"buy_point_ok": True})))
                stack.enter_context(mock.patch.object(pl, "get_rule_top_pct", return_value=15.0))
                stack.enter_context(mock.patch.object(pl, "summarize_rule", return_value={"rule_name": "top_15pct_reference", "selected": True}))
                stack.enter_context(mock.patch.object(pl, "build_model_rationale", return_value=["reason"]))
                stack.enter_context(mock.patch.object(pl, "build_rule_rationale", return_value="rule rationale"))
                stack.enter_context(
                    mock.patch.object(
                        pl.ac,
                        "load_asset_config",
                        return_value={
                            "asset_key": "slv",
                            "benchmark_symbol": "GDX",
                            "live_model_family": "hard_gate_two_expert",
                            "live_operator_line_id": "hard_gate_two_expert_gdx_live",
                            "live_label_mode": "future-return-top-bottom-15pct",
                        },
                    )
                )
                stack.enter_context(mock.patch.object(pl.ac, "get_asset_symbol", return_value="SLV"))
                stack.enter_context(mock.patch.object(pl.ac, "get_latest_prediction_path", return_value=prediction_path))
                pl.main()

            payload = json.loads(prediction_path.read_text(encoding="utf-8"))

        self.assertEqual(payload["live_operator_line_id"], "hard_gate_two_expert_gdx_live")
        self.assertEqual(payload["model_summary"]["model_family"], "hard_gate_two_expert")
        self.assertEqual(payload["model_summary"]["label_mode"], "future-return-top-bottom-15pct")
        self.assertEqual(payload["live_provenance"]["benchmark_symbol"], "GDX")
        self.assertEqual(payload["live_provenance"]["outer_gate_feature"], "price_ratio_benchmark_z_20")
        self.assertEqual(payload["live_provenance"]["operator_line_id"], "hard_gate_two_expert_gdx_live")

    def test_main_writes_explicit_gld_vix_term_live_operator_line_for_mixed_path(self) -> None:
        latest_live = pd.DataFrame(
            [
                {
                    "date": pd.Timestamp("2026-04-15"),
                    "open": 100.0,
                    "high": 102.0,
                    "low": 99.0,
                    "close": 101.0,
                }
            ]
        )
        splits = {"test": mock.Mock(frame=pd.DataFrame({"date": [pd.Timestamp("2026-03-31")]}))}
        model_artifacts = {
            "model_family": "hard_gate_two_expert_mixed",
            "threshold": 0.5,
            "train_frame": pd.DataFrame({"baseline_feature": [1.0]}),
            "left_expert": "dual_context",
            "right_expert": "context_no_atr",
            "outer_gate_feature": "atr_pct_20_percentile",
            "outer_gate_threshold": 0.7,
            "feature_names": [
                "baseline_feature",
                "ret_60",
                "sma_gap_60",
                "trend_quality_20",
                "percent_up_days_20",
                "bollinger_bandwidth_20",
                "distance_from_60d_low",
                "atr_pct_20_percentile",
                "above_200dma_flag",
            ],
            "default_interactions": [],
            "live_label_mode": "future-return-top-bottom-10pct",
        }
        with tempfile.TemporaryDirectory() as tmp:
            prediction_path = Path(tmp) / "latest_prediction.json"
            with ExitStack() as stack:
                stack.enter_context(mock.patch.object(pl.tr, "set_seed"))
                stack.enter_context(mock.patch.object(pl.tr, "get_env_int", return_value=pl.tr.SEED))
                stack.enter_context(mock.patch.object(pl.tr, "FEATURE_COLUMNS", ["baseline_feature"]))
                stack.enter_context(mock.patch.object(pl, "download_asset_prices", return_value="raw_prices"))
                stack.enter_context(mock.patch.object(pl, "add_price_features", return_value="price_features"))
                stack.enter_context(mock.patch.object(pl, "add_relative_strength_features", return_value="relative_features"))
                stack.enter_context(mock.patch.object(pl, "add_context_features", return_value=latest_live))
                stack.enter_context(mock.patch.object(pl, "download_vix_prices", return_value="vix_prices", create=True))
                stack.enter_context(mock.patch.object(pl, "add_vix_features", return_value=latest_live, create=True))
                stack.enter_context(mock.patch.object(pl, "download_vix3m_prices", return_value="vix3m_prices", create=True))
                stack.enter_context(mock.patch.object(pl, "add_vix_term_structure_features", return_value=latest_live, create=True))
                stack.enter_context(mock.patch.object(pl.tr, "load_splits", return_value=splits))
                stack.enter_context(mock.patch.object(pl, "build_feature_names", return_value=["baseline_feature"]))
                stack.enter_context(mock.patch.object(pl, "fit_model", return_value=model_artifacts))
                stack.enter_context(mock.patch.object(pl, "score_latest_row", return_value=(latest_live.copy(), {"ret_60": 0.1, "vix_vxv_ratio_pct_63_rolling_max_3": 0.2})))
                stack.enter_context(mock.patch.object(pl, "predict_probabilities", return_value=np.array([0.7], dtype=np.float32)))
                stack.enter_context(mock.patch.object(pl, "build_history_probabilities", return_value=np.array([0.2, 0.4, 0.6], dtype=np.float32)))
                stack.enter_context(mock.patch.object(pl, "classify_signal", return_value=("bullish", {"confidence_gap": 0.2})))
                stack.enter_context(mock.patch.object(pl, "get_rule_top_pct", return_value=20.0))
                stack.enter_context(mock.patch.object(pl, "summarize_rule", return_value={"rule_name": "top_20pct_reference", "selected": True}))
                stack.enter_context(mock.patch.object(pl, "build_model_rationale", return_value=["reason"]))
                stack.enter_context(mock.patch.object(pl, "build_rule_rationale", return_value="rule rationale"))
                stack.enter_context(
                    mock.patch.object(
                        pl.ac,
                        "load_asset_config",
                        return_value={
                            "asset_key": "gld",
                            "live_model_family": "hard_gate_two_expert_mixed",
                            "live_label_mode": "future-return-top-bottom-10pct",
                            "live_operator_line_id": "gld_mixed_vix_vxv_term_panic_live",
                            "live_left_expert": "dual_context",
                            "live_right_expert": "context_no_atr",
                            "live_outer_gate_feature": "atr_pct_20_percentile",
                            "live_outer_gate_threshold": 0.7,
                            "live_term_panic_feature": "vix_vxv_ratio_pct_63_rolling_max_3",
                            "live_term_panic_threshold": 0.9,
                        },
                    )
                )
                stack.enter_context(mock.patch.object(pl.ac, "get_asset_symbol", return_value="GLD"))
                stack.enter_context(mock.patch.object(pl.ac, "get_latest_prediction_path", return_value=prediction_path))
                pl.main()

            payload = json.loads(prediction_path.read_text(encoding="utf-8"))

        self.assertEqual(payload["live_operator_line_id"], "gld_mixed_vix_vxv_term_panic_live")
        self.assertEqual(payload["model_summary"]["live_decision_rule"], "threshold_plus_buy_point_overlay_plus_vix_vxv_term_panic_block")
        self.assertEqual(payload["live_provenance"]["operator_line_id"], "gld_mixed_vix_vxv_term_panic_live")
        self.assertEqual(payload["live_provenance"]["left_expert"], "dual_context")
        self.assertEqual(payload["live_provenance"]["right_expert"], "context_no_atr")
        self.assertEqual(payload["live_provenance"]["outer_gate_feature"], "atr_pct_20_percentile")
        self.assertEqual(payload["live_provenance"]["decision_overlay"], "vix_vxv_term_panic_block")
        self.assertEqual(payload["live_provenance"]["term_panic_feature"], "vix_vxv_ratio_pct_63_rolling_max_3")

    def test_fit_hard_gate_two_expert_mixed_model_uses_baseline_module_for_baseline_line(self) -> None:
        frame = pd.DataFrame(
            {
                "date": [pd.Timestamp("2026-03-01"), pd.Timestamp("2026-03-02")],
                tr.TARGET_COLUMN: [1.0, 0.0],
                "above_200dma_flag": [1.0, 0.0],
                "ret_60": [0.1, 0.2],
                "baseline_only_left": [0.3, 0.1],
                "baseline_only_right": [-0.2, -0.1],
            }
        )
        fake_rb = types.SimpleNamespace()
        fake_rb.build_labeled_frame = mock.Mock(return_value=frame)
        fake_rb.select_threshold_with_steps = mock.Mock(return_value=0.55)
        fake_rb.split_frame = mock.Mock(
            return_value={
                "train": frame.iloc[[0]].reset_index(drop=True),
                "validation": frame.iloc[[0]].reset_index(drop=True),
                "test": frame.iloc[[1]].reset_index(drop=True),
            }
        )

        def train_model_side_effect(_frame, _expert, **kwargs):
            extra_features = list(kwargs["extra_features"])
            return None, {
                "feature_names": extra_features,
                "validation_probabilities": np.array([0.7], dtype=np.float32),
                "test_probabilities": np.array([0.6], dtype=np.float32),
            }

        fake_rb.train_model = mock.Mock(side_effect=train_model_side_effect)
        fake_baseline = types.SimpleNamespace(
            LEFT_EXPERT="baseline_left",
            RIGHT_EXPERT="baseline_right",
            LEFT_EXTRA_FEATURES=("ret_60", "baseline_only_left"),
            RIGHT_EXTRA_FEATURES=("ret_60", "baseline_only_right"),
            OUTER_GATE_FEATURE="above_200dma_flag",
            OUTER_GATE_THRESHOLD=0.5,
        )

        with mock.patch.dict(
            sys.modules,
            {
                "research_batch": fake_rb,
                "research_gld_current_live_mixed_baseline": fake_baseline,
            },
        ):
            with mock.patch.object(pl, "get_live_operator_line_id", return_value="gld_current_live_mixed_live"):
                artifacts = pl.fit_hard_gate_two_expert_mixed_model(raw_prices=mock.sentinel.raw_prices)

        left_call = fake_rb.train_model.call_args_list[0]
        right_call = fake_rb.train_model.call_args_list[1]
        self.assertEqual(left_call.kwargs["extra_features"], ("ret_60", "baseline_only_left"))
        self.assertEqual(right_call.kwargs["extra_features"], ("ret_60", "baseline_only_right"))
        self.assertEqual(artifacts["left_expert"], "baseline_left")
        self.assertEqual(artifacts["right_expert"], "baseline_right")
        self.assertEqual(artifacts["outer_gate_threshold"], 0.5)

    def test_main_writes_explicit_gld_baseline_live_operator_line_without_term_panic_overlay(self) -> None:
        latest_live = pd.DataFrame(
            [
                {
                    "date": pd.Timestamp("2026-04-15"),
                    "open": 100.0,
                    "high": 102.0,
                    "low": 99.0,
                    "close": 101.0,
                }
            ]
        )
        splits = {"test": mock.Mock(frame=pd.DataFrame({"date": [pd.Timestamp("2026-03-31")]}))}
        model_artifacts = {
            "model_family": "hard_gate_two_expert_mixed",
            "threshold": 0.5,
            "train_frame": pd.DataFrame({"baseline_feature": [1.0]}),
            "left_expert": "dual_context",
            "right_expert": "context_no_atr",
            "outer_gate_feature": "atr_pct_20_percentile",
            "outer_gate_threshold": 0.7,
            "feature_names": [
                "baseline_feature",
                "ret_60",
                "sma_gap_60",
                "trend_quality_20",
                "percent_up_days_20",
                "bollinger_bandwidth_20",
                "distance_from_60d_low",
                "atr_pct_20_percentile",
                "above_200dma_flag",
            ],
            "default_interactions": [],
            "live_label_mode": "future-return-top-bottom-10pct",
        }
        with tempfile.TemporaryDirectory() as tmp:
            prediction_path = Path(tmp) / "latest_prediction.json"
            with ExitStack() as stack:
                stack.enter_context(mock.patch.object(pl.tr, "set_seed"))
                stack.enter_context(mock.patch.object(pl.tr, "get_env_int", return_value=pl.tr.SEED))
                stack.enter_context(mock.patch.object(pl.tr, "FEATURE_COLUMNS", ["baseline_feature"]))
                stack.enter_context(mock.patch.object(pl, "download_asset_prices", return_value="raw_prices"))
                stack.enter_context(mock.patch.object(pl, "add_price_features", return_value="price_features"))
                stack.enter_context(mock.patch.object(pl, "add_relative_strength_features", return_value="relative_features"))
                stack.enter_context(mock.patch.object(pl, "add_context_features", return_value=latest_live))
                stack.enter_context(mock.patch.object(pl, "download_vix_prices", return_value="vix_prices", create=True))
                stack.enter_context(mock.patch.object(pl, "add_vix_features", return_value=latest_live, create=True))
                stack.enter_context(mock.patch.object(pl, "download_vix3m_prices", return_value="vix3m_prices", create=True))
                stack.enter_context(mock.patch.object(pl, "add_vix_term_structure_features", return_value=latest_live, create=True))
                stack.enter_context(mock.patch.object(pl.tr, "load_splits", return_value=splits))
                stack.enter_context(mock.patch.object(pl, "build_feature_names", return_value=["baseline_feature"]))
                stack.enter_context(mock.patch.object(pl, "fit_model", return_value=model_artifacts))
                stack.enter_context(mock.patch.object(pl, "score_latest_row", return_value=(latest_live.copy(), {"ret_60": 0.1})))
                stack.enter_context(mock.patch.object(pl, "predict_probabilities", return_value=np.array([0.7], dtype=np.float32)))
                stack.enter_context(mock.patch.object(pl, "build_history_probabilities", return_value=np.array([0.2, 0.4, 0.6], dtype=np.float32)))
                stack.enter_context(mock.patch.object(pl, "classify_signal", return_value=("bullish", {"confidence_gap": 0.2})))
                stack.enter_context(mock.patch.object(pl, "get_rule_top_pct", return_value=20.0))
                stack.enter_context(mock.patch.object(pl, "summarize_rule", return_value={"rule_name": "top_20pct_reference", "selected": True}))
                stack.enter_context(mock.patch.object(pl, "build_model_rationale", return_value=["reason"]))
                stack.enter_context(mock.patch.object(pl, "build_rule_rationale", return_value="rule rationale"))
                stack.enter_context(
                    mock.patch.object(
                        pl.ac,
                        "load_asset_config",
                        return_value={
                            "asset_key": "gld",
                            "live_model_family": "hard_gate_two_expert_mixed",
                            "live_label_mode": "future-return-top-bottom-10pct",
                            "live_operator_line_id": "gld_current_live_mixed_live",
                            "live_left_expert": "dual_context",
                            "live_right_expert": "context_no_atr",
                            "live_outer_gate_feature": "atr_pct_20_percentile",
                            "live_outer_gate_threshold": 0.7,
                            "live_term_panic_feature": "vix_vxv_ratio_pct_63_rolling_max_3",
                            "live_term_panic_threshold": 0.9,
                        },
                    )
                )
                stack.enter_context(mock.patch.object(pl.ac, "get_asset_symbol", return_value="GLD"))
                stack.enter_context(mock.patch.object(pl.ac, "get_latest_prediction_path", return_value=prediction_path))
                pl.main()

            payload = json.loads(prediction_path.read_text(encoding="utf-8"))

        self.assertEqual(payload["live_operator_line_id"], "gld_current_live_mixed_live")
        self.assertEqual(payload["model_summary"]["live_decision_rule"], "threshold_plus_buy_point_overlay")
        self.assertEqual(payload["live_provenance"]["operator_line_id"], "gld_current_live_mixed_live")
        self.assertEqual(payload["live_provenance"]["left_expert"], "dual_context")
        self.assertEqual(payload["live_provenance"]["right_expert"], "context_no_atr")
        self.assertEqual(payload["live_provenance"]["outer_gate_feature"], "atr_pct_20_percentile")
        self.assertNotIn("decision_overlay", payload["live_provenance"])
        self.assertNotIn("term_panic_feature", payload["live_provenance"])

    def test_main_writes_explicit_tsla_live_operator_line_for_xgboost_path(self) -> None:
        latest_live = pd.DataFrame(
            [
                {
                    "date": pd.Timestamp("2026-04-15"),
                    "open": 100.0,
                    "high": 102.0,
                    "low": 99.0,
                    "close": 101.0,
                    "distance_to_252_high": -0.18,
                }
            ]
        )
        splits = {
            "test": mock.Mock(frame=pd.DataFrame({"date": [pd.Timestamp("2026-03-31")]})),
        }
        model_artifacts = {
            "model_family": "xgboost",
            "threshold": 0.5,
            "train_frame": pd.DataFrame({"baseline_feature": [1.0]}),
            "feature_names": ["baseline_feature", "distance_to_252_high"],
            "default_interactions": [],
            "live_label_mode": "future-return-top-bottom-30pct",
            "xgboost_params": {
                "n_estimators": 150,
                "max_depth": 2,
                "learning_rate": 0.05,
            },
        }
        with tempfile.TemporaryDirectory() as tmp:
            prediction_path = Path(tmp) / "latest_prediction.json"
            with ExitStack() as stack:
                stack.enter_context(mock.patch.object(pl.tr, "set_seed"))
                stack.enter_context(mock.patch.object(pl.tr, "get_env_int", return_value=pl.tr.SEED))
                stack.enter_context(mock.patch.object(pl.tr, "FEATURE_COLUMNS", ["baseline_feature"]))
                stack.enter_context(mock.patch.object(pl, "download_asset_prices", return_value="raw_prices"))
                stack.enter_context(mock.patch.object(pl, "add_price_features", return_value="price_features"))
                stack.enter_context(mock.patch.object(pl, "add_relative_strength_features", return_value="relative_features"))
                stack.enter_context(mock.patch.object(pl, "add_context_features", return_value=latest_live))
                stack.enter_context(mock.patch.object(pl, "download_vix_prices", return_value="vix_prices", create=True))
                stack.enter_context(mock.patch.object(pl, "add_vix_features", return_value=latest_live, create=True))
                stack.enter_context(mock.patch.object(pl.tr, "load_splits", return_value=splits))
                stack.enter_context(mock.patch.object(pl, "build_feature_names", return_value=["baseline_feature", "distance_to_252_high"]))
                stack.enter_context(mock.patch.object(pl, "fit_model", return_value=model_artifacts))
                stack.enter_context(
                    mock.patch.object(
                        pl,
                        "score_latest_row",
                        return_value=(
                            np.array([[1.0]], dtype=np.float32),
                            {"distance_to_252_high": -0.18},
                        ),
                    )
                )
                stack.enter_context(mock.patch.object(pl, "predict_probabilities", return_value=np.array([0.8123], dtype=np.float32)))
                stack.enter_context(
                    mock.patch.object(pl, "build_history_probabilities", return_value=np.array([0.2, 0.4, 0.6], dtype=np.float32))
                )
                stack.enter_context(mock.patch.object(pl, "classify_signal", return_value=("bullish", {"confidence_gap": 0.3123})))
                stack.enter_context(mock.patch.object(pl, "apply_buy_point_overlay", return_value=("bullish", {"buy_point_ok": True})))
                stack.enter_context(mock.patch.object(pl, "get_rule_top_pct", return_value=30.0))
                stack.enter_context(mock.patch.object(pl, "summarize_rule", return_value={"rule_name": "top_30pct_reference", "selected": True}))
                stack.enter_context(mock.patch.object(pl, "build_model_rationale", return_value=["reason"]))
                stack.enter_context(mock.patch.object(pl, "build_rule_rationale", return_value="rule rationale"))
                stack.enter_context(
                    mock.patch.object(
                        pl.ac,
                        "load_asset_config",
                        return_value={
                            "asset_key": "tsla",
                            "live_model_family": "xgboost",
                            "live_label_mode": "future-return-top-bottom-30pct",
                            "live_operator_line_id": "xgboost_tb30_distance_live",
                            "live_extra_features": ["distance_to_252_high"],
                            "live_reference_top_pct": 30,
                            "live_xgboost_params": {
                                "n_estimators": 150,
                                "max_depth": 2,
                                "learning_rate": 0.05,
                            },
                        },
                    )
                )
                stack.enter_context(mock.patch.object(pl.ac, "get_live_model_family", return_value="xgboost"))
                stack.enter_context(mock.patch.object(pl.ac, "get_asset_symbol", return_value="TSLA"))
                stack.enter_context(mock.patch.object(pl.ac, "get_latest_prediction_path", return_value=prediction_path))
                pl.main()

            payload = json.loads(prediction_path.read_text(encoding="utf-8"))

        self.assertEqual(payload["live_operator_line_id"], "xgboost_tb30_distance_live")
        self.assertEqual(payload["model_summary"]["model_family"], "xgboost")
        self.assertEqual(payload["model_summary"]["label_mode"], "future-return-top-bottom-30pct")

    def test_nvda_config_declares_live_operator_line_and_features(self) -> None:
        config_path = Path(__file__).resolve().parents[1] / "assets" / "nvda" / "config.json"
        config = json.loads(config_path.read_text(encoding="utf-8"))

        self.assertEqual(config["live_operator_line_id"], "ret_60_sma_gap_60_atr_pct_20")
        self.assertEqual(config["live_extra_features"], ["ret_60", "sma_gap_60", "atr_pct_20"])
        self.assertEqual(config["upper_barrier"], 0.15)
        self.assertEqual(config["lower_barrier"], -0.08)

    def test_slv_config_declares_live_hard_gate_two_expert_path(self) -> None:
        config_path = Path(__file__).resolve().parents[1] / "assets" / "slv" / "config.json"
        config = json.loads(config_path.read_text(encoding="utf-8"))

        self.assertEqual(config["live_model_family"], "hard_gate_two_expert")
        self.assertEqual(config["live_operator_line_id"], "hard_gate_two_expert_gdx_live")
        self.assertEqual(config["live_label_mode"], "future-return-top-bottom-15pct")
        self.assertEqual(config["benchmark_symbol"], "GDX")

    def test_tsla_config_declares_live_xgboost_path(self) -> None:
        config_path = Path(__file__).resolve().parents[1] / "assets" / "tsla" / "config.json"
        config = json.loads(config_path.read_text(encoding="utf-8"))

        self.assertEqual(config["live_model_family"], "xgboost")
        self.assertEqual(config["live_operator_line_id"], "xgboost_tb30_distance_live")
        self.assertEqual(config["live_label_mode"], "future-return-top-bottom-30pct")
        self.assertEqual(config["live_extra_features"], ["distance_to_252_high"])


if __name__ == "__main__":
    unittest.main()
