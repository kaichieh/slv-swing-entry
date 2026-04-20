from __future__ import annotations

import os
import unittest
from unittest import mock

import numpy as np
import pandas as pd

import prepare


def make_price_frame(rows: int = 80) -> pd.DataFrame:
    index = np.arange(rows, dtype=np.float64)
    close = 100.0 + 0.3 * index + 1.5 * np.sin(index / 4.0)
    open_price = close * (1.0 - 0.001)
    high = close * 1.01
    low = close * 0.99
    volume = 1_000_000 + 1_000 * index
    return pd.DataFrame(
        {
            "date": pd.date_range("2026-01-01", periods=rows, freq="D"),
            "open": open_price,
            "high": high,
            "low": low,
            "close": close,
            "volume": volume,
        }
    )


class PrepareOptionsIvFeatureTests(unittest.TestCase):
    def test_normalize_options_iv_history_accepts_aliases(self) -> None:
        frame = pd.DataFrame(
            {
                "asof_date": ["2026-01-02", "2026-01-01", "2026-01-02"],
                "atm_iv_30": [0.28, 0.25, 0.27],
            }
        )

        normalized = prepare.normalize_options_iv_history_frame(frame)

        self.assertEqual(list(normalized.columns), ["date", "target_30d_atm_iv"])
        self.assertEqual(list(normalized["date"]), list(pd.to_datetime(["2026-01-01", "2026-01-02"])))
        self.assertEqual(list(normalized["target_30d_atm_iv"]), [0.25, 0.27])

    def test_add_options_iv_features_aligns_backward_without_lookahead(self) -> None:
        asset = make_price_frame(rows=5)
        history = pd.DataFrame(
            {
                "date": pd.to_datetime(["2026-01-02", "2026-01-04"]),
                "target_30d_atm_iv": [0.22, 0.30],
            }
        )

        enriched = prepare.add_options_iv_features(asset, history)

        self.assertTrue(np.isnan(enriched.loc[0, "options_iv_30"]))
        self.assertTrue(np.isnan(enriched.loc[1, "options_iv_30"]))
        self.assertEqual(enriched.loc[2, "options_iv_30"], 0.22)
        self.assertEqual(enriched.loc[4, "options_iv_30"], 0.30)

    def test_add_options_iv_features_builds_iv_rank_columns(self) -> None:
        asset = make_price_frame(rows=320)
        history = pd.DataFrame(
            {
                "date": asset["date"],
                "target_30d_atm_iv": np.linspace(0.15, 0.55, len(asset)),
            }
        )

        enriched = prepare.add_options_iv_features(asset, history)
        lagged = enriched["options_iv_30"]
        expected_rank_252 = (lagged - lagged.rolling(252).min()) / (
            lagged.rolling(252).max() - lagged.rolling(252).min() + 1e-10
        )
        expected_rank_126 = (lagged - lagged.rolling(126).min()) / (
            lagged.rolling(126).max() - lagged.rolling(126).min() + 1e-10
        )
        row = enriched.iloc[-1]

        self.assertIn("options_iv_30_iv_rank_252", enriched.columns)
        self.assertIn("options_iv_30_iv_rank_126", enriched.columns)
        self.assertAlmostEqual(row["options_iv_30_iv_rank_252"], expected_rank_252.iloc[-1], places=6)
        self.assertAlmostEqual(row["options_iv_30_iv_rank_126"], expected_rank_126.iloc[-1], places=6)

    def test_add_features_loads_options_iv_history_when_requested(self) -> None:
        frame = make_price_frame()
        price_features = prepare.add_price_features(frame)
        context_features = prepare.add_context_features(price_features)
        options_iv_history = pd.DataFrame(
            {
                "date": frame["date"],
                "target_30d_atm_iv": np.linspace(0.2, 0.5, len(frame)),
            }
        )

        with mock.patch.object(
            prepare,
            "get_runtime_config",
            return_value={"horizon_days": 60, "upper_barrier": 0.08, "lower_barrier": -0.04, "label_mode": "keep-all-binary"},
        ):
            with mock.patch.object(prepare, "selected_vix_features_requested", return_value=False):
                with mock.patch.object(prepare, "selected_options_iv_features_requested", return_value=True):
                    with mock.patch.object(prepare, "add_relative_strength_features", return_value=price_features):
                        with mock.patch.object(prepare, "add_context_features", return_value=context_features):
                            with mock.patch.object(prepare, "load_options_iv_history", return_value=options_iv_history) as load_history:
                                enriched = prepare.add_features(frame)

        load_history.assert_called_once_with()
        self.assertIn("options_iv_30", enriched.columns)
        self.assertIn("options_iv_30_change_1", enriched.columns)
        self.assertIn("options_iv_30_iv_rank_252", enriched.columns)

    def test_load_options_iv_history_uses_configured_csv(self) -> None:
        path = os.path.join(self._testMethodName + "_options_iv.csv")
        try:
            pd.DataFrame({"date": ["2026-01-01"], "target_30d_atm_iv": [0.24]}).to_csv(path, index=False)
            loaded = prepare.load_options_iv_history(path)
        finally:
            if os.path.exists(path):
                os.remove(path)

        self.assertEqual(list(loaded["target_30d_atm_iv"]), [0.24])


if __name__ == "__main__":
    unittest.main()
