"""
Render a shared-renderer HTML chart for recent regression ranking signals.
"""

from __future__ import annotations

import json
from typing import cast

import pandas as pd

import asset_config as ac
import signal_chart_renderer

INPUT_PATH = str(ac.get_regression_recent_output_path())
OUTPUT_PATH = str(ac.get_regression_recent_chart_path())
REGRESSION_COLORS = {
    "selected": "#065f46",
    "watch": "#f59e0b",
    "idle": "#f8d9a0",
}


def load_rows() -> list[dict[str, object]]:
    frame = pd.read_csv(INPUT_PATH, sep="\t", parse_dates=["date"])
    rows: list[dict[str, object]] = []
    for _, row in frame.iterrows():
        row_date = cast(pd.Timestamp, row["date"])
        rows.append(
            {
                "date": row_date.strftime("%Y-%m-%d"),
                "close": round(float(row["close"]), 2),
                "predicted_return": round(float(row["predicted_return"]), 4),
                "future_return_60": round(float(row["future_return_60"]), 4),
                "prediction_percentile": round(float(row["prediction_percentile"]), 4),
                "bucket_direction": str(row["bucket_direction"]),
                "bucket_pct": float(row["bucket_pct"]),
                "bucket_cutoff": round(float(row["bucket_cutoff"]), 4),
                "selected": bool(row["selected"]),
            }
        )
    return rows


def _as_float(value: object, default: float = 0.0) -> float:
    if value is None:
        return default
    if isinstance(value, (int, float)):
        return float(value)
    try:
        return float(str(value))
    except ValueError:
        return default


def _normalize_regression_render_state(row: dict[str, object]) -> str:
    if bool(row.get("selected")):
        return "selected"

    percentile = _as_float(row.get("prediction_percentile"))
    bucket_pct = _as_float(row.get("bucket_pct"))
    bucket_ratio = bucket_pct / 100.0
    bucket_direction = str(row.get("bucket_direction", "bottom")).strip().lower()

    if bucket_direction == "upper":
        watch_cutoff = max(0.0, 1.0 - (bucket_ratio * 2.0))
        return "watch" if percentile >= watch_cutoff else "idle"

    watch_cutoff = min(1.0, bucket_ratio * 2.0)
    return "watch" if percentile <= watch_cutoff else "idle"


def normalize_regression_rows(rows: list[dict[str, object]]) -> list[dict[str, object]]:
    normalized_rows: list[dict[str, object]] = []
    for row in rows:
        normalized_row = dict(row)
        normalized_row["render_state"] = _normalize_regression_render_state(normalized_row)
        normalized_rows.append(normalized_row)
    return normalized_rows


def build_regression_recent_payload(rows: list[dict[str, object]], meta: dict[str, object]) -> dict[str, object]:
    config = ac.load_asset_config()
    algorithm_name = str(config.get("model_family", "ridge_regression"))
    label_mode = str(config.get("label_mode", "future_return_60"))
    symbol = ac.get_asset_symbol()
    normalized_rows = normalize_regression_rows(rows)
    latest = normalized_rows[-1] if normalized_rows else None

    latest_text = (
        f"最近資料 {latest['date']} | 預測報酬={latest['predicted_return']:.4f} | selected={'yes' if latest['selected'] else 'no'}"
        if latest
        else "No rows"
    )

    if latest:
        reference_rule = f"{latest['bucket_direction']}_{latest['bucket_pct']:g}pct_bucket"
    else:
        reference_rule = "regression_bucket"

    recent_rows = [dict(row) for row in normalized_rows[-5:]]

    return {
        "variant": "regression",
        "asset_key": ac.get_asset_key(),
        "symbol": symbol,
        "algorithm_name": algorithm_name,
        "algorithm_label": f"{symbol} {algorithm_name}",
        "model_family": algorithm_name,
        "label_mode": label_mode,
        "reference_rule": reference_rule,
        "default_chart_signal_mode": "raw",
        "generated_date": meta.get("latest_date"),
        "latest_summary": {
            "latest_date": meta.get("latest_date"),
            "lookback_days": meta.get("lookback_days"),
        },
        "legend": REGRESSION_COLORS,
        "title": f"{symbol} Ranking Watchlist",
        "selected_count": sum(1 for row in normalized_rows if bool(row.get("selected"))),
        "latest_text": latest_text,
        "recent_rows": recent_rows,
        "rows": normalized_rows,
    }


def build_html(rows: list[dict[str, object]], meta: dict[str, object]) -> str:
    return signal_chart_renderer.render_html(build_regression_recent_payload(rows, meta))


def build_meta(rows: list[dict[str, object]]) -> dict[str, object]:
    latest = rows[-1] if rows else None
    return {
        "latest_date": latest["date"] if latest else None,
        "lookback_days": len(rows),
    }


def main() -> None:
    rows = load_rows()
    meta = build_meta(rows)
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        f.write(build_html(rows, meta))
    latest = rows[-1] if rows else None
    print(
        json.dumps(
            {
                "output_path": OUTPUT_PATH,
                "rows": len(rows),
                "latest_date": latest["date"] if latest else None,
                "latest_selected": latest["selected"] if latest else None,
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
