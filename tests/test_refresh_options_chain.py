from __future__ import annotations

import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import pandas as pd

import refresh_options_chain as roc


def make_head_payload() -> dict[str, object]:
    return {
        "optionChain": {
            "result": [
                {
                    "quote": {
                        "regularMarketTime": 1776643200,
                        "regularMarketPrice": 101.25,
                    },
                    "expirationDates": [
                        1778457600,
                        1780185600,
                        1782864000,
                    ],
                    "options": [],
                }
            ]
        }
    }


def make_expiry_payload(expiry_epoch: int) -> dict[str, object]:
    return {
        "optionChain": {
            "result": [
                {
                    "quote": {
                        "regularMarketTime": 1776643200,
                        "regularMarketPrice": 101.25,
                    },
                    "expirationDates": [expiry_epoch],
                    "options": [
                        {
                            "calls": [
                                {
                                    "contractSymbol": "NVDATESTC",
                                    "expiration": expiry_epoch,
                                    "strike": 100.0,
                                    "bid": 4.9,
                                    "ask": 5.1,
                                    "lastPrice": 5.0,
                                    "volume": 150,
                                    "openInterest": 1000,
                                    "impliedVolatility": 0.31,
                                    "currency": "USD",
                                }
                            ],
                            "puts": [
                                {
                                    "contractSymbol": "NVDATESTP",
                                    "expiration": expiry_epoch,
                                    "strike": 100.0,
                                    "bid": 4.6,
                                    "ask": 4.8,
                                    "lastPrice": 4.7,
                                    "volume": 175,
                                    "openInterest": 900,
                                    "impliedVolatility": 0.32,
                                    "currency": "USD",
                                }
                            ],
                        }
                    ],
                }
            ]
        }
    }


class RefreshOptionsChainTests(unittest.TestCase):
    def test_filter_expiry_epochs_keeps_near_term_window(self) -> None:
        asof_date = pd.Timestamp("2026-04-20")
        expiry_epochs = [
            int(pd.Timestamp("2026-04-24").timestamp()),
            int(pd.Timestamp("2026-05-20").timestamp()),
            int(pd.Timestamp("2026-06-18").timestamp()),
            int(pd.Timestamp("2026-08-20").timestamp()),
        ]

        selected = roc.filter_expiry_epochs(asof_date, expiry_epochs, max_expiries=3)

        self.assertEqual(len(selected), 2)

    def test_download_options_chain_builds_normalized_rows(self) -> None:
        calls = {"count": 0}

        def fake_fetch_text(url: str) -> str:
            if "?date=" not in url:
                return json.dumps(make_head_payload())
            calls["count"] += 1
            expiry_epoch = int(url.split("?date=")[1])
            return json.dumps(make_expiry_payload(expiry_epoch))

        with mock.patch.object(roc, "fetch_text", side_effect=fake_fetch_text):
            frame = roc.download_options_chain("NVDA", max_expiries=2)

        self.assertEqual(calls["count"], 2)
        self.assertEqual(list(frame["option_type"]), ["call", "put", "call", "put"])
        self.assertIn("provider_implied_vol", frame.columns)
        self.assertEqual(frame["underlying"].iloc[0], "NVDA")

    def test_save_options_chain_writes_csv(self) -> None:
        frame = pd.DataFrame(
            {
                "asof_date": ["2026-04-20"],
                "underlying": ["SLV"],
                "spot": [25.0],
                "expiry": ["2026-05-20"],
                "strike": [25.0],
                "option_type": ["call"],
                "bid": [1.1],
                "ask": [1.3],
                "last": [1.2],
            }
        )
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "slv_options_chain.csv"
            saved_path = roc.save_options_chain(frame, path)
            written = pd.read_csv(saved_path)

        self.assertEqual(len(written), 1)
        self.assertEqual(written.loc[0, "underlying"], "SLV")

    def test_run_uses_asset_symbol_and_default_cache_path(self) -> None:
        frame = pd.DataFrame(
            {
                "asof_date": ["2026-04-20"],
                "underlying": ["NVDA"],
                "spot": [101.25],
                "expiry": ["2026-05-20"],
                "strike": [100.0],
                "option_type": ["call"],
                "bid": [4.9],
                "ask": [5.1],
                "last": [5.0],
            }
        )
        with tempfile.TemporaryDirectory() as temp_dir:
            output_path = Path(temp_dir) / "nvda_options_chain.csv"
            with mock.patch.object(roc.ac, "get_asset_download_symbol", return_value="NVDA"):
                with mock.patch.object(roc, "download_options_chain", return_value=frame) as download_chain:
                    with mock.patch.object(roc.ac, "get_options_chain_path", return_value=output_path):
                        saved = roc.run()

        download_chain.assert_called_once_with("NVDA", max_expiries=roc.DEFAULT_MAX_EXPIRIES)
        self.assertEqual(len(saved), 1)


if __name__ == "__main__":
    unittest.main()
