from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest import mock

import numpy as np
import pandas as pd

import research_regression as rr
import research_regression_recent as rrr


class RegressionVixPipelineTests(unittest.TestCase):
    def test_build_dataset_adds_vix_features_before_feature_selection(self) -> None:
        vix_enriched = pd.DataFrame(
            {
                "date": pd.date_range("2026-01-01", periods=3, freq="D"),
                "close": [100.0, 101.0, 102.0],
                "baseline_feature": [0.1, 0.2, 0.3],
                "vix_close_lag1": [20.0, 21.0, 22.0],
            }
        )

        with mock.patch.object(rr, "load_raw_prices", return_value="raw_prices"):
            with mock.patch.object(rr.pr, "add_price_features", return_value="price_features"):
                with mock.patch.object(rr.pr, "add_relative_strength_features", return_value="relative_features"):
                    with mock.patch.object(rr.pr, "add_context_features", return_value="context_features"):
                        with mock.patch.object(rr.pr, "download_vix_prices", return_value="vix_prices") as download_vix_prices:
                            with mock.patch.object(rr.pr, "add_vix_features", return_value=vix_enriched) as add_vix_features:
                                with mock.patch.object(rr.pr, "build_barrier_labels", return_value=(np.array([1.0, 0.0, 1.0]), np.array([0.1, -0.2, 0.3]))) as build_barrier_labels:
                                    with mock.patch.object(rr, "build_feature_names", return_value=["baseline_feature", "vix_close_lag1"]):
                                        frame, feature_names = rr.build_dataset()

        download_vix_prices.assert_called_once_with()
        add_vix_features.assert_called_once_with("context_features", "vix_prices")
        pd.testing.assert_frame_equal(build_barrier_labels.call_args.args[0], vix_enriched)
        self.assertEqual(feature_names, ["baseline_feature", "vix_close_lag1"])
        self.assertIn("vix_close_lag1", frame.columns)

    def test_main_adds_vix_features_to_recent_live_regression_frame(self) -> None:
        frame = pd.DataFrame(
            {
                "date": pd.date_range("2026-01-01", periods=3, freq="D"),
                "baseline_feature": [0.1, 0.2, 0.3],
                "vix_close_lag1": [20.0, 21.0, 22.0],
                "future_return_60": [0.03, 0.02, 0.01],
            }
        )
        splits = {
            "train": frame.iloc[[0]].copy(),
            "validation": frame.iloc[[1]].copy(),
            "test": frame.iloc[[2]].copy(),
        }
        live_frame = pd.DataFrame(
            {
                "date": pd.to_datetime(["2026-04-14", "2026-04-15"]),
                "close": [110.0, 111.0],
                "baseline_feature": [0.4, 0.5],
                "vix_close_lag1": [23.0, 24.0],
            }
        )

        with tempfile.TemporaryDirectory() as tmp:
            output_path = Path(tmp) / "regression_recent.tsv"
            with mock.patch.object(rrr, "OUTPUT_PATH", str(output_path)):
                with mock.patch.object(rrr.tr, "set_seed"):
                    with mock.patch.object(rrr.tr, "get_env_int", return_value=rrr.tr.SEED):
                        with mock.patch.object(rrr, "get_env_int", side_effect=lambda name, default: 2 if name == "AR_REG_LOOKBACK" else default):
                            with mock.patch.object(rrr, "get_env_float", side_effect=lambda name, default: default):
                                with mock.patch.object(rrr, "get_env_str", side_effect=lambda name, default: default):
                                    with mock.patch.object(rrr.rr, "build_dataset", return_value=(frame, ["baseline_feature", "vix_close_lag1"])):
                                        with mock.patch.object(rrr.rr, "split_frame", return_value=splits):
                                            with mock.patch.object(rrr.rr, "load_raw_prices", return_value="raw_prices"):
                                                with mock.patch.object(rrr.pr, "add_price_features", return_value="price_features"):
                                                    with mock.patch.object(rrr.pr, "add_relative_strength_features", return_value="relative_features"):
                                                        with mock.patch.object(rrr.pr, "add_context_features", return_value="context_features"):
                                                            with mock.patch.object(rrr.pr, "download_vix_prices", return_value="vix_prices") as download_vix_prices:
                                                                with mock.patch.object(rrr.pr, "add_vix_features", return_value=live_frame) as add_vix_features:
                                                                    with mock.patch.object(rrr.pr, "build_barrier_labels", return_value=(np.array([1.0, 0.0]), np.array([0.05, 0.06]))) as build_barrier_labels:
                                                                        with mock.patch.object(rrr.rr, "standardize", side_effect=lambda train_x, other: (train_x, other)):
                                                                            with mock.patch.object(rrr.rr, "fit_ridge_regression", return_value=np.array([1.0, 0.0])):
                                                                                with mock.patch.object(
                                                                                    rrr.rr,
                                                                                    "predict",
                                                                                    side_effect=[
                                                                                        np.array([0.1], dtype=np.float64),
                                                                                        np.array([0.2], dtype=np.float64),
                                                                                        np.array([0.3, 0.4], dtype=np.float64),
                                                                                    ],
                                                                                ):
                                                                                    with mock.patch.object(rrr.ac, "get_asset_key", return_value="qqq"):
                                                                                        rrr.main()

                written = pd.read_csv(output_path, sep="\t")

        download_vix_prices.assert_called_once_with()
        add_vix_features.assert_called_once_with("context_features", "vix_prices")
        pd.testing.assert_frame_equal(build_barrier_labels.call_args.args[0], live_frame)
        self.assertIn("predicted_return", written.columns)
        self.assertEqual(len(written), 2)


if __name__ == "__main__":
    unittest.main()
