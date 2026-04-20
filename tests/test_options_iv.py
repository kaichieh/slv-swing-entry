from __future__ import annotations

import json
import os
import unittest
from unittest import mock

import pandas as pd

import options_iv


class OptionsIvTests(unittest.TestCase):
    def test_load_option_chain_normalizes_aliases_and_prefers_mid_price(self) -> None:
        frame = pd.DataFrame(
            {
                "quote_date": ["2026-04-20", "2026-04-20"],
                "ticker": ["NVDA", "NVDA"],
                "underlying_price": [100.0, 100.0],
                "expiration_date": ["2026-05-20", "2026-05-20"],
                "strike_price": [100.0, 100.0],
                "right": ["C", "P"],
                "bid_price": [4.0, 4.2],
                "ask_price": [6.0, 6.2],
                "contract_volume": [100, 120],
                "oi": [500, 450],
            }
        )
        path = os.path.join(self._testMethodName + ".csv")
        try:
            frame.to_csv(path, index=False)
            normalized = options_iv.load_option_chain(pathlib_path(path))
        finally:
            if os.path.exists(path):
                os.remove(path)

        self.assertEqual(list(normalized["option_type"]), ["call", "put"])
        self.assertEqual(list(normalized["price"]), [5.0, 5.2])
        self.assertEqual(normalized.loc[0, "underlying"], "NVDA")

    def test_build_iv_summary_interpolates_target_30d_iv(self) -> None:
        asof = pd.Timestamp("2026-04-20")
        sigma_1 = 0.20
        sigma_2 = 0.30
        spot = 100.0
        strike = 100.0
        rows = []
        for days_to_expiry, sigma in ((20.0, sigma_1), (40.0, sigma_2)):
            year_fraction = days_to_expiry / 252.0
            for option_type in ("call", "put"):
                price = options_iv.black_scholes_price(
                    spot=spot,
                    strike=strike,
                    year_fraction=year_fraction,
                    rate=0.04,
                    sigma=sigma,
                    option_type=option_type,
                )
                rows.append(
                    {
                        "asof_date": asof,
                        "underlying": "NVDA",
                        "spot": spot,
                        "expiry": asof + pd.Timedelta(days=int(days_to_expiry)),
                        "strike": strike,
                        "option_type": option_type,
                        "price": price,
                        "bid": price - 0.05,
                        "ask": price + 0.05,
                        "last": price,
                        "mark": price,
                        "open_interest": 1000.0,
                        "volume": 100.0,
                        "rate": 0.04,
                        "trading_days_to_expiry": days_to_expiry,
                        "year_fraction": year_fraction,
                        "atm_distance": 0.0,
                        "liquidity_score": 200.0,
                    }
                )
        frame = pd.DataFrame(rows)

        summary = options_iv.build_iv_summary(frame)

        self.assertEqual(summary["interpolation"]["method"], "linear_by_trading_days")
        self.assertAlmostEqual(summary["target_30d_atm_iv"], 0.25, places=3)
        self.assertEqual(summary["usable_expiries"], 2)

    def test_run_writes_summary_json(self) -> None:
        asof = "2026-04-20"
        frame = pd.DataFrame(
            {
                "quote_date": [asof, asof],
                "ticker": ["SLV", "SLV"],
                "underlying_price": [25.0, 25.0],
                "expiration_date": ["2026-05-20", "2026-05-20"],
                "strike_price": [25.0, 25.0],
                "right": ["C", "P"],
                "bid_price": [1.1, 1.0],
                "ask_price": [1.3, 1.2],
                "contract_volume": [40, 45],
                "oi": [200, 210],
            }
        )
        input_path = os.path.join(self._testMethodName + "_chain.csv")
        output_path = os.path.join(self._testMethodName + "_summary.json")
        history_path = os.path.join(self._testMethodName + "_history.csv")
        try:
            frame.to_csv(input_path, index=False)
            with mock.patch.object(options_iv.ac, "get_options_iv_history_path", return_value=pathlib_path(history_path)):
                summary = options_iv.run(path=pathlib_path(input_path), output_path=pathlib_path(output_path))
            written = json.loads(pathlib_path(output_path).read_text(encoding="utf-8"))
            history = pd.read_csv(history_path)
        finally:
            if os.path.exists(input_path):
                os.remove(input_path)
            if os.path.exists(output_path):
                os.remove(output_path)
            if os.path.exists(history_path):
                os.remove(history_path)

        self.assertEqual(summary["underlying"], "SLV")
        self.assertIn("target_30d_atm_iv", written)
        self.assertEqual(len(history), 1)
        self.assertIn("target_30d_atm_iv", history.columns)


def pathlib_path(raw: str) -> "Path":
    from pathlib import Path

    return Path(raw)


if __name__ == "__main__":
    unittest.main()
