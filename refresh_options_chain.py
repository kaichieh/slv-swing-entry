from __future__ import annotations

import json
import os
import time
from http.client import RemoteDisconnected
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

import pandas as pd
import yfinance as yf

import asset_config as ac

FETCH_TEXT_TIMEOUT_SECONDS = 60
FETCH_TEXT_MAX_ATTEMPTS = 3
FETCH_TEXT_RETRY_BASE_SECONDS = 1.5
DEFAULT_MAX_EXPIRIES = 6
MIN_DAYS_TO_EXPIRY = 7
MAX_DAYS_TO_EXPIRY = 60


def get_env_int(name: str, default: int) -> int:
    value = os.getenv(name)
    return int(value) if value is not None else default


def fetch_text(url: str) -> str:
    headers = {
        "User-Agent": "Mozilla/5.0",
        "Accept": "application/json",
    }
    last_error: Exception | None = None
    for attempt in range(1, FETCH_TEXT_MAX_ATTEMPTS + 1):
        request = Request(url, headers=headers)
        try:
            with urlopen(request, timeout=FETCH_TEXT_TIMEOUT_SECONDS) as response:
                charset = response.headers.get_content_charset() or "utf-8"
                return response.read().decode(charset)
        except Exception as exc:
            last_error = exc
            if attempt >= FETCH_TEXT_MAX_ATTEMPTS or not should_retry_fetch(exc):
                raise
            time.sleep(FETCH_TEXT_RETRY_BASE_SECONDS * attempt)
    if last_error is not None:
        raise last_error
    raise RuntimeError(f"Unable to fetch URL: {url}")


def should_retry_fetch(exc: Exception) -> bool:
    return isinstance(exc, (HTTPError, URLError, TimeoutError, ConnectionResetError, RemoteDisconnected, ValueError))


def yahoo_options_url(symbol: str, expiry_epoch: int | None = None) -> str:
    base = f"https://query1.finance.yahoo.com/v7/finance/options/{symbol}"
    if expiry_epoch is None:
        return base
    return f"{base}?date={expiry_epoch}"


def load_options_payload(symbol: str, expiry_epoch: int | None = None) -> dict[str, Any]:
    payload = json.loads(fetch_text(yahoo_options_url(symbol, expiry_epoch)))
    result = payload["optionChain"]["result"]
    if not result:
        raise RuntimeError(f"Yahoo options response returned no results for {symbol}.")
    return result[0]


def extract_quote_context(payload: dict[str, Any]) -> tuple[pd.Timestamp, float, list[int]]:
    quote = payload["quote"]
    regular_market_time = quote.get("regularMarketTime")
    if regular_market_time is None:
        raise RuntimeError("Yahoo options quote payload missing regularMarketTime.")
    asof_date = pd.to_datetime(int(regular_market_time), unit="s", utc=True).tz_localize(None).normalize()

    spot_candidates = (
        quote.get("regularMarketPrice"),
        quote.get("postMarketPrice"),
        quote.get("bid"),
        quote.get("ask"),
    )
    spot = next((float(candidate) for candidate in spot_candidates if candidate is not None), None)
    if spot is None or spot <= 0.0:
        raise RuntimeError("Yahoo options quote payload missing a usable underlying spot price.")

    expiries = payload.get("expirationDates") or []
    if not expiries:
        raise RuntimeError("Yahoo options payload missing expirationDates.")
    return asof_date, spot, [int(expiry) for expiry in expiries]


def normalize_option_rows(
    contract_rows: list[dict[str, Any]],
    *,
    asof_date: pd.Timestamp,
    symbol: str,
    fallback_spot: float,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for contract in contract_rows:
        expiry_epoch = contract.get("expiration")
        strike = contract.get("strike")
        if expiry_epoch is None or strike is None:
            continue
        contract_type = str(contract.get("contractSymbol", ""))
        option_type = "call" if contract_type.endswith("C") else "put"
        bid = contract.get("bid")
        ask = contract.get("ask")
        last = contract.get("lastPrice")
        implied_vol = contract.get("impliedVolatility")
        volume = contract.get("volume")
        open_interest = contract.get("openInterest")
        row = {
            "asof_date": asof_date.date().isoformat(),
            "underlying": symbol,
            "spot": float(contract.get("lastPriceUnderlying", fallback_spot) or fallback_spot),
            "expiry": pd.to_datetime(int(expiry_epoch), unit="s", utc=True).tz_localize(None).normalize().date().isoformat(),
            "strike": float(strike),
            "option_type": option_type,
            "bid": float(bid) if bid is not None else None,
            "ask": float(ask) if ask is not None else None,
            "last": float(last) if last is not None else None,
            "mark": None,
            "open_interest": float(open_interest) if open_interest is not None else None,
            "volume": float(volume) if volume is not None else None,
            "provider_implied_vol": float(implied_vol) if implied_vol is not None else None,
            "contract_symbol": contract.get("contractSymbol"),
            "currency": contract.get("currency"),
        }
        rows.append(row)
    return rows


def filter_expiry_epochs(asof_date: pd.Timestamp, expiry_epochs: list[int], max_expiries: int) -> list[int]:
    selected: list[tuple[int, int]] = []
    for expiry_epoch in expiry_epochs:
        expiry_date = pd.to_datetime(int(expiry_epoch), unit="s", utc=True).tz_localize(None).normalize()
        days = int((expiry_date - asof_date).days)
        if MIN_DAYS_TO_EXPIRY <= days <= MAX_DAYS_TO_EXPIRY:
            selected.append((days, int(expiry_epoch)))
    selected.sort()
    return [epoch for _, epoch in selected[:max_expiries]]


def download_options_chain(symbol: str, max_expiries: int = DEFAULT_MAX_EXPIRIES) -> pd.DataFrame:
    try:
        head_payload = load_options_payload(symbol)
        asof_date, spot, expiry_epochs = extract_quote_context(head_payload)
        selected_expiries = filter_expiry_epochs(asof_date, expiry_epochs, max_expiries)
        if not selected_expiries:
            raise RuntimeError(
                f"No expiries within {MIN_DAYS_TO_EXPIRY}-{MAX_DAYS_TO_EXPIRY} days were found for {symbol}."
            )

        rows: list[dict[str, Any]] = []
        for expiry_epoch in selected_expiries:
            payload = load_options_payload(symbol, expiry_epoch)
            option_sets = payload.get("options") or []
            if not option_sets:
                continue
            option_set = option_sets[0]
            rows.extend(
                normalize_option_rows(option_set.get("calls") or [], asof_date=asof_date, symbol=symbol, fallback_spot=spot)
            )
            rows.extend(
                normalize_option_rows(option_set.get("puts") or [], asof_date=asof_date, symbol=symbol, fallback_spot=spot)
            )
        frame = pd.DataFrame(rows)
        if frame.empty:
            raise RuntimeError(f"Yahoo options importer produced no contracts for {symbol}.")
        return frame.sort_values(["expiry", "option_type", "strike"]).reset_index(drop=True)
    except Exception:
        return download_options_chain_with_yfinance(symbol, max_expiries=max_expiries)


def download_options_chain_with_yfinance(symbol: str, max_expiries: int = DEFAULT_MAX_EXPIRIES) -> pd.DataFrame:
    ticker = yf.Ticker(symbol)
    expiries = list(ticker.options)
    if not expiries:
        raise RuntimeError(f"yfinance returned no option expiries for {symbol}.")

    history = ticker.history(period="5d", interval="1d", auto_adjust=False)
    if history.empty or "Close" not in history.columns:
        raise RuntimeError(f"yfinance returned no spot history for {symbol}.")
    asof_date = pd.to_datetime(history.index[-1]).tz_localize(None).normalize()
    spot = float(history["Close"].iloc[-1])

    selected_expiries: list[str] = []
    for expiry_text in expiries:
        expiry_date = pd.to_datetime(expiry_text).normalize()
        days = int((expiry_date - asof_date).days)
        if MIN_DAYS_TO_EXPIRY <= days <= MAX_DAYS_TO_EXPIRY:
            selected_expiries.append(expiry_text)
    selected_expiries = selected_expiries[:max_expiries]
    if not selected_expiries:
        raise RuntimeError(
            f"yfinance found no expiries within {MIN_DAYS_TO_EXPIRY}-{MAX_DAYS_TO_EXPIRY} days for {symbol}."
        )

    rows: list[dict[str, Any]] = []
    for expiry_text in selected_expiries:
        chain = ticker.option_chain(expiry_text)
        expiry_date = pd.to_datetime(expiry_text).normalize().date().isoformat()
        for option_type, frame in (("call", chain.calls), ("put", chain.puts)):
            for _, contract in frame.iterrows():
                rows.append(
                    {
                        "asof_date": asof_date.date().isoformat(),
                        "underlying": symbol,
                        "spot": spot,
                        "expiry": expiry_date,
                        "strike": float(contract["strike"]),
                        "option_type": option_type,
                        "bid": float(contract["bid"]) if pd.notna(contract["bid"]) else None,
                        "ask": float(contract["ask"]) if pd.notna(contract["ask"]) else None,
                        "last": float(contract["lastPrice"]) if pd.notna(contract["lastPrice"]) else None,
                        "mark": None,
                        "open_interest": float(contract["openInterest"]) if pd.notna(contract["openInterest"]) else None,
                        "volume": float(contract["volume"]) if pd.notna(contract["volume"]) else None,
                        "provider_implied_vol": float(contract["impliedVolatility"]) if pd.notna(contract["impliedVolatility"]) else None,
                        "contract_symbol": contract.get("contractSymbol"),
                        "currency": "USD",
                    }
                )
    frame = pd.DataFrame(rows)
    if frame.empty:
        raise RuntimeError(f"yfinance options importer produced no contracts for {symbol}.")
    return frame.sort_values(["expiry", "option_type", "strike"]).reset_index(drop=True)


def save_options_chain(frame: pd.DataFrame, path: Path | None = None) -> Path:
    output_path = path or ac.get_options_chain_path()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(output_path, index=False)
    return output_path


def run() -> pd.DataFrame:
    symbol = ac.get_asset_download_symbol()
    max_expiries = get_env_int("AR_OPTIONS_MAX_EXPIRIES", DEFAULT_MAX_EXPIRIES)
    frame = download_options_chain(symbol, max_expiries=max_expiries)
    save_options_chain(frame)
    return frame


def main() -> None:
    frame = run()
    output = {
        "asset_key": ac.get_asset_key(),
        "symbol": ac.get_asset_download_symbol(),
        "rows": len(frame),
        "expiries": sorted(frame["expiry"].drop_duplicates().tolist()),
        "output_path": str(ac.get_options_chain_path()),
    }
    print(json.dumps(output, indent=2))


if __name__ == "__main__":
    main()
