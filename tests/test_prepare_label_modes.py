from __future__ import annotations

import unittest
import tempfile
from pathlib import Path
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

        self.assertAlmostEqual(float(upper_cutoff), 0.26, places=6)
        self.assertAlmostEqual(float(lower_cutoff), 0.14, places=6)

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
            with mock.patch.object(prepare, "download_prices_from_yahoo", return_value=frame):
                saved = prepare.download_symbol_prices("GLD", "unused", str(cache_path))

            self.assertTrue(cache_path.exists())
            self.assertEqual(len(saved), 3)


if __name__ == "__main__":
    unittest.main()
