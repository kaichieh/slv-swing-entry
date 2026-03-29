"""
Prepare asset-specific swing-entry data with barrier-based labels.

Default label:
- 1 if +8% is hit before -4% within 60 trading days
- 0 if -4% is hit before +8% within 60 trading days
- neutral rows are dropped later
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from io import StringIO
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

import numpy as np
import pandas as pd

import asset_config as ac

ASSET_CONFIG = ac.load_asset_config()
HORIZON_DAYS = int(ASSET_CONFIG["horizon_days"])
UPPER_BARRIER = float(ASSET_CONFIG["upper_barrier"])
LOWER_BARRIER = float(ASSET_CONFIG["lower_barrier"])
BENCHMARK_SYMBOL = str(ASSET_CONFIG.get("benchmark_symbol", "")).strip().upper()
TRAIN_FRACTION = 0.70
VALID_FRACTION = 0.15
LABEL_MODE = str(ASSET_CONFIG["label_mode"])

CACHE_DIR = str(ac.get_cache_dir())
RAW_DATA_PATH = str(ac.get_raw_data_path())
PROCESSED_DATA_PATH = str(ac.get_processed_data_path())
METADATA_PATH = str(ac.get_metadata_path())
TARGET_COLUMN = "target_hit_up_first"

FEATURE_COLUMNS = [
    "ret_1",
    "ret_3",
    "ret_5",
    "ret_10",
    "ret_20",
    "sma_gap_5",
    "sma_gap_10",
    "sma_gap_20",
    "volatility_5",
    "volatility_10",
    "range_pct",
    "volume_change_1",
    "volume_vs_20",
    "breakout_20",
    "drawdown_20",
    "rsi_14",
    "overnight_gap",
    "intraday_return",
    "upper_shadow",
]

EXPERIMENTAL_FEATURE_COLUMNS = [
    "ret_60",
    "rolling_vol_60",
    "drawdown_60",
    "volatility_20",
    "volume_vs_60",
    "sma_gap_60",
    "range_z_20",
    "gap_up_flag",
    "gap_down_flag",
    "inside_bar",
    "outside_bar",
    "distance_to_252_high",
    "close_location_20",
    "up_day_ratio_20",
    "above_200dma_flag",
    "atr_pct_20",
    "rs_vs_benchmark_60",
]


@dataclass(frozen=True)
class DatasetSplit:
    features: np.ndarray
    labels: np.ndarray
    frame: pd.DataFrame


def get_env_int(name: str, default: int) -> int:
    value = os.getenv(name)
    return int(value) if value is not None else default


def get_env_float(name: str, default: float) -> float:
    value = os.getenv(name)
    return float(value) if value is not None else default


def get_env_str(name: str, default: str) -> str:
    value = os.getenv(name)
    return value.strip() if value is not None and value.strip() else default


def get_runtime_config() -> dict[str, float | int | str]:
    return {
        "horizon_days": get_env_int("AR_HORIZON_DAYS", HORIZON_DAYS),
        "upper_barrier": get_env_float("AR_UPPER_BARRIER", UPPER_BARRIER),
        "lower_barrier": get_env_float("AR_LOWER_BARRIER", LOWER_BARRIER),
        "label_mode": get_env_str("AR_LABEL_MODE", LABEL_MODE),
    }


def ensure_cache_dir() -> None:
    os.makedirs(CACHE_DIR, exist_ok=True)


def normalize_ohlcv_frame(frame: pd.DataFrame) -> pd.DataFrame:
    normalized = frame.copy()
    normalized.columns = [column.lower() for column in normalized.columns]
    expected = ["date", "open", "high", "low", "close", "volume"]
    missing = [column for column in expected if column not in normalized.columns]
    if missing:
        raise RuntimeError(f"Downloaded dataset missing columns: {missing}")
    normalized = normalized[expected].copy()
    normalized["date"] = pd.to_datetime(normalized["date"])
    normalized = normalized.sort_values("date").drop_duplicates(subset="date", keep="last").reset_index(drop=True)
    return normalized


def yahoo_chart_url(symbol: str) -> str:
    return (
        f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}"
        "?period1=0&period2=9999999999&interval=1d&includePrePost=false&events=div%2Csplits"
    )


def fetch_text(url: str, *, accept_json: bool = False) -> str:
    headers = {"User-Agent": "Mozilla/5.0"}
    if accept_json:
        headers["Accept"] = "application/json"
    request = Request(url, headers=headers)
    with urlopen(request, timeout=30) as response:
        charset = response.headers.get_content_charset() or "utf-8"
        return response.read().decode(charset)


def download_prices_from_yahoo(symbol: str) -> pd.DataFrame:
    payload = json.loads(fetch_text(yahoo_chart_url(symbol), accept_json=True))
    result = payload["chart"]["result"][0]
    quote = result["indicators"]["quote"][0]
    frame = pd.DataFrame(
        {
            "date": pd.to_datetime(result["timestamp"], unit="s", utc=True).tz_localize(None),
            "open": quote["open"],
            "high": quote["high"],
            "low": quote["low"],
            "close": quote["close"],
            "volume": quote["volume"],
        }
    )
    frame = frame.dropna(subset=["open", "high", "low", "close", "volume"])
    if frame.empty:
        raise RuntimeError("Yahoo chart dataset is empty after dropping missing OHLCV rows.")
    return normalize_ohlcv_frame(frame)


def download_prices_from_stooq(url: str) -> pd.DataFrame:
    frame = pd.read_csv(StringIO(fetch_text(url)))
    if frame.empty:
        raise RuntimeError(f"Downloaded {ac.get_asset_symbol()} dataset from stooq is empty.")
    return normalize_ohlcv_frame(frame)


def download_symbol_prices(symbol: str, stooq_url: str, cache_path: str) -> pd.DataFrame:
    ensure_cache_dir()
    try:
        frame = download_prices_from_yahoo(symbol)
    except (HTTPError, URLError, TimeoutError, ValueError, KeyError, IndexError):
        try:
            frame = download_prices_from_stooq(stooq_url)
        except (HTTPError, URLError, TimeoutError, pd.errors.EmptyDataError):
            if not os.path.exists(cache_path):
                raise
            frame = pd.read_csv(cache_path)
            if frame.empty:
                raise RuntimeError(f"Cached {symbol} dataset is empty.")
            frame = normalize_ohlcv_frame(frame)
    frame.to_csv(cache_path, index=False)
    return frame


def download_asset_prices() -> pd.DataFrame:
    symbol = ac.get_asset_symbol()
    return download_symbol_prices(symbol, ac.stooq_url(symbol), RAW_DATA_PATH)


def get_benchmark_cache_path(symbol: str) -> str:
    return os.path.join(CACHE_DIR, f"{symbol.lower()}_benchmark.csv")


def download_benchmark_prices(symbol: str) -> pd.DataFrame:
    return download_symbol_prices(symbol, ac.stooq_url(symbol), get_benchmark_cache_path(symbol))


def download_slv_prices() -> pd.DataFrame:
    return download_asset_prices()


def add_relative_strength_features(frame: pd.DataFrame, benchmark_symbol: str) -> pd.DataFrame:
    if not benchmark_symbol:
        return frame
    benchmark = add_price_features(download_benchmark_prices(benchmark_symbol))[["date", "ret_20", "ret_60"]].rename(
        columns={
            "ret_20": "benchmark_ret_20",
            "ret_60": "benchmark_ret_60",
        }
    )
    df = frame.merge(benchmark, on="date", how="left")
    df["rs_vs_benchmark_60"] = df["ret_60"] - df["benchmark_ret_60"]
    return df.drop(columns=["benchmark_ret_20", "benchmark_ret_60"])


def add_context_features(frame: pd.DataFrame) -> pd.DataFrame:
    df = frame.copy()
    close = df["close"]
    high = df["high"]
    low = df["low"]
    eps = 1e-6

    df["rolling_vol_60"] = df["ret_1"].rolling(60).std()
    rolling_high_252 = close.rolling(252).max()
    rolling_high_20 = high.rolling(20).max()
    rolling_low_20 = low.rolling(20).min()

    df["distance_to_252_high"] = close / rolling_high_252 - 1.0
    df["close_location_20"] = (close - rolling_low_20) / (rolling_high_20 - rolling_low_20 + eps)
    df["up_day_ratio_20"] = (df["ret_1"] > 0).astype(float).rolling(20).mean()
    df["above_200dma_flag"] = (close > close.rolling(200).mean()).astype(float)

    true_range = pd.concat(
        [
            (high - low),
            (high - close.shift(1)).abs(),
            (low - close.shift(1)).abs(),
        ],
        axis=1,
    ).max(axis=1)
    df["atr_pct_20"] = true_range.rolling(20).mean() / close
    return df


def build_barrier_labels(
    df: pd.DataFrame, horizon_days: int, upper_barrier: float, lower_barrier: float
) -> tuple[np.ndarray, np.ndarray]:
    closes = df["close"].to_numpy(dtype=np.float64)
    highs = df["high"].to_numpy(dtype=np.float64)
    lows = df["low"].to_numpy(dtype=np.float64)
    labels = np.full(len(df), np.nan, dtype=np.float64)
    realized_returns = np.full(len(df), np.nan, dtype=np.float64)

    for idx in range(len(df)):
        entry = closes[idx]
        end = min(len(df), idx + horizon_days + 1)
        if idx + 1 >= end:
            continue
        future_highs = highs[idx + 1 : end] / entry - 1.0
        future_lows = lows[idx + 1 : end] / entry - 1.0
        future_closes = closes[idx + 1 : end] / entry - 1.0
        realized_returns[idx] = future_closes[-1]

        hit_upper = np.where(future_highs >= upper_barrier)[0]
        hit_lower = np.where(future_lows <= lower_barrier)[0]
        upper_idx = int(hit_upper[0]) if hit_upper.size else None
        lower_idx = int(hit_lower[0]) if hit_lower.size else None

        if upper_idx is None and lower_idx is None:
            continue
        if upper_idx is not None and lower_idx is None:
            labels[idx] = 1.0
            continue
        if lower_idx is not None and upper_idx is None:
            labels[idx] = 0.0
            continue
        if upper_idx < lower_idx:
            labels[idx] = 1.0
        elif lower_idx < upper_idx:
            labels[idx] = 0.0
        else:
            labels[idx] = np.nan

    return labels, realized_returns


def add_price_features(frame: pd.DataFrame) -> pd.DataFrame:
    df = frame.copy()
    df.columns = [column.lower() for column in df.columns]
    df["date"] = pd.to_datetime(df["date"])
    df = df.sort_values("date").reset_index(drop=True)

    close = df["close"]
    open_price = df["open"]
    high = df["high"]
    low = df["low"]
    volume = df["volume"].replace(0, np.nan)

    df["ret_1"] = close.pct_change(1)
    df["ret_3"] = close.pct_change(3)
    df["ret_5"] = close.pct_change(5)
    df["ret_10"] = close.pct_change(10)
    df["ret_20"] = close.pct_change(20)
    df["ret_60"] = close.pct_change(60)

    df["sma_gap_5"] = close / close.rolling(5).mean() - 1.0
    df["sma_gap_10"] = close / close.rolling(10).mean() - 1.0
    df["sma_gap_20"] = close / close.rolling(20).mean() - 1.0
    df["sma_gap_60"] = close / close.rolling(60).mean() - 1.0

    df["volatility_5"] = df["ret_1"].rolling(5).std()
    df["volatility_10"] = df["ret_1"].rolling(10).std()
    df["volatility_20"] = df["ret_1"].rolling(20).std()
    df["range_pct"] = (high - low) / close
    df["volume_change_1"] = volume.pct_change(1)
    df["volume_vs_20"] = volume / volume.rolling(20).mean() - 1.0
    df["volume_vs_60"] = volume / volume.rolling(60).mean() - 1.0

    df["breakout_20"] = (close > close.shift(1).rolling(20).max()).astype(float)
    df["drawdown_20"] = (close - close.rolling(20).max()) / close.rolling(20).max()
    df["drawdown_60"] = (close - close.rolling(60).max()) / close.rolling(60).max()

    delta = close.diff()
    gain = delta.where(delta > 0, 0).rolling(14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
    rs = gain / (loss + 1e-10)
    df["rsi_14"] = 100 - (100 / (1 + rs))

    prev_close = close.shift(1)
    eps = 1e-6
    range_size = np.maximum((high - low).to_numpy(dtype=np.float32), eps)
    body = (close - open_price).to_numpy(dtype=np.float32)
    df["overnight_gap"] = open_price / prev_close - 1.0
    df["intraday_return"] = body / np.maximum(open_price.to_numpy(dtype=np.float32), eps)
    df["upper_shadow"] = (
        high.to_numpy(dtype=np.float32)
        - np.maximum(open_price.to_numpy(dtype=np.float32), close.to_numpy(dtype=np.float32))
    ) / np.maximum(close.to_numpy(dtype=np.float32), eps)
    df["range_z_20"] = (df["range_pct"] - df["range_pct"].rolling(20).mean()) / (
        df["range_pct"].rolling(20).std() + 1e-10
    )

    prev_high = high.shift(1)
    prev_low = low.shift(1)
    prev_open = open_price.shift(1)
    prev_close = close.shift(1)
    prev_body_high = np.maximum(prev_open, prev_close)
    prev_body_low = np.minimum(prev_open, prev_close)
    df["inside_bar"] = ((high <= prev_high) & (low >= prev_low)).astype(float)
    df["outside_bar"] = ((high >= prev_high) & (low <= prev_low)).astype(float)
    df["gap_up_flag"] = (open_price > prev_body_high).astype(float)
    df["gap_down_flag"] = (open_price < prev_body_low).astype(float)
    return df


def add_features(frame: pd.DataFrame) -> pd.DataFrame:
    config = get_runtime_config()
    df = add_price_features(frame)
    df = add_relative_strength_features(df, BENCHMARK_SYMBOL)
    df = add_context_features(df)
    labels, realized_returns = build_barrier_labels(
        df,
        int(config["horizon_days"]),
        float(config["upper_barrier"]),
        float(config["lower_barrier"]),
    )
    if config["label_mode"] == "keep-all-binary":
        labels = np.where(np.isnan(labels), 0.0, labels)
    df[TARGET_COLUMN] = labels
    df["future_return_60"] = realized_returns

    # Keep experimental features selectable without silently leaking NaNs into training.
    needed = FEATURE_COLUMNS + EXPERIMENTAL_FEATURE_COLUMNS + ["future_return_60"]
    if config["label_mode"] != "keep-all-binary":
        needed.append(TARGET_COLUMN)
    df = df.replace([np.inf, -np.inf], np.nan)
    df = df.dropna(subset=needed).reset_index(drop=True)
    return df


def split_indices(num_rows: int) -> tuple[int, int]:
    train_end = int(num_rows * TRAIN_FRACTION)
    valid_end = train_end + int(num_rows * VALID_FRACTION)
    if train_end <= 0 or valid_end >= num_rows:
        raise RuntimeError("Not enough rows to create chronological splits.")
    return train_end, valid_end


def save_processed_dataset(df: pd.DataFrame) -> None:
    config = get_runtime_config()
    train_end, valid_end = split_indices(len(df))
    ensure_cache_dir()
    df.to_csv(PROCESSED_DATA_PATH, index=False)
    metadata = {
        "asset_key": str(ASSET_CONFIG["asset_key"]),
        "symbol": ac.get_asset_symbol(),
        "horizon_days": int(config["horizon_days"]),
        "upper_barrier": float(config["upper_barrier"]),
        "lower_barrier": float(config["lower_barrier"]),
        "label_mode": str(config["label_mode"]),
        "feature_columns": FEATURE_COLUMNS,
        "target_column": TARGET_COLUMN,
        "train_rows": train_end,
        "validation_rows": valid_end - train_end,
        "test_rows": len(df) - valid_end,
        "positive_rate": float(df[TARGET_COLUMN].mean()),
        "total_rows": len(df),
        "date_start": df["date"].iloc[0].strftime("%Y-%m-%d"),
        "date_end": df["date"].iloc[-1].strftime("%Y-%m-%d"),
    }
    with open(METADATA_PATH, "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2)


def load_dataset_frame() -> pd.DataFrame:
    if not os.path.exists(PROCESSED_DATA_PATH):
        raise FileNotFoundError(f"Processed dataset not found at {PROCESSED_DATA_PATH}. Run prepare.py first.")
    return pd.read_csv(PROCESSED_DATA_PATH, parse_dates=["date"])


def load_splits() -> dict[str, DatasetSplit]:
    df = load_dataset_frame()
    train_end, valid_end = split_indices(len(df))
    splits = {
        "train": df.iloc[:train_end].copy(),
        "validation": df.iloc[train_end:valid_end].copy(),
        "test": df.iloc[valid_end:].copy(),
    }
    output: dict[str, DatasetSplit] = {}
    for name, frame in splits.items():
        output[name] = DatasetSplit(
            features=frame[FEATURE_COLUMNS].to_numpy(dtype=np.float32),
            labels=frame[TARGET_COLUMN].to_numpy(dtype=np.float32),
            frame=frame,
        )
    return output


def describe_dataset(df: pd.DataFrame) -> str:
    train_end, valid_end = split_indices(len(df))
    lines = [
        f"Rows: {len(df)}",
        f"Date range: {df['date'].iloc[0].date()} -> {df['date'].iloc[-1].date()}",
        f"Train/validation/test: {train_end}/{valid_end - train_end}/{len(df) - valid_end}",
        f"Positive class rate: {df[TARGET_COLUMN].mean():.3f}",
        f"Features: {', '.join(FEATURE_COLUMNS)}",
    ]
    return "\n".join(lines)


def main() -> None:
    config = get_runtime_config()
    symbol = ac.get_asset_symbol()
    print(f"Downloading {symbol} daily prices...")
    raw = download_asset_prices()
    processed = add_features(raw)
    save_processed_dataset(processed)
    print("Prepared dataset:")
    print(
        "Label config: "
        f"horizon={config['horizon_days']}, "
        f"upper={float(config['upper_barrier']):.2%}, "
        f"lower={float(config['lower_barrier']):.2%}, "
        f"mode={config['label_mode']}"
    )
    print(describe_dataset(processed))
    print(f"Processed data saved to: {PROCESSED_DATA_PATH}")


if __name__ == "__main__":
    main()
