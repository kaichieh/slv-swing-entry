from __future__ import annotations

import unittest
import types
from unittest import mock

import numpy as np
import pandas as pd

import research_batch as rb


class _FakeXGBClassifier:
    def __init__(self, **kwargs) -> None:
        self.kwargs = kwargs

    def fit(self, train_x, train_y, sample_weight=None) -> None:
        self.train_rows = len(train_x)

    def predict_proba(self, matrix):
        rows = len(matrix)
        positive = np.linspace(0.35, 0.65, rows, dtype=np.float32)
        negative = 1.0 - positive
        return np.column_stack([negative, positive])


def make_frame(rows: int = 90) -> pd.DataFrame:
    values = np.linspace(-1.0, 1.0, rows, dtype=np.float32)
    frame = pd.DataFrame(
        {
            name: values + (idx * 0.01)
            for idx, name in enumerate(rb.pr.FEATURE_COLUMNS)
        }
    )
    frame["date"] = pd.date_range("2020-01-01", periods=rows, freq="D")
    frame[rb.pr.TARGET_COLUMN] = (np.arange(rows) % 3 == 0).astype(np.float32)
    frame[rb.FUTURE_RETURN_COLUMN] = np.linspace(-0.05, 0.10, rows, dtype=np.float32)
    return frame


class XGBoostSupportTests(unittest.TestCase):
    def test_require_xgboost_raises_clear_error_when_dependency_missing(self) -> None:
        with mock.patch.object(rb, "_XGBOOST_IMPORT_ERROR", ModuleNotFoundError("No module named 'xgboost'")):
            with mock.patch.object(rb, "_XGBOOST_MODULE", None):
                with mock.patch.object(rb.importlib, "import_module", side_effect=ModuleNotFoundError("No module named 'xgboost'")):
                    with self.assertRaisesRegex(ModuleNotFoundError, "xgboost"):
                        rb.require_xgboost()

    def test_train_xgboost_model_returns_probabilities_and_metadata(self) -> None:
        fake_module = types.SimpleNamespace(XGBClassifier=_FakeXGBClassifier)
        with mock.patch.object(rb, "_XGBOOST_MODULE", fake_module):
            result, artifacts = rb.train_xgboost_model(make_frame(), "demo_xgb")

        self.assertEqual(result.name, "demo_xgb")
        self.assertEqual(artifacts["model_family"], "xgboost")
        self.assertEqual(len(artifacts["test_probabilities"]), result.test_rows)
        self.assertGreaterEqual(result.threshold, rb.tr.THRESHOLD_MIN)
        self.assertLessEqual(result.threshold, rb.tr.THRESHOLD_MAX)


def make_regime_frame(rows: int = 240) -> pd.DataFrame:
    index = np.arange(rows, dtype=np.float32)
    gate = ((index // 30) % 2).astype(np.float32)
    signal = np.sin(index / 6.0).astype(np.float32)
    labels = np.where(gate > 0.5, signal < 0.0, signal > 0.0).astype(np.float32)
    future_returns = np.where(labels > 0.5, 0.08, -0.04).astype(np.float32)

    frame = pd.DataFrame(
        {
            name: (signal + (idx * 0.01)).astype(np.float32)
            for idx, name in enumerate(rb.pr.FEATURE_COLUMNS)
        }
    )
    frame["date"] = pd.date_range("2020-01-01", periods=rows, freq="D")
    frame[rb.pr.TARGET_COLUMN] = labels
    frame[rb.FUTURE_RETURN_COLUMN] = future_returns
    frame["ret_60"] = signal
    frame["sma_gap_60"] = signal * 0.8
    frame["above_200dma_flag"] = gate
    return frame


class RegimeDualLogisticTests(unittest.TestCase):
    def test_train_model_regime_dual_logistic_returns_family_metadata(self) -> None:
        result, artifacts = rb.train_model(
            make_regime_frame(),
            "demo_regime_dual",
            extra_features=("ret_60", "sma_gap_60", "above_200dma_flag"),
            model_family="regime_dual_logistic",
        )

        self.assertEqual(result.name, "demo_regime_dual")
        self.assertEqual(artifacts["model_family"], "regime_dual_logistic")
        self.assertEqual(len(artifacts["validation_probabilities"]), result.validation_rows)
        self.assertEqual(len(artifacts["test_probabilities"]), result.test_rows)

    def test_regime_dual_logistic_outperforms_single_logistic_on_regime_shifted_data(self) -> None:
        frame = make_regime_frame()

        logistic_result, _ = rb.train_model(
            frame,
            "demo_logistic",
            extra_features=("ret_60", "sma_gap_60", "above_200dma_flag"),
        )
        regime_result, _ = rb.train_model(
            frame,
            "demo_regime_dual",
            extra_features=("ret_60", "sma_gap_60", "above_200dma_flag"),
            model_family="regime_dual_logistic",
        )

        self.assertGreater(regime_result.test_bal_acc, logistic_result.test_bal_acc)
        self.assertGreater(regime_result.test_f1, logistic_result.test_f1)

    def test_evaluate_walk_forward_with_folds_supports_regime_dual_logistic(self) -> None:
        frame = make_regime_frame(300)
        rows = rb.evaluate_walk_forward_with_folds(
            frame,
            ("ret_60", "sma_gap_60", "above_200dma_flag"),
            folds=4,
            model_family="regime_dual_logistic",
        )

        self.assertEqual(len(rows), len(list(rb.walk_forward_splits(frame, folds=4))))
        self.assertTrue(all(row.test_bal_acc >= 0.0 for row in rows))


if __name__ == "__main__":
    unittest.main()
