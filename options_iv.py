from __future__ import annotations

import json
import math
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

import asset_config as ac

MIN_TRADING_DAYS = 7
TARGET_TRADING_DAYS = 30
MAX_TRADING_DAYS = 60
DEFAULT_RATE = 0.04
MIN_SIGMA = 1e-4
MAX_SIGMA = 5.0
MAX_BISECTION_STEPS = 120
PRICE_TOLERANCE = 1e-8

CALL_ALIASES = {"c", "call", "calls"}
PUT_ALIASES = {"p", "put", "puts"}

COLUMN_ALIASES: dict[str, tuple[str, ...]] = {
    "asof_date": ("asof_date", "quote_date", "date", "timestamp"),
    "underlying": ("underlying", "symbol", "ticker", "root"),
    "spot": ("spot", "underlying_price", "underlier_price", "stock_price", "close"),
    "expiry": ("expiry", "expiration", "expiration_date", "expiry_date", "maturity"),
    "strike": ("strike", "strike_price", "exercise_price"),
    "option_type": ("option_type", "call_put", "cp", "right", "type", "side"),
    "bid": ("bid", "bid_price"),
    "ask": ("ask", "ask_price"),
    "last": ("last", "last_price", "trade_price", "premium"),
    "mark": ("mark", "mid", "mid_price", "mark_price"),
    "open_interest": ("open_interest", "oi"),
    "volume": ("volume", "contract_volume"),
    "rate": ("rate", "risk_free_rate", "rf_rate"),
}


@dataclass(frozen=True)
class OptionQuote:
    asof_date: str
    underlying: str
    expiry: str
    option_type: str
    strike: float
    spot: float
    price: float
    trading_days_to_expiry: float
    year_fraction: float
    rate: float
    bid: float | None = None
    ask: float | None = None
    last: float | None = None
    mark: float | None = None
    open_interest: float | None = None
    volume: float | None = None


@dataclass(frozen=True)
class IvPoint:
    expiry: str
    trading_days_to_expiry: float
    strike: float
    spot: float
    option_type: str
    price: float
    implied_vol: float
    moneyness_gap: float


def normalize_option_type(raw_value: object) -> str:
    value = str(raw_value).strip().lower()
    if value in CALL_ALIASES:
        return "call"
    if value in PUT_ALIASES:
        return "put"
    raise ValueError(f"Unsupported option type '{raw_value}'")


def pick_column(frame: pd.DataFrame, canonical_name: str) -> str | None:
    for candidate in COLUMN_ALIASES[canonical_name]:
        if candidate in frame.columns:
            return candidate
    return None


def infer_separator(path: Path) -> str:
    return "\t" if path.suffix.lower() == ".tsv" else ","


def normal_cdf(value: float) -> float:
    return 0.5 * (1.0 + math.erf(value / math.sqrt(2.0)))


def black_scholes_price(
    spot: float,
    strike: float,
    year_fraction: float,
    rate: float,
    sigma: float,
    option_type: str,
) -> float:
    if spot <= 0.0 or strike <= 0.0 or year_fraction <= 0.0 or sigma <= 0.0:
        raise ValueError("Black-Scholes inputs must be positive.")
    sqrt_t = math.sqrt(year_fraction)
    sigma_sqrt_t = sigma * sqrt_t
    d1 = (math.log(spot / strike) + (rate + 0.5 * sigma * sigma) * year_fraction) / sigma_sqrt_t
    d2 = d1 - sigma_sqrt_t
    discounted_strike = strike * math.exp(-rate * year_fraction)
    if option_type == "call":
        return spot * normal_cdf(d1) - discounted_strike * normal_cdf(d2)
    if option_type == "put":
        return discounted_strike * normal_cdf(-d2) - spot * normal_cdf(-d1)
    raise ValueError(f"Unsupported option type '{option_type}'")


def intrinsic_value(spot: float, strike: float, option_type: str) -> float:
    if option_type == "call":
        return max(spot - strike, 0.0)
    if option_type == "put":
        return max(strike - spot, 0.0)
    raise ValueError(f"Unsupported option type '{option_type}'")


def implied_volatility(
    spot: float,
    strike: float,
    year_fraction: float,
    rate: float,
    option_price: float,
    option_type: str,
) -> float | None:
    if (
        spot <= 0.0
        or strike <= 0.0
        or year_fraction <= 0.0
        or option_price <= 0.0
    ):
        return None

    lower_bound = intrinsic_value(spot, strike, option_type)
    if option_price < lower_bound - 1e-8:
        return None

    low_sigma = MIN_SIGMA
    high_sigma = MAX_SIGMA
    low_price = black_scholes_price(spot, strike, year_fraction, rate, low_sigma, option_type)
    high_price = black_scholes_price(spot, strike, year_fraction, rate, high_sigma, option_type)
    if option_price < low_price - PRICE_TOLERANCE or option_price > high_price + PRICE_TOLERANCE:
        return None

    for _ in range(MAX_BISECTION_STEPS):
        mid_sigma = 0.5 * (low_sigma + high_sigma)
        mid_price = black_scholes_price(spot, strike, year_fraction, rate, mid_sigma, option_type)
        if abs(mid_price - option_price) <= PRICE_TOLERANCE:
            return mid_sigma
        if mid_price < option_price:
            low_sigma = mid_sigma
        else:
            high_sigma = mid_sigma
    return 0.5 * (low_sigma + high_sigma)


def choose_price_column(frame: pd.DataFrame) -> pd.Series:
    bid_column = pick_column(frame, "bid")
    ask_column = pick_column(frame, "ask")
    mark_column = pick_column(frame, "mark")
    last_column = pick_column(frame, "last")

    bid = pd.to_numeric(frame[bid_column], errors="coerce") if bid_column else pd.Series(np.nan, index=frame.index)
    ask = pd.to_numeric(frame[ask_column], errors="coerce") if ask_column else pd.Series(np.nan, index=frame.index)
    mark = pd.to_numeric(frame[mark_column], errors="coerce") if mark_column else pd.Series(np.nan, index=frame.index)
    last = pd.to_numeric(frame[last_column], errors="coerce") if last_column else pd.Series(np.nan, index=frame.index)

    price = (bid + ask) / 2.0
    price = price.where(~(bid.isna() | ask.isna()), mark)
    price = price.where(~price.isna(), last)
    return price


def load_option_chain(path: Path) -> pd.DataFrame:
    frame = pd.read_csv(path, sep=infer_separator(path))
    if frame.empty:
        raise RuntimeError(f"Option chain file is empty: {path}")

    normalized = frame.copy()
    normalized.columns = [str(column).strip().lower() for column in normalized.columns]

    required = ("asof_date", "underlying", "spot", "expiry", "strike", "option_type")
    selected_columns: dict[str, str] = {}
    for canonical_name in required:
        actual_name = pick_column(normalized, canonical_name)
        if actual_name is None:
            aliases = ", ".join(COLUMN_ALIASES[canonical_name])
            raise RuntimeError(f"Missing required options column '{canonical_name}'. Accepted aliases: {aliases}")
        selected_columns[canonical_name] = actual_name

    data = pd.DataFrame(
        {
            "asof_date": pd.to_datetime(normalized[selected_columns["asof_date"]]).dt.normalize(),
            "underlying": normalized[selected_columns["underlying"]].astype(str).str.upper().str.strip(),
            "spot": pd.to_numeric(normalized[selected_columns["spot"]], errors="coerce"),
            "expiry": pd.to_datetime(normalized[selected_columns["expiry"]]).dt.normalize(),
            "strike": pd.to_numeric(normalized[selected_columns["strike"]], errors="coerce"),
            "option_type": normalized[selected_columns["option_type"]].map(normalize_option_type),
            "price": choose_price_column(normalized),
        }
    )

    for canonical_name in ("bid", "ask", "last", "mark", "open_interest", "volume", "rate"):
        actual_name = pick_column(normalized, canonical_name)
        data[canonical_name] = pd.to_numeric(normalized[actual_name], errors="coerce") if actual_name else np.nan

    data = data.dropna(subset=["asof_date", "underlying", "spot", "expiry", "strike", "option_type", "price"]).copy()
    if data.empty:
        raise RuntimeError("Option chain became empty after normalization.")

    data["trading_days_to_expiry"] = (data["expiry"] - data["asof_date"]).dt.days.astype(float)
    data["year_fraction"] = data["trading_days_to_expiry"] / 252.0
    data["rate"] = data["rate"].fillna(DEFAULT_RATE)
    data = data[
        (data["spot"] > 0.0)
        & (data["strike"] > 0.0)
        & (data["price"] > 0.0)
        & (data["trading_days_to_expiry"] >= MIN_TRADING_DAYS)
        & (data["trading_days_to_expiry"] <= MAX_TRADING_DAYS)
    ].copy()
    data["atm_distance"] = (data["strike"] - data["spot"]).abs()
    data["liquidity_score"] = (
        data["open_interest"].fillna(0.0) * 0.1
        + data["volume"].fillna(0.0)
        - data["atm_distance"] * 0.01
    )
    if data.empty:
        raise RuntimeError("No usable option quotes remained after filtering by price and expiry window.")
    return data.sort_values(["expiry", "option_type", "atm_distance", "liquidity_score"], ascending=[True, True, True, False]).reset_index(drop=True)


def to_option_quotes(frame: pd.DataFrame) -> list[OptionQuote]:
    quotes: list[OptionQuote] = []
    for row in frame.to_dict("records"):
        quote = OptionQuote(
            asof_date=pd.Timestamp(row["asof_date"]).date().isoformat(),
            underlying=str(row["underlying"]),
            expiry=pd.Timestamp(row["expiry"]).date().isoformat(),
            option_type=str(row["option_type"]),
            strike=float(row["strike"]),
            spot=float(row["spot"]),
            price=float(row["price"]),
            trading_days_to_expiry=float(row["trading_days_to_expiry"]),
            year_fraction=float(row["year_fraction"]),
            rate=float(row["rate"]),
            bid=float(row["bid"]) if pd.notna(row["bid"]) else None,
            ask=float(row["ask"]) if pd.notna(row["ask"]) else None,
            last=float(row["last"]) if pd.notna(row["last"]) else None,
            mark=float(row["mark"]) if pd.notna(row["mark"]) else None,
            open_interest=float(row["open_interest"]) if pd.notna(row["open_interest"]) else None,
            volume=float(row["volume"]) if pd.notna(row["volume"]) else None,
        )
        quotes.append(quote)
    return quotes


def compute_iv_point(quote: OptionQuote) -> IvPoint | None:
    sigma = implied_volatility(
        spot=quote.spot,
        strike=quote.strike,
        year_fraction=quote.year_fraction,
        rate=quote.rate,
        option_price=quote.price,
        option_type=quote.option_type,
    )
    if sigma is None:
        return None
    return IvPoint(
        expiry=quote.expiry,
        trading_days_to_expiry=quote.trading_days_to_expiry,
        strike=quote.strike,
        spot=quote.spot,
        option_type=quote.option_type,
        price=quote.price,
        implied_vol=sigma,
        moneyness_gap=abs(quote.strike - quote.spot) / quote.spot,
    )


def pick_atm_iv_points(quotes: list[OptionQuote]) -> dict[float, dict[str, IvPoint]]:
    grouped: dict[float, dict[str, IvPoint]] = {}
    for quote in quotes:
        point = compute_iv_point(quote)
        if point is None:
            continue
        expiry_bucket = grouped.setdefault(point.trading_days_to_expiry, {})
        existing = expiry_bucket.get(point.option_type)
        if existing is None or point.moneyness_gap < existing.moneyness_gap:
            expiry_bucket[point.option_type] = point
    return grouped


def summarize_expiry_bucket(points: dict[str, IvPoint]) -> dict[str, Any] | None:
    call = points.get("call")
    put = points.get("put")
    if call is None and put is None:
        return None
    avg_iv = float(np.mean([point.implied_vol for point in (call, put) if point is not None]))
    trading_days = call.trading_days_to_expiry if call is not None else put.trading_days_to_expiry
    return {
        "trading_days_to_expiry": trading_days,
        "call": asdict(call) if call is not None else None,
        "put": asdict(put) if put is not None else None,
        "avg_iv": avg_iv,
    }


def interpolate_30d_iv(expiry_summaries: list[dict[str, Any]]) -> dict[str, Any]:
    ordered = sorted(expiry_summaries, key=lambda item: abs(float(item["trading_days_to_expiry"]) - TARGET_TRADING_DAYS))
    if not ordered:
        raise RuntimeError("Could not build any expiry summaries with usable ATM IV quotes.")

    closest = ordered[0]
    exact_days = float(closest["trading_days_to_expiry"])
    if len(ordered) == 1 or abs(exact_days - TARGET_TRADING_DAYS) < 1e-8:
        return {
            "target_trading_days": TARGET_TRADING_DAYS,
            "method": "nearest_expiry",
            "interpolated_iv": float(closest["avg_iv"]),
            "near_expiry": closest,
            "far_expiry": None,
        }

    lower_candidates = [item for item in ordered if float(item["trading_days_to_expiry"]) <= TARGET_TRADING_DAYS]
    upper_candidates = [item for item in ordered if float(item["trading_days_to_expiry"]) >= TARGET_TRADING_DAYS]
    if not lower_candidates or not upper_candidates:
        return {
            "target_trading_days": TARGET_TRADING_DAYS,
            "method": "nearest_expiry",
            "interpolated_iv": float(closest["avg_iv"]),
            "near_expiry": closest,
            "far_expiry": None,
        }

    lower = max(lower_candidates, key=lambda item: float(item["trading_days_to_expiry"]))
    upper = min(upper_candidates, key=lambda item: float(item["trading_days_to_expiry"]))
    lower_days = float(lower["trading_days_to_expiry"])
    upper_days = float(upper["trading_days_to_expiry"])
    if abs(upper_days - lower_days) < 1e-8:
        interpolated_iv = float(lower["avg_iv"])
    else:
        weight = (TARGET_TRADING_DAYS - lower_days) / (upper_days - lower_days)
        interpolated_iv = float(lower["avg_iv"] + weight * (upper["avg_iv"] - lower["avg_iv"]))
    return {
        "target_trading_days": TARGET_TRADING_DAYS,
        "method": "linear_by_trading_days",
        "interpolated_iv": interpolated_iv,
        "near_expiry": lower,
        "far_expiry": upper,
    }


def build_iv_summary(frame: pd.DataFrame) -> dict[str, Any]:
    quotes = to_option_quotes(frame)
    buckets = pick_atm_iv_points(quotes)
    expiry_summaries = []
    for points in buckets.values():
        summary = summarize_expiry_bucket(points)
        if summary is not None:
            expiry_summaries.append(summary)
    interpolation = interpolate_30d_iv(expiry_summaries)
    asof_date = pd.Timestamp(frame["asof_date"].iloc[0]).date().isoformat()
    underlying = str(frame["underlying"].iloc[0])
    spot = float(frame["spot"].iloc[0])
    return {
        "asof_date": asof_date,
        "underlying": underlying,
        "spot": spot,
        "input_rows": int(len(frame)),
        "usable_expiries": len(expiry_summaries),
        "target_30d_atm_iv": interpolation["interpolated_iv"],
        "interpolation": interpolation,
        "expiry_summaries": sorted(expiry_summaries, key=lambda item: float(item["trading_days_to_expiry"])),
    }


def build_history_row(summary: dict[str, Any]) -> dict[str, Any]:
    interpolation = summary["interpolation"]
    near_expiry = interpolation["near_expiry"]
    far_expiry = interpolation["far_expiry"]
    return {
        "date": summary["asof_date"],
        "underlying": summary["underlying"],
        "spot": summary["spot"],
        "target_30d_atm_iv": summary["target_30d_atm_iv"],
        "interpolation_method": interpolation["method"],
        "usable_expiries": summary["usable_expiries"],
        "near_expiry_days": near_expiry["trading_days_to_expiry"] if near_expiry is not None else np.nan,
        "near_expiry_iv": near_expiry["avg_iv"] if near_expiry is not None else np.nan,
        "far_expiry_days": far_expiry["trading_days_to_expiry"] if far_expiry is not None else np.nan,
        "far_expiry_iv": far_expiry["avg_iv"] if far_expiry is not None else np.nan,
    }


def append_history(summary: dict[str, Any], history_path: Path | None = None) -> pd.DataFrame:
    target_path = history_path or ac.get_options_iv_history_path()
    target_path.parent.mkdir(parents=True, exist_ok=True)
    next_row = pd.DataFrame([build_history_row(summary)])
    if target_path.exists():
        history = pd.read_csv(target_path)
        combined = pd.concat([history, next_row], ignore_index=True)
    else:
        combined = next_row
    combined["date"] = pd.to_datetime(combined["date"]).dt.normalize()
    combined = combined.sort_values("date").drop_duplicates(subset=["date", "underlying"], keep="last").reset_index(drop=True)
    combined.to_csv(target_path, index=False)
    return combined


def run(path: Path | None = None, output_path: Path | None = None) -> dict[str, Any]:
    chain_path = path or ac.get_options_chain_path()
    summary_path = output_path or ac.get_options_iv_summary_path()
    frame = load_option_chain(chain_path)
    summary = build_iv_summary(frame)
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    summary_path.write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
    append_history(summary)
    return summary


def main() -> None:
    summary = run()
    print(json.dumps(summary, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
