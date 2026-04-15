from __future__ import annotations

import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import pandas as pd

import research_nvda_topbottom12_5_soft_gate_two_expert as winner


class NvdaSoftGateWinningResearchTests(unittest.TestCase):
    def test_evaluate_winning_algorithm_pins_soft_gate_nvda_branch_when_env_points_elsewhere(self) -> None:
        payload_frame = pd.DataFrame(
            {
                "date": pd.date_range("2020-01-01", periods=6, freq="D"),
                winner.pr.TARGET_COLUMN: [0, 1, 0, 1, 0, 1],
                winner.rb.FUTURE_RETURN_COLUMN: [0.01, 0.02, -0.01, 0.03, -0.02, 0.04],
                winner.SOFT_GATE_FEATURE: [0.7, 0.8, 0.9, 1.0, 1.1, 1.2],
            }
        )
        left_artifacts = {
            "validation_probabilities": [0.3, 0.8],
            "test_probabilities": [0.4, 0.9],
        }
        right_artifacts = {
            "validation_probabilities": [0.6, 0.4],
            "test_probabilities": [0.7, 0.5],
        }
        with mock.patch.dict(os.environ, {"AR_ASSET": "slv"}, clear=False):
            with mock.patch.object(winner.pr, "download_symbol_prices", return_value=payload_frame) as download_mock:
                with mock.patch.object(winner.rb, "build_labeled_frame", return_value=payload_frame) as build_mock:
                    with mock.patch.object(
                        winner.rb,
                        "split_frame",
                        return_value={"validation": payload_frame.iloc[:2].copy(), "test": payload_frame.iloc[2:4].copy()},
                    ):
                        with mock.patch.object(winner.rb, "train_model", side_effect=[(None, left_artifacts), (None, right_artifacts)]) as train_mock:
                            with mock.patch.object(
                                winner.tr,
                                "compute_metrics",
                                side_effect=[
                                    mock.Mock(f1=0.7310, balanced_accuracy=0.6601, positive_rate=0.75),
                                    mock.Mock(f1=0.9226, balanced_accuracy=0.8502, positive_rate=0.7533),
                                ],
                            ):
                                payload = winner.evaluate_winning_algorithm()

        self.assertEqual(payload["asset"], "nvda")
        self.assertEqual(download_mock.call_args.args[0], winner.ac.get_asset_symbol("nvda"))
        self.assertEqual(Path(download_mock.call_args.args[2]), winner.ac.get_raw_data_path("nvda"))
        self.assertEqual(build_mock.call_args.kwargs["horizon_days"], winner.HORIZON_DAYS)
        self.assertEqual(build_mock.call_args.kwargs["label_mode"], winner.LABEL_MODE)
        self.assertEqual(train_mock.call_args_list[0].kwargs["extra_features"], winner.EXTRA_FEATURES)
        self.assertEqual(train_mock.call_args_list[0].kwargs["drop_features"], winner.DROP_FEATURES)
        self.assertEqual(train_mock.call_args_list[0].kwargs["model_family"], winner.LEFT_MODEL_FAMILY)
        self.assertEqual(train_mock.call_args_list[1].kwargs["model_family"], winner.RIGHT_MODEL_FAMILY)
        self.assertEqual(train_mock.call_args_list[1].kwargs["gate_feature"], winner.RIGHT_GATE_FEATURE)
        self.assertEqual(payload["algorithm"], "soft_gate_two_expert")
        self.assertEqual(payload["soft_gate_feature"], winner.SOFT_GATE_FEATURE)

    def test_main_writes_to_nvda_cache_even_if_env_points_elsewhere(self) -> None:
        payload = {
            "asset": "nvda",
            "label_mode": winner.LABEL_MODE,
            "algorithm": "soft_gate_two_expert",
            "headline_score": 0.8237,
        }
        with tempfile.TemporaryDirectory() as temp_dir:
            cache_dir = Path(temp_dir) / "nvda-swing-entry"
            cache_dir.mkdir(parents=True, exist_ok=True)
            with mock.patch.dict(os.environ, {"AR_ASSET": "slv"}, clear=False):
                with mock.patch.object(winner, "evaluate_winning_algorithm", return_value=payload):
                    with mock.patch.object(
                        winner.ac,
                        "get_cache_dir",
                        side_effect=lambda asset_key=None: cache_dir if asset_key == "nvda" else Path(temp_dir) / "wrong",
                    ):
                        winner.main()

            saved = cache_dir / "nvda_topbottom12_5_soft_gate_two_expert.json"
            self.assertTrue(saved.exists())
            self.assertEqual(json.loads(saved.read_text(encoding="utf-8"))["asset"], "nvda")


if __name__ == "__main__":
    unittest.main()
