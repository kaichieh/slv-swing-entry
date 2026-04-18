from __future__ import annotations

import json
import re
from html import escape
from typing import Any, cast

import pandas as pd

import asset_config as ac

ACTION_PRIORITY = {
    "selected_now": 0,
    "watchlist_wait": 1,
    "watchlist_blocked": 1,
    "inactive_wait": 2,
    "reference_only": 3,
    "research_only": 4,
}

MIXED_ACTION_PRIORITY = {
    "selected_now": 0,
    "watchlist_wait": 1,
    "watchlist_blocked": 1,
    "priority_research": 2,
    "inactive_wait": 3,
    "reference_only": 4,
    "research_only": 5,
}

PRIORITY_RESEARCH_SIGNAL_COLOR = "#7c3aed"
FOLLOWUP_ROUNDS = (4, 3, 2)

TECHNICAL_ENUM_ZH: dict[str, dict[str, str]] = {
    "A_trend": {
        "bullish": "\u591a\u982d",
        "bearish": "\u7a7a\u982d",
        "sideways": "\u9707\u76ea",
        "bullish_rebound": "\u591a\u982d\u53cd\u5f48",
        "bearish_pullback": "\u7a7a\u982d\u56de\u6a94",
    },
    "B_price_vs_ma": {
        "above": "\u5728\u5747\u7dda\u4e0a\u65b9",
        "below": "\u5728\u5747\u7dda\u4e0b\u65b9",
        "near": "\u63a5\u8fd1\u5747\u7dda",
        "crossing_up": "\u5411\u4e0a\u7a7f\u8d8a\u5747\u7dda",
        "crossing_down": "\u5411\u4e0b\u8dcc\u7834\u5747\u7dda",
    },
    "C_rsi_state": {
        "overbought": "\u904e\u71b1",
        "strong": "\u504f\u5f37",
        "neutral": "\u4e2d\u6027",
        "weak": "\u504f\u5f31",
        "oversold": "\u8d85\u8ce3",
    },
    "D_kd_state": {
        "golden_cross": "\u9ec3\u91d1\u4ea4\u53c9",
        "death_cross": "\u6b7b\u4ea1\u4ea4\u53c9",
        "high_level_flattening": "\u9ad8\u6a94\u921d\u5316",
        "low_level_flattening": "\u4f4e\u6a94\u921d\u5316",
        "overbought": "\u9ad8\u6a94\u904e\u71b1",
        "oversold": "\u4f4e\u6a94\u8d85\u8ce3",
        "neutral": "\u4e2d\u6027",
    },
    "E_levels.type": {
        "support": "\u652f\u6490",
        "resistance": "\u58d3\u529b",
    },
    "E_levels.strength": {
        "weak": "\u5f31",
        "medium": "\u4e2d",
        "strong": "\u5f37",
    },
    "E_levels.status": {
        "holding": "\u5b88\u4f4f\u4e2d",
        "broken": "\u5df2\u8dcc\u7834\uff0f\u5df2\u7a81\u7834",
        "tested": "\u6e2c\u8a66\u4e2d",
    },
    "F_volume_state": {
        "expanding_on_rise": "\u4e0a\u6f32\u653e\u91cf",
        "contracting_on_rise": "\u4e0a\u6f32\u7e2e\u91cf",
        "expanding_on_drop": "\u4e0b\u8dcc\u653e\u91cf",
        "contracting_on_drop": "\u4e0b\u8dcc\u7e2e\u91cf",
        "volume_spike": "\u7206\u91cf",
        "normal": "\u91cf\u80fd\u6b63\u5e38",
        "dry_up": "\u91cf\u7e2e",
    },
    "G_ma_structure": {
        "bullish_alignment": "\u5747\u7dda\u591a\u982d\u6392\u5217",
        "bearish_alignment": "\u5747\u7dda\u7a7a\u982d\u6392\u5217",
        "mixed": "\u5747\u7dda\u6df7\u5408",
        "golden_cross": "\u5747\u7dda\u9ec3\u91d1\u4ea4\u53c9",
        "death_cross": "\u5747\u7dda\u6b7b\u4ea1\u4ea4\u53c9",
        "compression": "\u5747\u7dda\u7cfe\u7d50",
        "expanding": "\u5747\u7dda\u767c\u6563",
    },
    "H_macd_state": {
        "golden_cross": "MACD \u9ec3\u91d1\u4ea4\u53c9",
        "death_cross": "MACD \u6b7b\u4ea1\u4ea4\u53c9",
        "bullish_expanding": "\u591a\u65b9\u67f1\u72c0\u9ad4\u64f4\u5927",
        "bullish_contracting": "\u591a\u65b9\u67f1\u72c0\u9ad4\u7e2e\u5c0f",
        "bearish_expanding": "\u7a7a\u65b9\u67f1\u72c0\u9ad4\u64f4\u5927",
        "bearish_contracting": "\u7a7a\u65b9\u67f1\u72c0\u9ad4\u7e2e\u5c0f",
        "neutral": "\u4e2d\u6027",
    },
    "I_divergence_state": {
        "bullish_divergence": "\u504f\u591a\u80cc\u96e2",
        "bearish_divergence": "\u504f\u7a7a\u80cc\u96e2",
        "hidden_bullish_divergence": "\u96b1\u6027\u504f\u591a\u80cc\u96e2",
        "hidden_bearish_divergence": "\u96b1\u6027\u504f\u7a7a\u80cc\u96e2",
        "none": "\u7121",
    },
    "J_candlestick_pattern": {
        "bullish_engulfing": "\u591a\u982d\u541e\u565c",
        "bearish_engulfing": "\u7a7a\u982d\u541e\u565c",
        "hammer": "\u9318\u5b50\u7dda",
        "shooting_star": "\u5c04\u64ca\u4e4b\u661f",
        "doji": "\u5341\u5b57\u7dda",
        "long_bullish_candle": "\u9577\u7d05K",
        "long_bearish_candle": "\u9577\u9ed1K",
        "inside_bar": "\u5167\u5305\u7dda",
        "none": "\u7121\u660e\u78ba\u578b\u614b",
    },
    "K_trade_action": {
        "buy_pullback": "\u7b49\u56de\u6a94\u8cb7\u9032",
        "buy_breakout": "\u7b49\u7a81\u7834\u8cb7\u9032",
        "hold": "\u6301\u6709",
        "wait": "\u89c0\u671b",
        "reduce": "\u6e1b\u78bc",
        "sell": "\u8ce3\u51fa",
        "avoid": "\u907f\u958b",
    },
    "L_price_volume_divergence": {
        "bearish_volume_divergence": "\u504f\u7a7a\u50f9\u91cf\u80cc\u96e2",
        "bullish_volume_divergence": "\u504f\u591a\u50f9\u91cf\u80cc\u96e2",
        "price_volume_confirmed": "\u50f9\u91cf\u914d\u5408\u78ba\u8a8d",
        "inconclusive": "\u8a0a\u865f\u4e0d\u660e",
        "none": "\u7121",
    },
}


def _coerce_float(value: object) -> float:
    if pd.isna(value):
        return float("nan")
    try:
        return float(value)
    except (TypeError, ValueError):
        return float("nan")


def _coerce_int(value: object, default: int = 0) -> int:
    if pd.isna(value):
        return default
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return default


def _coerce_str(value: object, default: str = "n/a") -> str:
    if pd.isna(value):
        return default
    text = str(value).strip()
    return text if text else default


def _coerce_bool(value: object, default: bool = False) -> bool:
    if pd.isna(value):
        return default
    if isinstance(value, bool):
        return value
    text = str(value).strip().lower()
    if text in {"true", "1", "yes", "y"}:
        return True
    if text in {"false", "0", "no", "n"}:
        return False
    return bool(value)


def _load_snapshot_row(asset_key: str) -> pd.Series | None:
    path = ac.get_monitor_snapshot_path(asset_key)
    if not path.exists():
        return None
    frame = pd.read_csv(path, sep="\t")
    if frame.empty:
        return None
    return frame.iloc[0]


def _load_technical_reading(asset_key: str) -> dict[str, object] | None:
    path = ac.get_technical_reading_json_path(asset_key)
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def _technical_label(reading: dict[str, object] | None, key: str) -> str:
    if not reading:
        return "n/a"
    technical = reading.get("technical_reading", {})
    if isinstance(technical, dict):
        value = technical.get(key)
        if value is not None:
            enum_value = str(value).strip()
            mapped = TECHNICAL_ENUM_ZH.get(key, {}).get(enum_value)
            if mapped:
                return mapped
            return enum_value
    return "n/a"


def _technical_value(reading: dict[str, object] | None, key: str) -> str:
    if not reading:
        return ""
    technical = reading.get("technical_reading", {})
    if isinstance(technical, dict):
        value = technical.get(key)
        if value is not None:
            return str(value).strip()
    return ""


def _technical_levels(reading: dict[str, object] | None) -> list[dict[str, object]]:
    if not reading:
        return []
    technical = reading.get("technical_reading", {})
    if isinstance(technical, dict):
        levels = technical.get("E_levels")
        if isinstance(levels, list):
            return [level for level in levels if isinstance(level, dict)]
    return []


def _key_level_text(reading: dict[str, object] | None) -> str:
    levels = _technical_levels(reading)
    if not levels:
        return "n/a"
    resistances = [level for level in levels if str(level.get("type")) == "resistance"]
    supports = [level for level in levels if str(level.get("type")) == "support"]
    preferred = resistances[0] if resistances else supports[-1]
    level_type = "壓力" if str(preferred.get("type")) == "resistance" else "支撐"
    level_value = preferred.get("level")
    if isinstance(level_value, (int, float)):
        return f"{level_type} {float(level_value):.0f}"
    return level_type


def _technical_summary(trend_zh: str, rsi_zh: str, action_zh: str, volume_zh: str) -> str:
    if trend_zh == "\u591a\u982d" and rsi_zh in {"\u904e\u71b1", "\u504f\u5f37"} and action_zh == "\u7b49\u56de\u6a94\u8cb7\u9032":
        return "\u591a\u982d\u504f\u71b1\uff0c\u7b49\u56de\u6a94"
    if trend_zh == "\u591a\u982d" and action_zh == "\u7b49\u7a81\u7834\u8cb7\u9032":
        return "\u591a\u982d\u504f\u5f37\uff0c\u53ef\u7b49\u7a81\u7834"
    if trend_zh in {"\u7a7a\u982d", "\u7a7a\u982d\u56de\u6a94"} and action_zh in {"\u89c0\u671b", "\u907f\u958b"}:
        return "\u7a7a\u982d\u504f\u5f31\uff0c\u5148\u89c0\u671b"
    if action_zh == "\u89c0\u671b":
        return f"{trend_zh}\uff0c\u5148\u89c0\u671b"
    if action_zh == "\u6301\u6709":
        return f"{trend_zh}\uff0c\u53ef\u7e7c\u7e8c\u6301\u6709"
    if volume_zh != "n/a":
        return f"{trend_zh} / {rsi_zh} / {volume_zh}"
    return f"{trend_zh} / {rsi_zh} / {action_zh}"



def _chip_class(value: str, group: str) -> str:
    if group == "trend":
        return "chip-green" if value in {"bullish", "bullish_rebound"} else "chip-red" if value in {"bearish", "bearish_pullback"} else "chip-sand"
    if group == "rsi":
        return "chip-red" if value == "overbought" else "chip-blue" if value == "oversold" else "chip-amber" if value in {"strong", "weak"} else "chip-sand"
    if group == "volume":
        return "chip-sand"
    if group == "action":
        if value == "buy_breakout":
            return "chip-blue"
        if value == "buy_pullback":
            return "chip-amber"
        if value == "hold":
            return "chip-green"
        if value in {"wait", "avoid", "sell", "reduce"}:
            return "chip-red"
        return "chip-sand"
    return "chip-sand"


def _enrich_board_row(row: dict[str, object]) -> dict[str, object]:
    asset_key = str(row["asset_key"])
    reading = _load_technical_reading(asset_key)
    trend = _technical_value(reading, "A_trend")
    rsi = _technical_value(reading, "C_rsi_state")
    volume = _technical_value(reading, "F_volume_state")
    action = _technical_value(reading, "K_trade_action")
    trend_zh = _technical_label(reading, "A_trend")
    rsi_zh = _technical_label(reading, "C_rsi_state")
    volume_zh = _technical_label(reading, "F_volume_state")
    action_zh = _technical_label(reading, "K_trade_action")
    row["technical_trend"] = trend
    row["technical_trend_zh"] = trend_zh
    row["technical_rsi"] = rsi
    row["technical_rsi_zh"] = rsi_zh
    row["technical_volume"] = volume
    row["technical_volume_zh"] = volume_zh
    row["technical_action"] = action
    row["technical_action_zh"] = action_zh
    row["technical_summary"] = _technical_summary(trend_zh, rsi_zh, action_zh, volume_zh) if reading else "n/a"
    row["technical_key_level"] = _key_level_text(reading)
    row["detail_reading"] = reading or {}
    return row


def _key_level_text(reading: dict[str, object] | None) -> str:
    levels = _technical_levels(reading)
    if not levels:
        return "n/a"
    resistances = [level for level in levels if str(level.get("type")) == "resistance"]
    supports = [level for level in levels if str(level.get("type")) == "support"]
    preferred = resistances[0] if resistances else supports[-1]
    level_type = "Resistance" if str(preferred.get("type")) == "resistance" else "Support"
    level_value = preferred.get("level")
    if isinstance(level_value, (int, float)):
        return f"{level_type} {float(level_value):.0f}"
    return level_type


def _technical_summary(trend_zh: str, rsi_zh: str, action_zh: str, volume_zh: str) -> str:
    if trend_zh == "\u591a\u982d" and rsi_zh in {"\u904e\u71b1", "\u504f\u5f37"} and action_zh == "\u7b49\u56de\u6a94\u8cb7\u9032":
        return "\u591a\u982d\u504f\u71b1\uff0c\u7b49\u56de\u6a94"
    if trend_zh == "\u591a\u982d" and action_zh == "\u7b49\u7a81\u7834\u8cb7\u9032":
        return "\u591a\u982d\u504f\u5f37\uff0c\u53ef\u7b49\u7a81\u7834"
    if trend_zh in {"\u7a7a\u982d", "\u7a7a\u982d\u56de\u6a94"} and action_zh in {"\u89c0\u671b", "\u907f\u958b"}:
        return "\u7a7a\u982d\u504f\u5f31\uff0c\u5148\u89c0\u671b"
    if action_zh == "\u89c0\u671b":
        return f"{trend_zh}\uff0c\u5148\u89c0\u671b"
    if action_zh == "\u6301\u6709":
        return f"{trend_zh}\uff0c\u53ef\u7e7c\u7e8c\u6301\u6709"
    if volume_zh != "n/a":
        return f"{trend_zh} / {rsi_zh} / {volume_zh}"
    return f"{trend_zh} / {rsi_zh} / {action_zh}"


def _load_followup_rows(asset_key: str) -> tuple[pd.Series | None, pd.Series | None, int | None]:
    for round_num in FOLLOWUP_ROUNDS:
        operator_path = ac.get_asset_dir(asset_key) / f"followup_round{round_num}_operator_summary.tsv"
        validation_path = ac.get_asset_dir(asset_key) / f"followup_round{round_num}_validation_summary.tsv"
        operator_row: pd.Series | None = None
        validation_row: pd.Series | None = None
        if operator_path.exists():
            frame = pd.read_csv(operator_path, sep="\t")
            if not frame.empty:
                sort_column = "avg_return" if "avg_return" in frame.columns else "latest_score" if "latest_score" in frame.columns else None
                if sort_column is not None:
                    frame = frame.sort_values(sort_column, ascending=False, na_position="last")
                operator_row = frame.iloc[0]
        if validation_path.exists():
            frame = pd.read_csv(validation_path, sep="\t")
            if not frame.empty:
                score_column = f"round{round_num}_score"
                if score_column in frame.columns:
                    frame = frame.sort_values(score_column, ascending=False, na_position="last")
                validation_row = frame.iloc[0]
                if operator_path.exists():
                    operator_frame = pd.read_csv(operator_path, sep="\t")
                    if not operator_frame.empty and "model_name" in operator_frame.columns and "best_rule_name" in operator_frame.columns:
                        matches = operator_frame.loc[
                            (operator_frame["model_name"] == validation_row.get("model_name"))
                            & (operator_frame["best_rule_name"] == validation_row.get("best_rule_name"))
                        ]
                        if not matches.empty:
                            operator_row = matches.iloc[0]
        if operator_row is not None or validation_row is not None:
            return operator_row, validation_row, round_num
    return None, None, None


def _build_research_action_note(followup_round: int | None) -> str:
    if followup_round == 4:
        return "Benchmark-aware round-four follow-up candidate."
    if followup_round == 3:
        return "Round-three follow-up candidate pending benchmark-aware completion."
    if followup_round == 2:
        return "Round-two follow-up candidate awaiting deeper follow-up."
    return "Priority research candidate."


def has_real_chart(asset_key: str) -> bool:
    if ac.uses_regression_chart(asset_key):
        return ac.get_regression_recent_chart_path(asset_key).exists()
    return ac.get_chart_output_path(asset_key).exists()


def load_operating_board() -> pd.DataFrame:
    frames: list[pd.DataFrame] = []
    for key in ac.MONITOR_BOARD_ASSET_KEYS:
        if not has_real_chart(key):
            continue
        path = ac.get_monitor_snapshot_path(key)
        if not path.exists():
            continue
        frame = pd.read_csv(path, sep="\t")
        if frame.empty:
            continue
        frame["card_family"] = "operating"
        frame["sort_priority"] = frame["action"].map(lambda value: ACTION_PRIORITY.get(str(value), 99))
        frame["chart_href"] = ac.get_monitor_card_chart_path(key).relative_to(ac.REPO_DIR).as_posix()
        frame["display_latest_date"] = load_display_latest_date(key)
        frame["signal_color"] = load_signal_color(key)
        frame = pd.DataFrame([_enrich_board_row(cast(dict[str, object], row.to_dict())) for _, row in frame.iterrows()])
        frames.append(frame)
    return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()


def load_priority_research_board() -> pd.DataFrame:
    records: list[dict[str, object]] = []
    for key in ac.MONITOR_PRIORITY_RESEARCH_ASSET_KEYS:
        if not has_real_chart(key):
            continue
        operator_row, validation_row, followup_round = _load_followup_rows(key)
        snapshot_row = _load_snapshot_row(key)
        base_row: pd.Series | None = operator_row if operator_row is not None else validation_row if validation_row is not None else snapshot_row
        if base_row is None:
            base_row = pd.Series(dtype="object")
        score_row = validation_row if validation_row is not None else operator_row
        score_label = f"round{followup_round}_score" if followup_round is not None else "research_score"
        research_score = _coerce_float(score_row.get(score_label)) if score_row is not None else float("nan")
        if score_row is not None and pd.isna(research_score):
            for fallback_label in ("round4_score", "round3_score", "round2_score", "latest_score"):
                research_score = _coerce_float(score_row.get(fallback_label))
                if not pd.isna(research_score):
                    score_label = fallback_label
                    break
        if pd.isna(research_score) and operator_row is not None:
            research_score = _coerce_float(operator_row.get("latest_score"))
            if not pd.isna(research_score):
                score_label = "latest_score"
        latest_date = _coerce_str(base_row.get("latest_date"))
        display_latest_date = latest_date if latest_date != "n/a" else load_display_latest_date(key)
        latest_value = _coerce_float(operator_row.get("latest_score")) if operator_row is not None else float("nan")
        if pd.isna(latest_value):
            latest_value = _coerce_float(score_row.get(score_label)) if score_row is not None else _coerce_float(base_row.get("latest_value"))
        research_rule = _coerce_str(base_row.get("best_rule_name"))
        if research_rule == "n/a":
            research_rule = _coerce_str(base_row.get("preferred_line"))
        preferred_line = _coerce_str(base_row.get("model_name"), research_rule)
        record = {
            "asset_key": key,
            "symbol": ac.get_asset_symbol(key),
            "preferred_line": preferred_line,
            "lane_type": "priority_research",
            "role": "research",
            "status": "benchmark_aware_followup",
            "action": "priority_research",
            "recent_selected_count": _coerce_int(base_row.get("recent_selected_count")),
            "latest_date": latest_date,
            "latest_value": latest_value,
            "latest_selected": _coerce_bool(base_row.get("latest_selected")),
            "cutoff": _coerce_float(base_row.get("cutoff")),
            "last_selected_date": base_row.get("last_selected_date") if not pd.isna(base_row.get("last_selected_date")) else pd.NA,
            "days_since_last_selected": _coerce_float(base_row.get("days_since_last_selected")),
            "action_note": _build_research_action_note(followup_round),
            "chart_href": ac.get_monitor_card_chart_path(key).relative_to(ac.REPO_DIR).as_posix(),
            "display_latest_date": display_latest_date,
            "signal_color": PRIORITY_RESEARCH_SIGNAL_COLOR,
            "card_family": "priority_research",
            "research_score": research_score,
            "research_score_label": score_label,
            "research_rule": research_rule,
            "research_avg_return": _coerce_float(base_row.get("avg_return")),
            "research_trade_count": _coerce_int(base_row.get("selected_count"), _coerce_int(base_row.get("recent_selected_count"))),
        }
        records.append(_enrich_board_row(record))
    return pd.DataFrame.from_records(records)


def load_board() -> pd.DataFrame:
    operating = load_operating_board()
    research = load_priority_research_board()
    board = pd.concat([operating, research], ignore_index=True, sort=False)
    if "research_score" not in board.columns:
        board["research_score"] = float("nan")
    board["sort_priority"] = board["action"].map(lambda value: MIXED_ACTION_PRIORITY.get(str(value), 99))
    board["research_sort_score"] = board["research_score"].fillna(-1.0)
    return board.sort_values(["sort_priority", "research_sort_score", "symbol"], ascending=[True, False, True]).drop(
        columns=["sort_priority", "research_sort_score"]
    )


def load_display_latest_date(asset_key: str) -> str:
    if ac.uses_regression_chart(asset_key):
        path = ac.get_regression_recent_output_path(asset_key)
        if path.exists():
            frame = pd.read_csv(path, sep="\t")
            if not frame.empty:
                return str(pd.to_datetime(frame.iloc[-1]["date"]).strftime("%Y-%m-%d"))
    raw_path = ac.get_raw_data_path(asset_key)
    if raw_path.exists():
        frame = pd.read_csv(raw_path)
        if not frame.empty:
            return str(pd.to_datetime(frame.iloc[-1]["date"]).strftime("%Y-%m-%d"))
    return "n/a"


def card_color(action: str) -> str:
    if action == "selected_now":
        return "#2563eb"
    if action == "watchlist_wait":
        return "#0ea5e9"
    if action == "inactive_wait":
        return "#cbd5e1"
    if action == "reference_only":
        return "#94a3b8"
    if action == "research_only":
        return "#64748b"
    return "#475569"


def load_signal_color(asset_key: str) -> str:
    if ac.uses_regression_chart(asset_key):
        path = ac.get_regression_recent_output_path(asset_key)
        if not path.exists():
            return "#cbd5e1"
        frame = pd.read_csv(path, sep="\t")
        if frame.empty:
            return "#cbd5e1"
        row = frame.iloc[-1]
        if _coerce_bool(row.get("selected")):
            return "#065f46"
        percentile = _coerce_float(row.get("prediction_percentile"))
        bucket_pct = _coerce_float(row.get("bucket_pct"))
        if pd.isna(percentile) or pd.isna(bucket_pct):
            return "#cbd5e1"
        if percentile <= bucket_pct / 100.0 * 2:
            return "#f59e0b"
        if percentile <= 0.35:
            return "#fde68a"
        return "#f8d9a0"

    path = ac.get_latest_prediction_path(asset_key)
    if not path.exists():
        return "#9ca3af"
    payload = json.loads(path.read_text(encoding="utf-8"))
    signal = str(payload.get("signal_summary", {}).get("signal", "no_entry"))
    return {
        "no_entry": "#9ca3af",
        "weak_bullish": "#fde68a",
        "bullish": "#f59e0b",
        "strong_bullish": "#16a34a",
        "very_strong_bullish": "#065f46",
    }.get(signal, "#9ca3af")


def normalize_role(row: pd.Series) -> str:
    raw_tokens = " ".join(
        [
            str(row.get("role", "")),
            str(row.get("lane_type", "")),
            str(row.get("status", "")),
        ]
    ).lower()
    tokens = {
        token
        for token in re.split(r"[\s_/-]+", raw_tokens)
        if token
    }
    if "reference" in tokens:
        return "reference"
    if "research" in tokens:
        return "research"
    return "primary"


def role_color(role: str) -> str:
    if role == "primary":
        return "#2563eb"
    if role == "reference":
        return "#94a3b8"
    if role == "research":
        return "#64748b"
    return "#475569"


def render_today_card(row: pd.Series) -> str:
    if str(row.get("card_family", "operating")) == "priority_research":
        return render_priority_research_card(row)
    color = str(row["signal_color"])
    chart_href = escape(str(row["chart_href"]))
    latest = "n/a" if pd.isna(row["latest_value"]) else f"{float(row['latest_value']):.4f}"
    cutoff = "n/a" if pd.isna(row["cutoff"]) else f"{float(row['cutoff']):.4f}"
    last_date = "n/a" if pd.isna(row["last_selected_date"]) else str(row["last_selected_date"])
    days = "n/a" if pd.isna(row["days_since_last_selected"]) else str(int(float(row["days_since_last_selected"])))
    latest_date = str(row["display_latest_date"])
    action = str(row["action"])
    if action == "selected_now":
        last_date = latest_date
        days = "0"
    recent_count = int(row["recent_selected_count"])
    return f"""
    <a class="spotlight-card" href="{chart_href}" style="--accent:{color}">
      <div class="spotlight-date">{escape(latest_date)}</div>
      <div class="spotlight-symbol" style="color:{color}">{escape(str(row["symbol"]))}</div>
      <div class="spotlight-line">{escape(str(row["preferred_line"]))}</div>
      <div class="spotlight-metric">today_status={escape(action)}</div>
      <div class="spotlight-metric">recent_selected={recent_count}/60</div>
      <div class="spotlight-metric">latest={latest}</div>
      <div class="spotlight-metric">cutoff={cutoff}</div>
      <div class="spotlight-metric">last_selected={escape(last_date)}</div>
      <div class="spotlight-metric">days_since_last={escape(days)}</div>
      <div class="spotlight-note">{escape(str(row["action_note"]))}</div>
    </a>
    """


def render_priority_research_card(row: pd.Series) -> str:
    color = str(row["signal_color"])
    chart_href = escape(str(row["chart_href"]))
    latest = "n/a" if pd.isna(row["latest_value"]) else f"{float(row['latest_value']):.4f}"
    cutoff = "n/a" if pd.isna(row["cutoff"]) else f"{float(row['cutoff']):.4f}"
    last_date = "n/a" if pd.isna(row["last_selected_date"]) else str(row["last_selected_date"])
    days = "n/a" if pd.isna(row["days_since_last_selected"]) else str(int(float(row["days_since_last_selected"])))
    latest_date = str(row["display_latest_date"])
    score_label = str(row.get("research_score_label", "research_score"))
    research_score = "n/a" if pd.isna(row["research_score"]) else f"{float(row['research_score']):.4f}"
    research_avg_return = "n/a" if pd.isna(row["research_avg_return"]) else f"{float(row['research_avg_return']):.4f}"
    research_trade_count = int(row["research_trade_count"])
    return f"""
    <a class="spotlight-card" href="{chart_href}" style="--accent:{color}">
      <div class="spotlight-date">{escape(latest_date)}</div>
      <div class="spotlight-symbol" style="color:{color}">{escape(str(row["symbol"]))}</div>
      <div class="spotlight-line">{escape(str(row["preferred_line"]))}</div>
      <div class="spotlight-metric">today_status={escape(str(row["action"]))}</div>
      <div class="spotlight-metric">{escape(score_label)}={escape(research_score)}</div>
      <div class="spotlight-metric">best_rule={escape(str(row["research_rule"]))}</div>
      <div class="spotlight-metric">avg_return={escape(research_avg_return)}</div>
      <div class="spotlight-metric">trade_count={research_trade_count}</div>
      <div class="spotlight-metric">latest={latest}</div>
      <div class="spotlight-metric">cutoff={cutoff}</div>
      <div class="spotlight-metric">last_selected={escape(last_date)}</div>
      <div class="spotlight-metric">days_since_last={escape(days)}</div>
      <div class="spotlight-note">{escape(str(row["action_note"]))}</div>
    </a>
    """


def render_role_card(row: pd.Series) -> str:
    role = normalize_role(row)
    color = role_color(role)
    chart_href = escape(str(row["chart_href"]))
    return f"""
    <a class="role-card" href="{chart_href}" style="--accent:{color}">
      <div class="role-symbol">{escape(str(row["symbol"]))}</div>
      <div class="role-badge">{escape(role)}</div>
      <div class="role-line">{escape(str(row["preferred_line"]))}</div>
      <div class="role-note">{escape(str(row["action_note"]))}</div>
    </a>
    """


def render_chip(label: str, chip_class: str) -> str:
    return f'<span class="chip {chip_class}">{escape(label)}</span>'



def render_table_row(row: pd.Series) -> str:
    status_label = str(row["action"]).replace("_", " ")
    status_chip = render_chip(
        status_label.title(),
        "chip-blue"
        if str(row["action"]) == "selected_now"
        else "chip-amber"
        if str(row["action"]) in {"watchlist_wait", "watchlist_blocked"}
        else "chip-sand"
        if str(row["action"]) == "reference_only"
        else "chip-red",
    )
    trend_chip = render_chip(str(row.get("technical_trend_zh", "n/a")), _chip_class(str(row.get("technical_trend", "")), "trend"))
    rsi_chip = render_chip(str(row.get("technical_rsi_zh", "n/a")), _chip_class(str(row.get("technical_rsi", "")), "rsi"))
    volume_chip = render_chip(str(row.get("technical_volume_zh", "n/a")), _chip_class(str(row.get("technical_volume", "")), "volume"))
    action_chip = render_chip(str(row.get("technical_action_zh", "n/a")), _chip_class(str(row.get("technical_action", "")), "action"))
    latest_value = "n/a" if pd.isna(row.get("latest_value")) else f"{float(row['latest_value']):.4f}"
    symbol_color = escape(str(row.get("signal_color", "#9ca3af")))
    asset_key = escape(str(row.get("asset_key", "")))
    chart_href = escape(str(row.get("chart_href", "#")))
    return f"""
      <tr>
        <td>
          <div class="symbol">
            <a class="symbol-link" href="{chart_href}"><strong style="color:{symbol_color}">{escape(str(row["symbol"]))}</strong></a>
            <div class="mini">{escape(str(row["display_latest_date"]))} · {escape(str(row["preferred_line"]))}</div>
            <div class="mini">latest {escape(latest_value)}</div>
          </div>
        </td>
        <td><button class="detail-link" type="button" data-target="detail-{asset_key}">view</button></td>
        <td>{status_chip}</td>
        <td>{trend_chip}</td>
        <td>{rsi_chip}</td>
        <td>{volume_chip}</td>
        <td>{action_chip}</td>
        <td class="summary">{escape(str(row.get("technical_summary", "n/a")))}</td>
        <td><div class="level">{escape(str(row.get("technical_key_level", "n/a")))}</div></td>
      </tr>
    """


def render_detail_metric(label: str, value: str) -> str:
    return f"""
          <div class="detail-metric">
            <div class="metric-label">{escape(label)}</div>
            <div class="metric-value">{escape(value or "n/a")}</div>
          </div>
    """


def render_levels_detail(reading: dict[str, Any]) -> str:
    levels = _technical_levels(reading)
    if not levels:
        return render_detail_metric("E Levels", "n/a")
    items: list[str] = []
    for level in levels:
        level_type = TECHNICAL_ENUM_ZH["E_levels.type"].get(str(level.get("type", "")), str(level.get("type", "n/a")))
        strength = TECHNICAL_ENUM_ZH["E_levels.strength"].get(str(level.get("strength", "")), str(level.get("strength", "n/a")))
        status = TECHNICAL_ENUM_ZH["E_levels.status"].get(str(level.get("status", "")), str(level.get("status", "n/a")))
        level_value = level.get("level")
        value_text = f"{float(level_value):.2f}" if isinstance(level_value, (int, float)) else str(level_value or "n/a")
        items.append(f"<li><strong>{escape(level_type)}</strong> {escape(value_text)} <span>{escape(strength)} / {escape(status)}</span></li>")
    return f"""
          <div class="detail-metric detail-metric-levels">
            <div class="metric-label">E Levels</div>
            <ul class="level-list">
              {''.join(items)}
            </ul>
          </div>
    """


def render_detail_card(row: pd.Series) -> str:
    reading = cast(dict[str, Any], row.get("detail_reading", {}))
    latest_close = cast(dict[str, object], reading.get("supporting_metrics", {})).get("latest_close", "n/a")
    levels = str(row.get("technical_key_level", "n/a"))
    status_chip = render_chip(
        str(row.get("action", "n/a")).replace("_", " ").title(),
        "chip-blue" if str(row.get("action")) == "selected_now" else "chip-amber",
    )
    return f"""
      <aside class="detail-card">
        <div class="detail-header">
          <div>
            <div class="eyebrow">Detail Card</div>
            <div class="detail-symbol">{escape(str(row["symbol"]))}</div>
            <div class="detail-price">Close {escape(str(latest_close))} · {escape(str(row["display_latest_date"]))}</div>
          </div>
          {status_chip}
        </div>

        <div class="detail-summary">
          <strong>{escape(str(row["symbol"]))}</strong> · {escape(str(row.get("technical_summary", "n/a")))}
        </div>

        <div class="detail-grid">
          <div class="detail-box">
            <div class="label">A / C / K</div>
            <div class="value">{escape(str(row.get("technical_trend_zh", "n/a")))} · {escape(str(row.get("technical_rsi_zh", "n/a")))} · {escape(str(row.get("technical_action_zh", "n/a")))}</div>
          </div>
          <div class="detail-box">
            <div class="label">F / G / L</div>
            <div class="value">{escape(str(row.get("technical_volume_zh", "n/a")))} · {escape(_technical_label(reading, "G_ma_structure"))} · {escape(_technical_label(reading, "L_price_volume_divergence"))}</div>
          </div>
          <div class="detail-box">
            <div class="label">D / H / I</div>
            <div class="value">{escape(_technical_label(reading, "D_kd_state"))} · {escape(_technical_label(reading, "H_macd_state"))} · {escape(_technical_label(reading, "I_divergence_state"))}</div>
          </div>
          <div class="detail-box">
            <div class="label">Key Levels</div>
            <div class="value">{escape(levels)}</div>
          </div>
        </div>

        <ul class="detail-list">
          <li><strong>Action note:</strong> {escape(str(row.get("action_note", "n/a")))}</li>
          <li><strong>Pattern:</strong> {escape(_technical_label(reading, "J_candlestick_pattern"))}</li>
          <li><strong>Chart:</strong> <a href="{escape(str(row["chart_href"]))}">{escape(str(row["chart_href"]))}</a></li>
        </ul>
      </aside>
    """


def render_detail_metric(label: str, value: str) -> str:
    return f"""
          <div class="detail-metric">
            <div class="metric-label">{escape(label)}</div>
            <div class="metric-value">{escape(value or "n/a")}</div>
          </div>
    """


def render_levels_detail(reading: dict[str, Any]) -> str:
    levels = _technical_levels(reading)
    if not levels:
        return render_detail_metric("E Levels", "n/a")
    items: list[str] = []
    for level in levels:
        level_type = TECHNICAL_ENUM_ZH["E_levels.type"].get(str(level.get("type", "")), str(level.get("type", "n/a")))
        strength = TECHNICAL_ENUM_ZH["E_levels.strength"].get(str(level.get("strength", "")), str(level.get("strength", "n/a")))
        status = TECHNICAL_ENUM_ZH["E_levels.status"].get(str(level.get("status", "")), str(level.get("status", "n/a")))
        level_value = level.get("level")
        value_text = f"{float(level_value):.2f}" if isinstance(level_value, (int, float)) else str(level_value or "n/a")
        items.append(
            f"<li><strong>{escape(level_type)}</strong> {escape(value_text)} <span>{escape(strength)} / {escape(status)}</span></li>"
        )
    return f"""
          <div class="detail-metric detail-metric-levels">
            <div class="metric-label">E Levels</div>
            <ul class="level-list">
              {''.join(items)}
            </ul>
          </div>
    """


def render_detail_card(row: pd.Series) -> str:
    reading = cast(dict[str, Any], row.get("detail_reading", {}))
    latest_close = cast(dict[str, object], reading.get("supporting_metrics", {})).get("latest_close", "n/a")
    levels = str(row.get("technical_key_level", "n/a"))
    status_chip = render_chip(
        str(row.get("action", "n/a")).replace("_", " ").title(),
        "chip-blue" if str(row.get("action")) == "selected_now" else "chip-amber",
    )
    return f"""
      <aside class="detail-card">
        <div class="detail-header">
          <div>
            <div class="eyebrow">Detail Card</div>
            <div class="detail-symbol">{escape(str(row["symbol"]))}</div>
            <div class="detail-price">Close {escape(str(latest_close))} · {escape(str(row["display_latest_date"]))}</div>
          </div>
          {status_chip}
        </div>

        <div class="detail-summary">
          <strong>{escape(str(row["symbol"]))}</strong> · {escape(str(row.get("technical_summary", "n/a")))}
        </div>

        <div class="detail-grid">
          <div class="detail-box">
            <div class="label">A to E</div>
            {render_detail_metric("A Trend", str(row.get("technical_trend_zh", "n/a")))}
            {render_detail_metric("B Price vs MA", _technical_label(reading, "B_price_vs_ma"))}
            {render_detail_metric("C RSI", str(row.get("technical_rsi_zh", "n/a")))}
            {render_detail_metric("D KD", _technical_label(reading, "D_kd_state"))}
            {render_levels_detail(reading)}
          </div>
          <div class="detail-box">
            <div class="label">F to I</div>
            {render_detail_metric("F Volume", str(row.get("technical_volume_zh", "n/a")))}
            {render_detail_metric("G MA Structure", _technical_label(reading, "G_ma_structure"))}
            {render_detail_metric("H MACD", _technical_label(reading, "H_macd_state"))}
            {render_detail_metric("I Divergence", _technical_label(reading, "I_divergence_state"))}
          </div>
          <div class="detail-box">
            <div class="label">Action & Pattern</div>
            {render_detail_metric("K Trade Action", str(row.get("technical_action_zh", "n/a")))}
            {render_detail_metric("J Pattern", _technical_label(reading, "J_candlestick_pattern"))}
            {render_detail_metric("L Price Volume", _technical_label(reading, "L_price_volume_divergence"))}
          </div>
          <div class="detail-box">
            <div class="label">Key Levels</div>
            <div class="value">{escape(levels)}</div>
          </div>
        </div>

        <ul class="detail-list">
          <li><strong>Action note:</strong> {escape(str(row.get("action_note", "n/a")))}</li>
          <li><strong>Pattern:</strong> {escape(_technical_label(reading, "J_candlestick_pattern"))}</li>
          <li><strong>Chart:</strong> <a href="{escape(str(row["chart_href"]))}">{escape(str(row["chart_href"]))}</a></li>
        </ul>
      </aside>
    """


def render_detail_template(row: pd.Series) -> str:
    asset_key = escape(str(row.get("asset_key", "")))
    return f'<template id="detail-template-{asset_key}">{render_detail_card(row)}</template>'


def build_html(board: pd.DataFrame) -> str:
    counts = board["action"].value_counts().to_dict()
    summary = " | ".join(f"{key}={value}" for key, value in counts.items())
    board_rows = "\n".join(render_table_row(row) for _, row in board.iterrows())
    detail_row = board.iloc[0] if not board.empty else pd.Series(dtype="object")
    current_detail = render_detail_card(detail_row) if not board.empty else ""
    detail_templates = "\n".join(render_detail_template(row) for _, row in board.iterrows())
    selected_count = int(counts.get("selected_now", 0))
    watchlist_count = int(counts.get("watchlist_wait", 0) + counts.get("watchlist_blocked", 0))
    overbought_count = int((board["technical_rsi"] == "overbought").sum()) if "technical_rsi" in board.columns else 0
    pullback_count = int((board["technical_action"] == "buy_pullback").sum()) if "technical_action" in board.columns else 0
    return f"""<!DOCTYPE html>
<html lang="zh-Hant">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Monitor Board</title>
  <style>
    :root {{
      --bg: #f4efe6;
      --panel: rgba(255, 252, 246, 0.82);
      --line: #dfd2bc;
      --ink: #1c1917;
      --muted: #6b6459;
      --shadow: 0 24px 60px rgba(46, 38, 24, 0.12);
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      font-family: "Segoe UI", "Noto Sans TC", sans-serif;
      background:
        radial-gradient(circle at top left, rgba(255, 255, 255, 0.6), transparent 28%),
        linear-gradient(180deg, #f5f0e7 0%, #eee4d4 100%);
      color: var(--ink);
    }}
    a {{ color: inherit; }}
    .wrap {{
      max-width: 1500px;
      margin: 0 auto;
      padding: 28px;
    }}
    .hero {{
      display: grid;
      grid-template-columns: 1.3fr 0.9fr;
      gap: 18px;
      margin-bottom: 18px;
    }}
    .hero-card,
    .stats-card,
    .board-card,
    .detail-card {{
      background: var(--panel);
      backdrop-filter: blur(12px);
      border: 1px solid rgba(223, 210, 188, 0.85);
      border-radius: 24px;
      box-shadow: var(--shadow);
    }}
    .hero-card {{
      padding: 26px 28px;
      background: linear-gradient(135deg, rgba(255, 250, 240, 0.98), rgba(245, 232, 207, 0.92));
    }}
    .eyebrow {{
      display: inline-flex;
      align-items: center;
      gap: 8px;
      padding: 8px 12px;
      border-radius: 999px;
      background: rgba(28, 25, 23, 0.06);
      color: var(--muted);
      font-size: 13px;
      letter-spacing: 0.06em;
      text-transform: uppercase;
    }}
    h1 {{
      margin: 18px 0 10px;
      font-size: 40px;
      line-height: 1.02;
      letter-spacing: -0.03em;
    }}
    .hero-copy {{
      max-width: 66ch;
      font-size: 16px;
      line-height: 1.6;
      color: var(--muted);
    }}
    .mock-note {{
      margin-top: 18px;
      padding: 14px 16px;
      border-left: 4px solid #b7791f;
      border-radius: 14px;
      background: rgba(255, 248, 230, 0.9);
      font-size: 14px;
      color: #7c5b1b;
    }}
    .legend-row {{
      display: flex;
      flex-wrap: wrap;
      gap: 18px;
      margin-top: 18px;
      color: var(--ink);
      font-size: 14px;
      align-items: center;
    }}
    .legend-item {{
      display: inline-flex;
      align-items: center;
      gap: 10px;
    }}
    .legend-dot {{
      width: 28px;
      height: 28px;
      border-radius: 8px;
      display: inline-block;
    }}
    .stats-card {{
      padding: 22px;
      display: grid;
      gap: 12px;
      align-content: start;
    }}
    .stats-grid {{
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 10px;
    }}
    .stat {{
      padding: 14px;
      border-radius: 18px;
      background: rgba(255, 255, 255, 0.55);
      border: 1px solid rgba(223, 210, 188, 0.8);
    }}
    .stat-label {{
      color: var(--muted);
      font-size: 12px;
      text-transform: uppercase;
      letter-spacing: 0.08em;
      margin-bottom: 8px;
    }}
    .stat-value {{
      font-size: 26px;
      font-weight: 700;
    }}
    .detail-link {{
      color: #1d4ed8;
      background: transparent;
      border: 0;
      padding: 0;
      font: inherit;
      font-weight: 600;
      cursor: pointer;
    }}
    .detail-link:hover {{
      text-decoration: underline;
    }}
    .main {{
      display: grid;
      grid-template-columns: 1.6fr 0.9fr;
      gap: 18px;
    }}
    .board-card {{
      overflow-x: auto;
      overflow-y: hidden;
    }}
    .board-head {{
      display: flex;
      justify-content: space-between;
      align-items: flex-end;
      gap: 16px;
      padding: 22px 24px 16px;
      border-bottom: 1px solid rgba(223, 210, 188, 0.8);
    }}
    .board-title {{
      font-size: 24px;
      font-weight: 700;
      margin: 0 0 6px;
    }}
    .board-sub {{
      font-size: 14px;
      color: var(--muted);
      max-width: 70ch;
      line-height: 1.5;
    }}
    table {{
      width: 100%;
      border-collapse: collapse;
    }}
    thead th {{
      text-align: left;
      font-size: 12px;
      letter-spacing: 0.08em;
      text-transform: uppercase;
      color: var(--muted);
      padding: 14px 16px;
      background: rgba(244, 239, 230, 0.9);
      border-bottom: 1px solid rgba(223, 210, 188, 0.8);
      white-space: nowrap;
    }}
    tbody td {{
      padding: 16px;
      vertical-align: top;
      border-bottom: 1px solid rgba(223, 210, 188, 0.6);
      font-size: 14px;
    }}
    tbody tr:hover {{
      background: rgba(255, 250, 240, 0.72);
    }}
    .symbol {{
      display: flex;
      flex-direction: column;
      gap: 6px;
    }}
    .symbol-link {{
      display: inline-flex;
      width: fit-content;
      text-decoration: none;
    }}
    .symbol-link:hover strong {{
      text-decoration: underline;
      text-decoration-thickness: 2px;
      text-underline-offset: 4px;
    }}
    .symbol strong {{
      font-size: 22px;
      line-height: 1;
    }}
    .mini {{
      color: var(--muted);
      font-size: 12px;
      line-height: 1.4;
    }}
    .chip {{
      display: inline-flex;
      align-items: center;
      gap: 6px;
      padding: 7px 10px;
      border-radius: 999px;
      font-size: 12px;
      font-weight: 600;
      white-space: nowrap;
      border: 1px solid transparent;
    }}
    .chip-green {{ color: #14532d; background: #dcfce7; border-color: #86efac; }}
    .chip-amber {{ color: #92400e; background: #fef3c7; border-color: #fcd34d; }}
    .chip-red {{ color: #991b1b; background: #fee2e2; border-color: #fca5a5; }}
    .chip-blue {{ color: #1d4ed8; background: #dbeafe; border-color: #93c5fd; }}
    .chip-sand {{ color: #6b4f1d; background: #f6e8cf; border-color: #e8c787; }}
    .summary {{
      font-size: 14px;
      line-height: 1.55;
      color: #3f3a33;
    }}
    .level {{
      font-size: 14px;
      font-weight: 700;
    }}
    .detail-card {{
      padding: 24px;
      display: none;
      gap: 16px;
      align-content: start;
      background: linear-gradient(180deg, rgba(255, 252, 246, 0.98), rgba(247, 240, 228, 0.94));
    }}
    .detail-header {{
      display: flex;
      justify-content: space-between;
      align-items: center;
      gap: 12px;
    }}
    .detail-symbol {{
      font-size: 34px;
      font-weight: 800;
      letter-spacing: -0.04em;
    }}
    .detail-price {{
      color: var(--muted);
      font-size: 14px;
    }}
    .detail-summary {{
      padding: 14px 16px;
      border-radius: 18px;
      background: rgba(39, 103, 73, 0.08);
      border: 1px solid rgba(39, 103, 73, 0.14);
      line-height: 1.6;
      font-size: 15px;
    }}
    .detail-grid {{
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 10px;
    }}
    .detail-box {{
      padding: 14px;
      border-radius: 18px;
      background: rgba(255, 255, 255, 0.62);
      border: 1px solid rgba(223, 210, 188, 0.8);
    }}
    .detail-box .label {{
      color: var(--muted);
      font-size: 12px;
      text-transform: uppercase;
      letter-spacing: 0.08em;
      margin-bottom: 8px;
    }}
    .detail-box .value {{
      font-size: 16px;
      font-weight: 700;
      line-height: 1.4;
    }}
    .detail-metric {{
      padding-top: 10px;
      margin-top: 10px;
      border-top: 1px solid rgba(223, 210, 188, 0.65);
    }}
    .detail-metric:first-of-type {{
      margin-top: 0;
      padding-top: 0;
      border-top: 0;
    }}
    .metric-label {{
      color: var(--muted);
      font-size: 11px;
      text-transform: uppercase;
      letter-spacing: 0.08em;
      margin-bottom: 6px;
    }}
    .metric-value {{
      font-size: 15px;
      font-weight: 700;
      line-height: 1.45;
    }}
    .level-list {{
      margin: 0;
      padding-left: 18px;
      display: grid;
      gap: 6px;
    }}
    .level-list li {{
      color: var(--ink);
      font-size: 14px;
      line-height: 1.45;
    }}
    .level-list span {{
      color: var(--muted);
    }}
    .detail-list {{
      display: grid;
      gap: 8px;
      margin: 0;
      padding: 0;
      list-style: none;
    }}
    .detail-list li {{
      padding: 12px 14px;
      border-radius: 14px;
      background: rgba(255, 255, 255, 0.65);
      border: 1px solid rgba(223, 210, 188, 0.8);
      line-height: 1.5;
      font-size: 14px;
    }}
    .detail-panel {{
      position: relative;
      min-height: 640px;
    }}
    .detail-card {{
      display: grid;
    }}
    @media (max-width: 1180px) {{
      .hero, .main {{ grid-template-columns: 1fr; }}
      
    }}
    @media (max-width: 860px) {{
      .wrap {{ padding: 18px; }}
      h1 {{ font-size: 32px; }}
      .board-card {{ overflow-x: auto; }}
      table {{ min-width: 980px; }}
          }}
  </style>
</head>
<body>
  <div class="wrap">
    <section class="hero">
      <div class="hero-card">
        <div class="eyebrow">Monitor Board · Technical Summary</div>
        <h1>Monitor Board with Technical Overlay</h1>
        <div class="hero-copy">
          Use the main table for the quick scan. Use the right panel for the currently selected asset detail view.
        </div>
        <div class="mock-note">
          Symbol color follows the signal state. Click `view` to switch the right-side detail panel.
        </div>
        <div class="legend-row">
          <span class="legend-item"><span class="legend-dot" style="background:#9ca3af"></span>no_entry</span>
          <span class="legend-item"><span class="legend-dot" style="background:#fde68a"></span>weak_bullish</span>
          <span class="legend-item"><span class="legend-dot" style="background:#f59e0b"></span>bullish</span>
          <span class="legend-item"><span class="legend-dot" style="background:#16a34a"></span>strong_bullish</span>
          <span class="legend-item"><span class="legend-dot" style="background:#065f46"></span>very_strong_bullish / selected</span>
        </div>
      </div>
      <div class="stats-card">
        <div class="stats-grid">
          <div class="stat"><div class="stat-label">Selected</div><div class="stat-value">{selected_count}</div></div>
          <div class="stat"><div class="stat-label">Watchlist</div><div class="stat-value">{watchlist_count}</div></div>
          <div class="stat"><div class="stat-label">Overbought</div><div class="stat-value">{overbought_count}</div></div>
          <div class="stat"><div class="stat-label">Pullback Buys</div><div class="stat-value">{pullback_count}</div></div>
        </div>
        <div class="stat">
          <div class="stat-label">Board Summary</div>
          <div class="summary">{escape(summary)}</div>
        </div>
      </div>
    </section>


    <section class="main">
      <div class="board-card">
        <div class="board-head">
          <div>
            <div class="board-title">Board</div>
            <div class="board-sub">technical summary 放在主表快速掃描，完整的 A~L 判讀與關鍵價位則放在右側 detail panel。</div>
          </div>
        </div>
        <table>
          <thead>
            <tr>
              <th>Asset</th>
              <th>View</th>
              <th>Status</th>
              <th>Trend</th>
              <th>RSI</th>
              <th>Volume</th>
              <th>Action</th>
              <th>Technical Summary</th>
              <th>Key Level</th>
            </tr>
          </thead>
          <tbody>{board_rows}</tbody>
        </table>
      </div>
      <div class="detail-panel">
        <div id="detail-current">
          {current_detail}
        </div>
        <div style="display:none">
          {detail_templates}
        </div>
      </div>
    </section>
  </div>
  <script>
    (() => {{
      const buttons = Array.from(document.querySelectorAll('.detail-link[data-target]'));
      const current = document.getElementById('detail-current');
      const activate = (targetId) => {{
        const template = document.getElementById(`detail-template-${{targetId.replace('detail-', '')}}`);
        if (!template || !current) return;
        current.innerHTML = template.innerHTML;
      }};
      buttons.forEach((button) => {{
        button.addEventListener('click', () => activate(button.dataset.target));
      }});
    }})();
  </script>
</body>
</html>"""



def main() -> None:
    board = load_board()
    board.to_csv(ac.get_monitor_board_path(), sep="\t", index=False)
    ac.get_monitor_board_chart_path().write_text(build_html(board), encoding="utf-8")
    print(
        json.dumps(
            {
                "output_path": str(ac.get_monitor_board_path()),
                "html_path": str(ac.get_monitor_board_chart_path()),
                "rows": len(board),
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
