from __future__ import annotations

import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import pandas as pd

import research_gld_topbottom20_hard_gate_two_expert as winner


class GldWinningResearchTests(unittest.TestCase):
    def test_evaluate_winning_algorithm_uses_gld_inputs_when_env_points_elsewhere(self) -> None:
        payload_frame = pd.DataFrame(
            {
                "date": pd.date_range("2020-01-01", periods=6, freq="D"),
                winner.pr.TARGET_COLUMN: [0, 1, 0, 1, 0, 1],
                winner.rb.FUTURE_RETURN_COLUMN: [0.01, 0.02, -0.01, 0.03, -0.02, 0.04],
                "trend_quality_20": [0.0, 0.1, 0.2, 0.3, 0.4, 0.5],
                "rolling_vol_60": [0.001, 0.002, 0.01, 0.02, 0.03, 0.04],
            }
        )
        left_artifacts = {
            "validation_probabilities": [0.2, 0.8],
            "test_probabilities": [0.3, 0.9],
        }
        right_artifacts = {
            "validation_probabilities": [0.6, 0.4],
            "test_probabilities": [0.7, 0.5],
        }
        with mock.patch.dict(os.environ, {"AR_ASSET": "slv"}, clear=False):
            with mock.patch.object(winner.pr, "download_symbol_prices", return_value=payload_frame) as download_mock:
                with mock.patch.object(winner.rb, "build_labeled_frame", return_value=payload_frame):
                    with mock.patch.object(winner.rb, "split_frame", return_value={"validation": payload_frame.iloc[:2].copy(), "test": payload_frame.iloc[2:4].copy()}):
                        with mock.patch.object(winner.rb, "train_model", side_effect=[(None, left_artifacts), (None, right_artifacts)]):
                            with mock.patch.object(winner.rb, "select_threshold_with_steps", return_value=0.4):
                                with mock.patch.object(winner.tr, "compute_metrics", side_effect=[mock.Mock(f1=0.55, balanced_accuracy=0.53, positive_rate=0.5), mock.Mock(f1=0.96, balanced_accuracy=0.70, positive_rate=0.9)]):
                                    payload = winner.evaluate_winning_algorithm()

        self.assertEqual(payload["asset"], "gld")
        self.assertEqual(download_mock.call_args.args[0], winner.ac.get_asset_symbol("gld"))
        self.assertEqual(Path(download_mock.call_args.args[2]), winner.ac.get_raw_data_path("gld"))

    def test_main_writes_to_gld_cache_even_if_env_points_elsewhere(self) -> None:
        payload = {
            "asset": "gld",
            "label_mode": winner.LABEL_MODE,
            "algorithm": "hard_gate_two_expert",
            "headline_score": 0.7799,
        }
        with tempfile.TemporaryDirectory() as temp_dir:
            cache_dir = Path(temp_dir) / "gld-swing-entry"
            cache_dir.mkdir(parents=True, exist_ok=True)
            with mock.patch.dict(os.environ, {"AR_ASSET": "slv"}, clear=False):
                with mock.patch.object(winner, "evaluate_winning_algorithm", return_value=payload):
                    with mock.patch.object(
                        winner.ac,
                        "get_cache_dir",
                        side_effect=lambda asset_key=None: cache_dir if asset_key == "gld" else Path(temp_dir) / "wrong",
                    ):
                        winner.main()

            saved = cache_dir / "gld_topbottom20_hard_gate_two_expert.json"
            self.assertTrue(saved.exists())
            self.assertEqual(json.loads(saved.read_text(encoding="utf-8"))["asset"], "gld")


if __name__ == "__main__":
    unittest.main()
