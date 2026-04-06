from __future__ import annotations

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


if __name__ == "__main__":
    unittest.main()
