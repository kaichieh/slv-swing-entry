from __future__ import annotations

import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import pandas as pd

import research_nvda_topbottom15_regime_dual_logistic as winner


class NvdaWinningResearchTests(unittest.TestCase):
    def test_evaluate_winning_algorithm_pins_nvda_branch_when_env_points_elsewhere(self) -> None:
        payload_frame = pd.DataFrame(
            {
                "date": pd.date_range("2020-01-01", periods=6, freq="D"),
                winner.pr.TARGET_COLUMN: [0, 1, 0, 1, 0, 1],
                winner.rb.FUTURE_RETURN_COLUMN: [0.01, 0.02, -0.01, 0.03, -0.02, 0.04],
            }
        )
        with mock.patch.dict(os.environ, {"AR_ASSET": "slv"}, clear=False):
            with mock.patch.object(winner.pr, "download_symbol_prices", return_value=payload_frame) as download_mock:
                with mock.patch.object(winner.rb, "build_labeled_frame", return_value=payload_frame) as build_mock:
                    with mock.patch.object(
                        winner.rb,
                        "train_model",
                        return_value=(
                            mock.Mock(
                                threshold=0.49,
                                validation_f1=0.76,
                                validation_bal_acc=0.61,
                                test_f1=0.85,
                                test_bal_acc=0.60,
                                test_positive_rate=0.84,
                            ),
                            {},
                        ),
                    ) as train_mock:
                        payload = winner.evaluate_winning_algorithm()

        self.assertEqual(payload["asset"], "nvda")
        self.assertEqual(download_mock.call_args.args[0], winner.ac.get_asset_symbol("nvda"))
        self.assertEqual(Path(download_mock.call_args.args[2]), winner.ac.get_raw_data_path("nvda"))

        self.assertEqual(build_mock.call_args.kwargs["horizon_days"], winner.HORIZON_DAYS)
        self.assertEqual(build_mock.call_args.kwargs["upper_barrier"], winner.UPPER_BARRIER)
        self.assertEqual(build_mock.call_args.kwargs["lower_barrier"], winner.LOWER_BARRIER)
        self.assertEqual(build_mock.call_args.kwargs["label_mode"], winner.LABEL_MODE)

        self.assertEqual(train_mock.call_args.kwargs["extra_features"], winner.EXTRA_FEATURES)
        self.assertEqual(train_mock.call_args.kwargs["model_family"], winner.MODEL_FAMILY)
        self.assertEqual(train_mock.call_args.kwargs["gate_feature"], winner.GATE_FEATURE)

    def test_main_writes_to_nvda_cache_even_if_env_points_elsewhere(self) -> None:
        payload = {
            "asset": "nvda",
            "label_mode": winner.LABEL_MODE,
            "model_family": winner.MODEL_FAMILY,
            "headline_score": 0.7357,
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

            saved = cache_dir / "nvda_topbottom15_regime_dual_logistic.json"
            self.assertTrue(saved.exists())
            self.assertEqual(json.loads(saved.read_text(encoding="utf-8"))["asset"], "nvda")


if __name__ == "__main__":
    unittest.main()
