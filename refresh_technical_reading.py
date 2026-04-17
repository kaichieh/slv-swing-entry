from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping, cast

import pandas as pd

import asset_config as ac


ENUM_ZH_MAPPING: dict[str, dict[str, str]] = {
    "A_trend": {
        "bullish": "多頭",
        "bearish": "空頭",
        "sideways": "震盪",
        "bullish_rebound": "多頭反彈",
        "bearish_pullback": "空頭回檔",
    },
    "B_price_vs_ma": {
        "above": "在均線上方",
        "below": "在均線下方",
        "near": "接近均線",
        "crossing_up": "向上穿越均線",
        "crossing_down": "向下跌破均線",
    },
    "C_rsi_state": {
        "overbought": "過熱／超買",
        "strong": "偏強",
        "neutral": "中性",
        "weak": "偏弱",
        "oversold": "超賣",
    },
    "D_kd_state": {
        "golden_cross": "黃金交叉",
        "death_cross": "死亡交叉",
        "high_level_flattening": "高檔鈍化",
        "low_level_flattening": "低檔鈍化",
        "overbought": "高檔過熱",
        "oversold": "低檔超賣",
        "neutral": "中性",
    },
    "E_levels.type": {
        "support": "支撐",
        "resistance": "壓力",
    },
    "E_levels.strength": {
        "weak": "弱",
        "medium": "中",
        "strong": "強",
    },
    "E_levels.status": {
        "holding": "守住中",
        "broken": "已跌破／已突破",
        "tested": "測試中",
    },
    "F_volume_state": {
        "expanding_on_rise": "上漲放量",
        "contracting_on_rise": "上漲縮量",
        "expanding_on_drop": "下跌放量",
        "contracting_on_drop": "下跌縮量",
        "volume_spike": "爆量",
        "normal": "量能正常",
        "dry_up": "量縮",
    },
    "G_ma_structure": {
        "bullish_alignment": "均線多頭排列",
        "bearish_alignment": "均線空頭排列",
        "mixed": "均線混合／排列混亂",
        "golden_cross": "均線黃金交叉",
        "death_cross": "均線死亡交叉",
        "compression": "均線糾結",
        "expanding": "均線發散",
    },
    "H_macd_state": {
        "golden_cross": "MACD 黃金交叉",
        "death_cross": "MACD 死亡交叉",
        "bullish_expanding": "多方柱狀體擴大",
        "bullish_contracting": "多方柱狀體縮小",
        "bearish_expanding": "空方柱狀體擴大",
        "bearish_contracting": "空方柱狀體縮小",
        "neutral": "中性",
    },
    "I_divergence_state": {
        "bullish_divergence": "偏多背離",
        "bearish_divergence": "偏空背離",
        "hidden_bullish_divergence": "隱性偏多背離",
        "hidden_bearish_divergence": "隱性偏空背離",
        "none": "無",
    },
    "J_candlestick_pattern": {
        "bullish_engulfing": "多頭吞噬",
        "bearish_engulfing": "空頭吞噬",
        "hammer": "錘子線",
        "shooting_star": "射擊之星",
        "doji": "十字線",
        "long_bullish_candle": "長紅K",
        "long_bearish_candle": "長黑K",
        "inside_bar": "內包線",
        "none": "無明確型態",
    },
    "K_trade_action": {
        "buy_pullback": "等回檔買進",
        "buy_breakout": "等突破買進",
        "hold": "持有",
        "wait": "觀望",
        "reduce": "減碼",
        "sell": "賣出",
        "avoid": "避開",
    },
    "L_price_volume_divergence": {
        "bearish_volume_divergence": "偏空價量背離",
        "bullish_volume_divergence": "偏多價量背離",
        "price_volume_confirmed": "價量配合確認",
        "inconclusive": "訊號不明",
        "none": "無",
    },
}

ENUM_ZH_MAPPING = {
    "A_trend": {
        "bullish": "多頭",
        "bearish": "空頭",
        "sideways": "震盪",
        "bullish_rebound": "多頭反彈",
        "bearish_pullback": "空頭回檔",
    },
    "B_price_vs_ma": {
        "above": "在均線上方",
        "below": "在均線下方",
        "near": "接近均線",
        "crossing_up": "向上穿越均線",
        "crossing_down": "向下跌破均線",
    },
    "C_rsi_state": {
        "overbought": "過熱／超買",
        "strong": "偏強",
        "neutral": "中性",
        "weak": "偏弱",
        "oversold": "超賣",
    },
    "D_kd_state": {
        "golden_cross": "黃金交叉",
        "death_cross": "死亡交叉",
        "high_level_flattening": "高檔鈍化",
        "low_level_flattening": "低檔鈍化",
        "overbought": "高檔過熱",
        "oversold": "低檔超賣",
        "neutral": "中性",
    },
    "E_levels.type": {
        "support": "支撐",
        "resistance": "壓力",
    },
    "E_levels.strength": {
        "weak": "弱",
        "medium": "中",
        "strong": "強",
    },
    "E_levels.status": {
        "holding": "守住中",
        "broken": "已跌破／已突破",
        "tested": "測試中",
    },
    "F_volume_state": {
        "expanding_on_rise": "上漲放量",
        "contracting_on_rise": "上漲縮量",
        "expanding_on_drop": "下跌放量",
        "contracting_on_drop": "下跌縮量",
        "volume_spike": "爆量",
        "normal": "量能正常",
        "dry_up": "量縮",
    },
    "G_ma_structure": {
        "bullish_alignment": "均線多頭排列",
        "bearish_alignment": "均線空頭排列",
        "mixed": "均線混合／排列混亂",
        "golden_cross": "均線黃金交叉",
        "death_cross": "均線死亡交叉",
        "compression": "均線糾結",
        "expanding": "均線發散",
    },
    "H_macd_state": {
        "golden_cross": "MACD 黃金交叉",
        "death_cross": "MACD 死亡交叉",
        "bullish_expanding": "多方柱狀體擴大",
        "bullish_contracting": "多方柱狀體縮小",
        "bearish_expanding": "空方柱狀體擴大",
        "bearish_contracting": "空方柱狀體縮小",
        "neutral": "中性",
    },
    "I_divergence_state": {
        "bullish_divergence": "偏多背離",
        "bearish_divergence": "偏空背離",
        "hidden_bullish_divergence": "隱性偏多背離",
        "hidden_bearish_divergence": "隱性偏空背離",
        "none": "無",
    },
    "J_candlestick_pattern": {
        "bullish_engulfing": "多頭吞噬",
        "bearish_engulfing": "空頭吞噬",
        "hammer": "錘子線",
        "shooting_star": "射擊之星",
        "doji": "十字線",
        "long_bullish_candle": "長紅K",
        "long_bearish_candle": "長黑K",
        "inside_bar": "內包線",
        "none": "無明確型態",
    },
    "K_trade_action": {
        "buy_pullback": "等回檔買進",
        "buy_breakout": "等突破買進",
        "hold": "持有",
        "wait": "觀望",
        "reduce": "減碼",
        "sell": "賣出",
        "avoid": "避開",
    },
    "L_price_volume_divergence": {
        "bearish_volume_divergence": "偏空價量背離",
        "bullish_volume_divergence": "偏多價量背離",
        "price_volume_confirmed": "價量配合確認",
        "inconclusive": "訊號不明",
        "none": "無",
    },
}

PHASE_1_PENDING_FIELDS = ("D_kd_state", "E_levels", "H_macd_state", "I_divergence_state", "J_candlestick_pattern", "L_price_volume_divergence")


def load_json(path: Path) -> dict[str, object]:
    if not path.exists():
        raise FileNotFoundError(f"Missing required JSON input: {path}")
    return cast(dict[str, object], json.loads(path.read_text(encoding="utf-8")))


def load_snapshot(path: Path) -> dict[str, object]:
    if not path.exists():
        raise FileNotFoundError(f"Missing required TSV input: {path}")
    frame = pd.read_csv(path, sep="\t")
    if frame.empty:
        raise ValueError(f"Snapshot file is empty: {path}")
    return cast(dict[str, object], frame.iloc[-1].to_dict())


def load_raw_prices(path: Path) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(f"Missing required raw price input: {path}")
    frame = pd.read_csv(path, parse_dates=["date"])
    if frame.empty:
        raise ValueError(f"Raw price input is empty: {path}")
    return frame.sort_values("date").reset_index(drop=True)


def metric(payload: Mapping[str, object], field_name: str, default: float = 0.0) -> float:
    snapshot = cast(dict[str, object], payload.get("latest_feature_snapshot", {}))
    raw_value = snapshot.get(field_name, default)
    return float(cast(float | int | str, raw_value))


def calc_rsi_series(closes: pd.Series, period: int = 14) -> pd.Series:
    delta = closes.diff()
    gains = delta.clip(lower=0.0)
    losses = (-delta.clip(upper=0.0))
    avg_gain = gains.rolling(period).mean()
    avg_loss = losses.rolling(period).mean()
    rs = avg_gain / (avg_loss + 1e-10)
    return 100.0 - (100.0 / (1.0 + rs))


def classify_trend(payload: Mapping[str, object]) -> str:
    ret_60 = metric(payload, "ret_60")
    sma_gap_60 = metric(payload, "sma_gap_60")
    sma_gap_20 = metric(payload, "sma_gap_20")
    if ret_60 >= 0.03 and sma_gap_60 >= 0.03:
        return "bullish"
    if ret_60 <= -0.03 and sma_gap_60 <= -0.03:
        return "bearish"
    if ret_60 < 0.0 and sma_gap_20 > 0.02:
        return "bullish_rebound"
    if ret_60 > 0.0 and sma_gap_20 < -0.02:
        return "bearish_pullback"
    return "sideways"


def classify_price_vs_ma(payload: Mapping[str, object]) -> str:
    sma_gap_20 = metric(payload, "sma_gap_20")
    if sma_gap_20 >= 0.02:
        return "above"
    if sma_gap_20 <= -0.02:
        return "below"
    return "near"


def classify_rsi_state(payload: Mapping[str, object]) -> str:
    rsi_14 = metric(payload, "rsi_14", 50.0)
    if rsi_14 >= 70.0:
        return "overbought"
    if rsi_14 >= 60.0:
        return "strong"
    if rsi_14 <= 30.0:
        return "oversold"
    if rsi_14 <= 45.0:
        return "weak"
    return "neutral"


def classify_volume_state(payload: Mapping[str, object]) -> str:
    ret_20 = metric(payload, "ret_20")
    volume_vs_20 = metric(payload, "volume_vs_20")
    if volume_vs_20 >= 1.0:
        return "volume_spike"
    if volume_vs_20 <= -0.5:
        return "dry_up"
    if ret_20 >= 0.0 and volume_vs_20 >= 0.15:
        return "expanding_on_rise"
    if ret_20 >= 0.0 and volume_vs_20 < 0.0:
        return "contracting_on_rise"
    if ret_20 < 0.0 and volume_vs_20 >= 0.15:
        return "expanding_on_drop"
    if ret_20 < 0.0 and volume_vs_20 < 0.0:
        return "contracting_on_drop"
    return "normal"


def classify_ma_structure(payload: Mapping[str, object]) -> str:
    sma_gap_20 = metric(payload, "sma_gap_20")
    sma_gap_60 = metric(payload, "sma_gap_60")
    if abs(sma_gap_20) <= 0.02 and abs(sma_gap_60) <= 0.02:
        return "compression"
    if sma_gap_20 >= 0.03 and sma_gap_60 >= 0.03:
        return "bullish_alignment"
    if sma_gap_20 <= -0.03 and sma_gap_60 <= -0.03:
        return "bearish_alignment"
    if (sma_gap_20 > 0.0 and sma_gap_60 < 0.0) or (sma_gap_20 < 0.0 and sma_gap_60 > 0.0):
        return "mixed"
    if abs(sma_gap_20 - sma_gap_60) >= 0.05:
        return "expanding"
    return "mixed"


def classify_trade_action(payload: Mapping[str, object], snapshot: Mapping[str, object]) -> str:
    signal_summary = cast(dict[str, object], payload.get("signal_summary", {}))
    buy_point_summary = cast(dict[str, object], payload.get("buy_point_summary", {}))
    rule_summary = cast(dict[str, object], payload.get("rule_summary", {}))
    signal = str(signal_summary.get("signal", "")).strip().lower()
    buy_point_ok = bool(buy_point_summary.get("buy_point_ok", False))
    rule_selected = bool(rule_summary.get("selected", False))
    monitor_action = str(snapshot.get("action", "")).strip().lower()
    price_vs_ma = classify_price_vs_ma(payload)

    if signal == "no_entry" and not rule_selected:
        return "wait"
    if monitor_action == "selected_now" and buy_point_ok:
        return "buy_breakout" if price_vs_ma == "above" else "buy_pullback"
    if rule_selected and not buy_point_ok:
        return "buy_pullback"
    if signal in {"bullish", "strong_bullish", "very_strong_bullish"} and buy_point_ok:
        return "buy_breakout" if price_vs_ma == "above" else "buy_pullback"
    if signal in {"bullish", "weak_bullish"}:
        return "hold"
    return "wait"


def classify_kd_state(raw_prices: pd.DataFrame) -> str:
    lows = raw_prices["low"].rolling(9).min()
    highs = raw_prices["high"].rolling(9).max()
    denominator = (highs - lows).replace(0.0, 1e-10)
    raw_k = 100.0 * (raw_prices["close"] - lows) / denominator
    k_series = raw_k.rolling(3).mean()
    d_series = k_series.rolling(3).mean()
    latest_k = float(k_series.iloc[-1])
    latest_d = float(d_series.iloc[-1])
    prev_k = float(k_series.iloc[-2])
    prev_d = float(d_series.iloc[-2])

    if prev_k <= prev_d and latest_k > latest_d:
        return "golden_cross"
    if prev_k >= prev_d and latest_k < latest_d:
        return "death_cross"
    if latest_k >= 80.0 and latest_d >= 80.0 and abs(latest_k - latest_d) <= 5.0:
        return "high_level_flattening"
    if latest_k <= 20.0 and latest_d <= 20.0 and abs(latest_k - latest_d) <= 5.0:
        return "low_level_flattening"
    if latest_k >= 80.0 or latest_d >= 80.0:
        return "overbought"
    if latest_k <= 20.0 or latest_d <= 20.0:
        return "oversold"
    return "neutral"


def _level_status(level_type: str, close_value: float, level_value: float) -> str:
    if level_type == "support":
        if close_value < level_value * 0.995:
            return "broken"
        if abs(close_value - level_value) / level_value <= 0.02:
            return "tested"
        return "holding"
    if close_value > level_value * 1.005:
        return "broken"
    if abs(close_value - level_value) / level_value <= 0.02:
        return "tested"
    return "holding"


def classify_levels(raw_prices: pd.DataFrame, payload: Mapping[str, object]) -> list[dict[str, object]]:
    close_value = float(cast(float | int | str, payload.get("latest_close", raw_prices["close"].iloc[-1])))
    ma20 = float(raw_prices["close"].rolling(20).mean().iloc[-1])
    ma60 = float(raw_prices["close"].rolling(60).mean().iloc[-1])
    recent_low_20 = float(raw_prices["low"].tail(20).min())
    recent_high_20 = float(raw_prices["high"].tail(20).max())
    candidate_levels = [
        {"type": "support", "level": recent_low_20, "strength": "medium"},
        {"type": "support", "level": ma20, "strength": "medium"},
        {"type": "support", "level": ma60, "strength": "strong"},
        {"type": "resistance", "level": recent_high_20, "strength": "medium"},
    ]

    levels: list[dict[str, object]] = []
    for candidate in candidate_levels:
        level_value = float(candidate["level"])
        if level_value <= 0.0:
            continue
        duplicate = False
        for existing in levels:
            existing_level = float(cast(float | int | str, existing["level"]))
            if abs(existing_level - level_value) / existing_level <= 0.02 and str(existing["type"]) == str(candidate["type"]):
                duplicate = True
                break
        if duplicate:
            continue
        levels.append(
            {
                "type": str(candidate["type"]),
                "level": round(level_value, 2),
                "strength": str(candidate["strength"]),
                "status": _level_status(str(candidate["type"]), close_value, level_value),
            }
        )
    return levels


def classify_macd_state(raw_prices: pd.DataFrame) -> str:
    closes = raw_prices["close"]
    ema12 = closes.ewm(span=12, adjust=False).mean()
    ema26 = closes.ewm(span=26, adjust=False).mean()
    macd_line = ema12 - ema26
    signal_line = macd_line.ewm(span=9, adjust=False).mean()
    histogram = macd_line - signal_line
    latest_hist = float(histogram.iloc[-1])
    prev_hist = float(histogram.iloc[-2])

    if prev_hist <= 0.0 and latest_hist > 0.0:
        return "golden_cross"
    if prev_hist >= 0.0 and latest_hist < 0.0:
        return "death_cross"
    if latest_hist > 0.0:
        return "bullish_expanding" if latest_hist > prev_hist else "bullish_contracting"
    if latest_hist < 0.0:
        return "bearish_expanding" if latest_hist < prev_hist else "bearish_contracting"
    return "neutral"


def classify_divergence_state(raw_prices: pd.DataFrame) -> str:
    window = raw_prices.tail(20).reset_index(drop=True)
    if len(window) < 20:
        return "none"
    closes = window["close"]
    rsi_series = calc_rsi_series(closes).fillna(50.0)
    early = window.iloc[:10]
    late = window.iloc[10:]
    early_rsi = rsi_series.iloc[:10]
    late_rsi = rsi_series.iloc[10:]

    if float(late["low"].min()) < float(early["low"].min()) and float(late_rsi.min()) > float(early_rsi.min()):
        return "bullish_divergence"
    if float(late["high"].max()) > float(early["high"].max()) and float(late_rsi.max()) < float(early_rsi.max()):
        return "bearish_divergence"
    if float(late["low"].min()) > float(early["low"].min()) and float(late_rsi.min()) < float(early_rsi.min()):
        return "hidden_bullish_divergence"
    if float(late["high"].max()) < float(early["high"].max()) and float(late_rsi.max()) > float(early_rsi.max()):
        return "hidden_bearish_divergence"
    return "none"


def classify_candlestick_pattern(raw_prices: pd.DataFrame) -> str:
    latest = raw_prices.iloc[-1]
    previous = raw_prices.iloc[-2]
    open_value = float(latest["open"])
    high_value = float(latest["high"])
    low_value = float(latest["low"])
    close_value = float(latest["close"])
    prev_open = float(previous["open"])
    prev_high = float(previous["high"])
    prev_low = float(previous["low"])
    prev_close = float(previous["close"])
    body = close_value - open_value
    prev_body = prev_close - prev_open
    candle_range = max(high_value - low_value, 1e-10)
    upper_shadow = high_value - max(open_value, close_value)
    lower_shadow = min(open_value, close_value) - low_value

    if close_value > open_value and open_value <= prev_close and close_value >= prev_open and abs(body) > abs(prev_body):
        return "bullish_engulfing"
    if close_value < open_value and open_value >= prev_close and close_value <= prev_open and abs(body) > abs(prev_body):
        return "bearish_engulfing"
    if abs(body) / candle_range <= 0.1:
        return "doji"
    if lower_shadow >= abs(body) * 2.0 and upper_shadow <= abs(body) * 0.5:
        return "hammer"
    if upper_shadow >= abs(body) * 2.0 and lower_shadow <= abs(body) * 0.5:
        return "shooting_star"
    if abs(body) / candle_range >= 0.6 and body > 0.0:
        return "long_bullish_candle"
    if abs(body) / candle_range >= 0.6 and body < 0.0:
        return "long_bearish_candle"
    if high_value <= prev_high and low_value >= prev_low:
        return "inside_bar"
    return "none"


def classify_price_volume_divergence(payload: Mapping[str, object], raw_prices: pd.DataFrame) -> str:
    ret_20 = metric(payload, "ret_20")
    volume_vs_20 = metric(payload, "volume_vs_20")
    close_5 = float(raw_prices["close"].iloc[-1] / raw_prices["close"].iloc[-6] - 1.0) if len(raw_prices) >= 6 else 0.0
    if ret_20 >= 0.03 and (volume_vs_20 <= -0.2 or close_5 > 0.0 and volume_vs_20 < 0.0):
        return "bearish_volume_divergence"
    if ret_20 <= -0.03 and volume_vs_20 <= -0.2:
        return "bullish_volume_divergence"
    if abs(ret_20) >= 0.03 and volume_vs_20 >= 0.15:
        return "price_volume_confirmed"
    if abs(ret_20) < 0.03:
        return "inconclusive"
    return "none"


def label_for(mapping_key: str, enum_value: object) -> str | None:
    if enum_value is None:
        return None
    value = str(enum_value)
    return ENUM_ZH_MAPPING.get(mapping_key, {}).get(value)


def translate_levels(levels: list[dict[str, object]]) -> list[dict[str, object]]:
    translated: list[dict[str, object]] = []
    for level in levels:
        translated.append(
            {
                "type": str(level["type"]),
                "type_zh": label_for("E_levels.type", level["type"]),
                "level": level["level"],
                "strength": str(level["strength"]),
                "strength_zh": label_for("E_levels.strength", level["strength"]),
                "status": str(level["status"]),
                "status_zh": label_for("E_levels.status", level["status"]),
            }
        )
    return translated


def build_reading() -> dict[str, object]:
    payload = load_json(ac.get_latest_prediction_path())
    snapshot = load_snapshot(ac.get_monitor_snapshot_path())
    raw_prices = load_raw_prices(ac.get_raw_data_path())
    asset_key = ac.get_asset_key()
    symbol = ac.get_asset_symbol()
    latest_date = str(payload.get("latest_raw_date", ""))

    a_trend = classify_trend(payload)
    b_price_vs_ma = classify_price_vs_ma(payload)
    c_rsi_state = classify_rsi_state(payload)
    d_kd_state = classify_kd_state(raw_prices)
    e_levels = classify_levels(raw_prices, payload)
    f_volume_state = classify_volume_state(payload)
    g_ma_structure = classify_ma_structure(payload)
    h_macd_state = classify_macd_state(raw_prices)
    i_divergence_state = classify_divergence_state(raw_prices)
    j_candlestick_pattern = classify_candlestick_pattern(raw_prices)
    k_trade_action = classify_trade_action(payload, snapshot)
    l_price_volume_divergence = classify_price_volume_divergence(payload, raw_prices)

    technical_reading: dict[str, object] = {
        "A_trend": a_trend,
        "B_price_vs_ma": b_price_vs_ma,
        "C_rsi_state": c_rsi_state,
        "D_kd_state": d_kd_state,
        "E_levels": e_levels,
        "F_volume_state": f_volume_state,
        "G_ma_structure": g_ma_structure,
        "H_macd_state": h_macd_state,
        "I_divergence_state": i_divergence_state,
        "J_candlestick_pattern": j_candlestick_pattern,
        "K_trade_action": k_trade_action,
        "L_price_volume_divergence": l_price_volume_divergence,
    }

    phase_status = {
        key: ("ready" if technical_reading[key] not in (None, []) else "pending")
        for key in technical_reading
    }

    result = {
        "symbol": symbol,
        "asset_key": asset_key,
        "date": latest_date,
        "technical_reading": technical_reading,
        "technical_reading_zh": {
            key: (
                translate_levels(cast(list[dict[str, object]], technical_reading[key]))
                if key == "E_levels"
                else label_for(key, technical_reading[key])
            )
            for key in technical_reading
        },
        "supporting_metrics": {
            "latest_close": payload.get("latest_close"),
            "ret_20": round(metric(payload, "ret_20"), 4),
            "ret_60": round(metric(payload, "ret_60"), 4),
            "sma_gap_20": round(metric(payload, "sma_gap_20"), 4),
            "sma_gap_60": round(metric(payload, "sma_gap_60"), 4),
            "drawdown_20": round(metric(payload, "drawdown_20"), 4),
            "rsi_14": round(metric(payload, "rsi_14", 50.0), 4),
            "volume_vs_20": round(metric(payload, "volume_vs_20"), 4),
            "predicted_probability": cast(dict[str, object], payload.get("signal_summary", {})).get("predicted_probability"),
            "decision_threshold": cast(dict[str, object], payload.get("signal_summary", {})).get("decision_threshold"),
            "monitor_action": snapshot.get("action"),
        },
        "phase_status": phase_status,
        "enum_zh_mapping": ENUM_ZH_MAPPING,
        "notes": [
            "Phase 2 fills D, E, H, I, J, L using rule-based heuristics from cached OHLCV data.",
            "Support and resistance levels are approximated from recent range and moving averages rather than manually curated annotations.",
        ],
    }
    return result


def build_tsv_row(reading: Mapping[str, object]) -> pd.DataFrame:
    technical = cast(dict[str, object], reading["technical_reading"])
    technical_zh = cast(dict[str, object], reading["technical_reading_zh"])
    levels_json = json.dumps(technical["E_levels"], ensure_ascii=False)
    levels_zh_json = json.dumps(technical_zh["E_levels"], ensure_ascii=False)
    return pd.DataFrame(
        [
            {
                "asset_key": reading["asset_key"],
                "symbol": reading["symbol"],
                "date": reading["date"],
                "A_trend": technical["A_trend"],
                "A_trend_zh": technical_zh["A_trend"],
                "B_price_vs_ma": technical["B_price_vs_ma"],
                "B_price_vs_ma_zh": technical_zh["B_price_vs_ma"],
                "C_rsi_state": technical["C_rsi_state"],
                "C_rsi_state_zh": technical_zh["C_rsi_state"],
                "D_kd_state": technical["D_kd_state"],
                "D_kd_state_zh": technical_zh["D_kd_state"],
                "E_levels": levels_json,
                "E_levels_zh": levels_zh_json,
                "F_volume_state": technical["F_volume_state"],
                "F_volume_state_zh": technical_zh["F_volume_state"],
                "G_ma_structure": technical["G_ma_structure"],
                "G_ma_structure_zh": technical_zh["G_ma_structure"],
                "H_macd_state": technical["H_macd_state"],
                "H_macd_state_zh": technical_zh["H_macd_state"],
                "I_divergence_state": technical["I_divergence_state"],
                "I_divergence_state_zh": technical_zh["I_divergence_state"],
                "J_candlestick_pattern": technical["J_candlestick_pattern"],
                "J_candlestick_pattern_zh": technical_zh["J_candlestick_pattern"],
                "K_trade_action": technical["K_trade_action"],
                "K_trade_action_zh": technical_zh["K_trade_action"],
                "L_price_volume_divergence": technical["L_price_volume_divergence"],
                "L_price_volume_divergence_zh": technical_zh["L_price_volume_divergence"],
            }
        ]
    )


def main() -> None:
    reading = build_reading()
    json_path = ac.get_technical_reading_json_path()
    tsv_path = ac.get_technical_reading_tsv_path()
    json_path.write_text(json.dumps(reading, indent=2, ensure_ascii=False), encoding="utf-8")
    build_tsv_row(reading).to_csv(tsv_path, sep="\t", index=False)
    print(
        json.dumps(
            {
                "asset_key": reading["asset_key"],
                "json_path": str(json_path),
                "tsv_path": str(tsv_path),
                "filled_fields": list(cast(dict[str, object], reading["technical_reading"]).keys()),
                "pending_fields": [
                    key for key, status in cast(dict[str, str], reading["phase_status"]).items() if status != "ready"
                ],
            },
            indent=2,
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()
