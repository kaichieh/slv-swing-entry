from __future__ import annotations

import unittest
import tempfile
from http.client import RemoteDisconnected
from pathlib import Path
from typing import cast
from unittest import mock

import numpy as np
import pandas as pd

import prepare


class PrepareLabelModeTests(unittest.TestCase):
    def test_select_label_mode_cutoffs_uses_train_window_only(self) -> None:
        realized_returns = np.array([0.10, 0.20, 0.30, 10.0, 11.0, -9.0], dtype=np.float64)

        upper_cutoff, lower_cutoff = prepare.select_label_mode_cutoffs(
            realized_returns,
            "future-return-top-bottom-20pct",
            train_end=3,
        )

        self.assertIsNotNone(upper_cutoff)
        self.assertIsNotNone(lower_cutoff)
        self.assertAlmostEqual(float(cast(float, upper_cutoff)), 0.26, places=6)
        self.assertAlmostEqual(float(cast(float, lower_cutoff)), 0.14, places=6)

    def test_download_symbol_prices_creates_parent_for_explicit_cache_path(self) -> None:
        frame = pd.DataFrame(
            {
                "date": pd.date_range("2020-01-01", periods=3, freq="D"),
                "open": [1.0, 2.0, 3.0],
                "high": [1.1, 2.1, 3.1],
                "low": [0.9, 1.9, 2.9],
                "close": [1.0, 2.0, 3.0],
                "volume": [100.0, 200.0, 300.0],
            }
        )
        with tempfile.TemporaryDirectory() as temp_dir:
            cache_path = Path(temp_dir) / "nested" / "gld.csv"
            with mock.patch.object(prepare, "download_prices_from_yfinance", return_value=frame):
                saved = prepare.download_symbol_prices("GLD", "unused", str(cache_path))

            self.assertTrue(cache_path.exists())
            self.assertEqual(len(saved), 3)

    def test_download_symbol_prices_falls_back_to_direct_yahoo_when_yfinance_fails(self) -> None:
        frame = pd.DataFrame(
            {
                "date": pd.date_range("2020-01-01", periods=3, freq="D"),
                "open": [1.0, 2.0, 3.0],
                "high": [1.1, 2.1, 3.1],
                "low": [0.9, 1.9, 2.9],
                "close": [1.0, 2.0, 3.0],
                "volume": [100.0, 200.0, 300.0],
            }
        )
        with tempfile.TemporaryDirectory() as temp_dir:
            cache_path = Path(temp_dir) / "fallback.csv"
            with mock.patch.object(prepare, "download_prices_from_yfinance", side_effect=TimeoutError):
                with mock.patch.object(prepare, "download_prices_from_yahoo", return_value=frame) as direct_yahoo:
                    saved = prepare.download_symbol_prices("GLD", "unused", str(cache_path))

        direct_yahoo.assert_called_once_with("GLD")
        self.assertEqual(len(saved), 3)

    def test_download_symbol_prices_uses_cached_csv_when_stooq_parse_fails(self) -> None:
        cached = pd.DataFrame(
            {
                "date": pd.date_range("2020-01-01", periods=3, freq="D"),
                "open": [1.0, 2.0, 3.0],
                "high": [1.1, 2.1, 3.1],
                "low": [0.9, 1.9, 2.9],
                "close": [1.0, 2.0, 3.0],
                "volume": [100.0, 200.0, 300.0],
            }
        )
        with tempfile.TemporaryDirectory() as temp_dir:
            cache_path = Path(temp_dir) / "cached.csv"
            cached.to_csv(cache_path, index=False)

            with mock.patch.object(prepare, "download_prices_from_yfinance", side_effect=TimeoutError):
                with mock.patch.object(prepare, "download_prices_from_yahoo", side_effect=TimeoutError):
                    with mock.patch.object(prepare, "download_prices_from_stooq", side_effect=pd.errors.ParserError("bad csv")):
                        saved = prepare.download_symbol_prices("GLD", "unused", str(cache_path))

        self.assertEqual(len(saved), 3)
        self.assertEqual(list(saved["close"]), [1.0, 2.0, 3.0])

    def test_download_symbol_prices_uses_cached_csv_when_stooq_normalization_fails(self) -> None:
        cached = pd.DataFrame(
            {
                "date": pd.date_range("2020-01-01", periods=3, freq="D"),
                "open": [7.0, 8.0, 9.0],
                "high": [7.1, 8.1, 9.1],
                "low": [6.9, 7.9, 8.9],
                "close": [7.0, 8.0, 9.0],
                "volume": [700.0, 800.0, 900.0],
            }
        )
        with tempfile.TemporaryDirectory() as temp_dir:
            cache_path = Path(temp_dir) / "cached.csv"
            cached.to_csv(cache_path, index=False)

            with mock.patch.object(prepare, "download_prices_from_yfinance", side_effect=TimeoutError):
                with mock.patch.object(prepare, "download_prices_from_yahoo", side_effect=TimeoutError):
                    with mock.patch.object(
                        prepare,
                        "download_prices_from_stooq",
                        side_effect=RuntimeError("Downloaded dataset missing columns: ['open']"),
                    ):
                        saved = prepare.download_symbol_prices("GLD", "unused", str(cache_path))

        self.assertEqual(len(saved), 3)
        self.assertEqual(list(saved["close"]), [7.0, 8.0, 9.0])

    def test_download_symbol_prices_uses_cached_csv_when_yahoo_disconnects(self) -> None:
        cached = pd.DataFrame(
            {
                "date": pd.date_range("2020-01-01", periods=3, freq="D"),
                "open": [4.0, 5.0, 6.0],
                "high": [4.1, 5.1, 6.1],
                "low": [3.9, 4.9, 5.9],
                "close": [4.0, 5.0, 6.0],
                "volume": [400.0, 500.0, 600.0],
            }
        )
        with tempfile.TemporaryDirectory() as temp_dir:
            cache_path = Path(temp_dir) / "cached.csv"
            cached.to_csv(cache_path, index=False)

            with mock.patch.object(prepare, "download_prices_from_yfinance", side_effect=RemoteDisconnected("closed")):
                with mock.patch.object(prepare, "download_prices_from_yahoo", side_effect=RemoteDisconnected("closed")):
                    with mock.patch.object(prepare, "download_prices_from_stooq", side_effect=TimeoutError):
                        saved = prepare.download_symbol_prices("GLD", "unused", str(cache_path))

        self.assertEqual(len(saved), 3)
        self.assertEqual(list(saved["close"]), [4.0, 5.0, 6.0])


if __name__ == "__main__":
    unittest.main()
