from __future__ import annotations

import os
import unittest
from unittest import mock

import numpy as np
import pandas as pd

import prepare


def make_price_frame(symbol_scale: float = 1.0) -> pd.DataFrame:
    rows = 320
    index = np.arange(rows, dtype=np.float64)
    close = symbol_scale * (100.0 + 0.4 * index + 3.0 * np.sin(index / 7.0))
    open_price = close * (1.0 - 0.002 + 0.001 * np.cos(index / 9.0))
    high = close * (1.0 + 0.01 + 0.002 * np.sin(index / 11.0))
    low = close * (1.0 - 0.01 - 0.002 * np.cos(index / 13.0))
    volume = 1_000_000 + 1_500 * index + 20_000 * np.sin(index / 5.0)
    return pd.DataFrame(
        {
            "date": pd.date_range("2020-01-01", periods=rows, freq="D"),
            "open": open_price,
            "high": high,
            "low": low,
            "close": close,
            "volume": volume,
        }
    )


class PrepareNewFeaturesTests(unittest.TestCase):
    def make_vix_frame(self, rows: int = 320) -> pd.DataFrame:
        index = np.arange(rows, dtype=np.float64)
        close = 18.0 + 0.05 * index + 2.5 * np.sin(index / 6.0)
        return pd.DataFrame(
            {
                "date": pd.date_range("2020-01-01", periods=rows, freq="D"),
                "close": close,
            }
        )

    def test_download_vix_prices_normalizes_fred_vixcls_shape(self) -> None:
        payload = "DATE,VIXCLS\n2020-01-02,13.45\n2020-01-01,12.50\n2020-01-02,14.00\n"

        with mock.patch.object(prepare, "fetch_text", return_value=payload):
            normalized = prepare.download_vix_prices("https://fred.example/vix.csv")

        self.assertEqual(list(normalized.columns), ["date", "close"])
        self.assertEqual(list(normalized["date"]), list(pd.to_datetime(["2020-01-01", "2020-01-02"])))
        self.assertEqual(list(normalized["close"]), [12.5, 14.0])

    def test_normalize_vix_frame_accepts_fred_observation_date_column(self) -> None:
        frame = pd.DataFrame(
            {
                "observation_date": ["2020-01-02", "2020-01-01"],
                "VIXCLS": [13.45, 12.50],
            }
        )

        normalized = prepare.normalize_vix_frame(frame)

        self.assertEqual(list(normalized.columns), ["date", "close"])
        self.assertEqual(list(normalized["date"]), list(pd.to_datetime(["2020-01-01", "2020-01-02"])))
        self.assertEqual(list(normalized["close"]), [12.5, 13.45])

    def test_add_vix_features_aligns_backward_without_lookahead(self) -> None:
        asset = make_price_frame().iloc[:5].copy()
        vix = pd.DataFrame(
            {
                "date": pd.to_datetime(["2020-01-02", "2020-01-04"]),
                "close": [20.0, 40.0],
            }
        )

        enriched = prepare.add_vix_features(asset, vix)

        self.assertTrue(np.isnan(enriched.loc[0, "vix_close"]))
        self.assertEqual(enriched.loc[1, "vix_close"], 20.0)
        self.assertEqual(enriched.loc[2, "vix_close"], 20.0)
        self.assertEqual(enriched.loc[3, "vix_close"], 40.0)
        self.assertEqual(enriched.loc[4, "vix_close"], 40.0)

    def test_add_vix_features_builds_requested_columns_from_lagged_close(self) -> None:
        asset = make_price_frame()
        vix = self.make_vix_frame()

        enriched = prepare.add_vix_features(asset, vix)
        row = enriched.iloc[-1]
        lagged = enriched["vix_close"].shift(1)
        expected_z = (lagged - lagged.rolling(20).mean()) / (lagged.rolling(20).std() + 1e-10)
        expected_percentile = lagged.rolling(20).rank(pct=True)

        for column in [
            "vix_close_lag1",
            "vix_change_1",
            "vix_change_5",
            "vix_z_20",
            "vix_percentile_20",
            "vix_high_regime_flag",
        ]:
            self.assertIn(column, enriched.columns)

        self.assertAlmostEqual(row["vix_close_lag1"], lagged.iloc[-1], places=6)
        self.assertAlmostEqual(row["vix_change_1"], lagged.pct_change(1).iloc[-1], places=6)
        self.assertAlmostEqual(row["vix_change_5"], lagged.pct_change(5).iloc[-1], places=6)
        self.assertAlmostEqual(row["vix_z_20"], expected_z.iloc[-1], places=6)
        self.assertAlmostEqual(row["vix_percentile_20"], expected_percentile.iloc[-1], places=6)
        self.assertEqual(row["vix_high_regime_flag"], float(expected_percentile.iloc[-1] >= 0.8))

    def test_add_relative_strength_features_builds_requested_columns(self) -> None:
        asset = prepare.add_price_features(make_price_frame())
        benchmark_prices = make_price_frame(symbol_scale=0.9)
        benchmark_features = prepare.add_price_features(benchmark_prices)

        with mock.patch.object(prepare, "download_benchmark_prices", return_value=benchmark_prices):
            enriched = prepare.add_relative_strength_features(asset, "SPY")

        row = enriched.iloc[-1]
        benchmark_row = benchmark_features.iloc[-1]

        self.assertIn("ret_20_vs_benchmark", enriched.columns)
        self.assertIn("ret_60_vs_benchmark", enriched.columns)
        self.assertIn("price_ratio_benchmark_z_20", enriched.columns)
        self.assertAlmostEqual(row["ret_20_vs_benchmark"], row["ret_20"] - benchmark_row["ret_20"], places=6)
        self.assertAlmostEqual(row["ret_60_vs_benchmark"], row["ret_60"] - benchmark_row["ret_60"], places=6)
        self.assertTrue(np.isfinite(row["price_ratio_benchmark_z_20"]))

    def test_add_context_features_builds_trend_compression_and_recovery_columns(self) -> None:
        asset = prepare.add_price_features(make_price_frame())

        enriched = prepare.add_context_features(asset)
        row = enriched.iloc[-1]

        self.assertIn("trend_quality_20", enriched.columns)
        self.assertIn("percent_up_days_20", enriched.columns)
        self.assertIn("bollinger_bandwidth_20", enriched.columns)
        self.assertIn("vol_ratio_20_120", enriched.columns)
        self.assertIn("distance_from_60d_low", enriched.columns)
        self.assertAlmostEqual(row["trend_quality_20"], row["slope_20"] / (row["volatility_20"] + 1e-6), places=6)
        self.assertGreaterEqual(row["percent_up_days_20"], 0.0)
        self.assertLessEqual(row["percent_up_days_20"], 1.0)
        self.assertGreater(row["bollinger_bandwidth_20"], 0.0)
        self.assertGreaterEqual(row["distance_from_60d_low"], 0.0)

    def test_add_features_only_requires_selected_experimental_columns(self) -> None:
        raw = make_price_frame()
        vix = self.make_vix_frame()

        with mock.patch.object(prepare, "BENCHMARK_SYMBOL", ""):
            with mock.patch.object(prepare, "download_vix_prices", return_value=vix):
                with mock.patch.dict(os.environ, {"AR_EXTRA_BASE_FEATURES": ""}, clear=False):
                    baseline = prepare.add_features(raw)
                with mock.patch.dict(os.environ, {"AR_EXTRA_BASE_FEATURES": "atr_pct_20_percentile"}, clear=False):
                    with_selected_experimental = prepare.add_features(raw)

        self.assertGreater(len(baseline), len(with_selected_experimental))
        self.assertIn("atr_pct_20_percentile", baseline.columns)
        self.assertIn("atr_pct_20_percentile", with_selected_experimental.columns)


if __name__ == "__main__":
    unittest.main()
