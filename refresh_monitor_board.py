from __future__ import annotations

import json
import re
from html import escape

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
        records.append(record)
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


def build_html(board: pd.DataFrame) -> str:
    counts = board["action"].value_counts().to_dict()
    summary = " | ".join(f"{key}={value}" for key, value in counts.items())
    today_board = board.loc[
        board["action"].isin(["selected_now", "watchlist_wait", "watchlist_blocked", "priority_research", "inactive_wait"])
    ].copy()
    today_cards = "\n".join(render_today_card(row) for _, row in today_board.iterrows())
    role_cards = "\n".join(render_role_card(row) for _, row in board.iterrows())
    today_legend = "".join(
        [
            '<span class="legend-item"><span class="swatch" style="background:#9ca3af"></span>no_entry</span>',
            '<span class="legend-item"><span class="swatch" style="background:#fde68a"></span>weak_bullish</span>',
            '<span class="legend-item"><span class="swatch" style="background:#f59e0b"></span>bullish</span>',
            '<span class="legend-item"><span class="swatch" style="background:#16a34a"></span>strong_bullish</span>',
            '<span class="legend-item"><span class="swatch" style="background:#065f46"></span>very_strong_bullish / selected</span>',
            f'<span class="legend-item"><span class="swatch" style="background:{PRIORITY_RESEARCH_SIGNAL_COLOR}"></span>priority_research</span>',
        ]
    )
    role_legend = "".join(
        f'<span class="legend-item"><span class="swatch" style="background:{role_color(role)}"></span>{escape(role)}</span>'
        for role in ["primary", "reference", "research"]
    )
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>Monitor Board</title>
  <style>
    :root {{
      --bg: #f6f3ec;
      --ink: #1f2937;
      --muted: #6b7280;
      --panel: #fffdf8;
    }}
    body {{
      margin: 0;
      font-family: "Segoe UI", Arial, sans-serif;
      background: linear-gradient(180deg, #f6f3ec 0%, #ebe5da 100%);
      color: var(--ink);
    }}
    .wrap {{
      max-width: 1600px;
      margin: 0 auto;
      padding: 24px;
    }}
    .card {{
      background: var(--panel);
      border: 1px solid #e7e0d4;
      border-radius: 18px;
      box-shadow: 0 18px 60px rgba(31, 41, 55, 0.08);
      padding: 20px 20px 12px;
    }}
    h1 {{
      margin: 0 0 8px;
      font-size: 28px;
    }}
    .sub {{
      color: var(--muted);
      margin-bottom: 14px;
    }}
    .legend {{
      display: flex;
      flex-wrap: wrap;
      gap: 14px;
      margin-bottom: 18px;
      font-size: 14px;
    }}
    .legend-item {{
      display: inline-flex;
      align-items: center;
      gap: 8px;
    }}
    .swatch {{
      width: 14px;
      height: 14px;
      border-radius: 3px;
      display: inline-block;
    }}
    .section {{
      margin-top: 18px;
    }}
    .section h2 {{
      margin: 0 0 8px;
      font-size: 20px;
    }}
    .section-sub {{
      color: var(--muted);
      margin-bottom: 12px;
      font-size: 14px;
    }}
    .spotlight-grid {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
      gap: 10px;
    }}
    .spotlight-card {{
      display: block;
      text-decoration: none;
      background: #faf6ee;
      border: 1px solid #eadfcb;
      border-top: 4px solid var(--accent);
      border-radius: 12px;
      padding: 10px 12px;
    }}
    .spotlight-date {{
      font-size: 12px;
      color: var(--muted);
      margin-bottom: 4px;
    }}
    .spotlight-symbol {{
      font-size: 20px;
      font-weight: 700;
      margin-bottom: 4px;
    }}
    .spotlight-line {{
      font-size: 14px;
      color: var(--muted);
      margin-bottom: 8px;
    }}
    .spotlight-metric {{
      font-size: 12px;
      color: var(--ink);
      line-height: 1.45;
    }}
    .spotlight-note {{
      font-size: 12px;
      color: var(--muted);
      line-height: 1.45;
      margin-top: 8px;
    }}
    .role-grid {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
      gap: 10px;
    }}
    .role-card {{
      display: block;
      text-decoration: none;
      background: #faf6ee;
      border: 1px solid #eadfcb;
      border-top: 4px solid var(--accent);
      border-radius: 12px;
      padding: 10px 12px;
    }}
    .role-symbol {{
      font-size: 18px;
      font-weight: 700;
      margin-bottom: 6px;
    }}
    .role-badge {{
      font-size: 12px;
      color: var(--muted);
      margin-bottom: 6px;
      text-transform: uppercase;
      letter-spacing: 0.06em;
    }}
    .role-line {{
      font-size: 13px;
      color: var(--ink);
      margin-bottom: 8px;
    }}
    .role-note {{
      font-size: 12px;
      color: var(--muted);
      line-height: 1.45;
    }}
  </style>
</head>
<body>
  <div class="wrap">
    <div class="card">
      <h1>Monitor Board</h1>
      <div class="sub">Single homepage for non-SLV assets. Read it top-down: first who matters today, then the priority research follow-ups, then each asset's structural role. {escape(summary)}</div>

      <div class="section">
        <h2>Today</h2>
        <div class="section-sub">Current operating states plus the eight benchmark-aware research follow-ups. Card accent colors match the latest bar color inside each asset chart; priority research cards use the purple follow-up shell.</div>
        <div class="legend">{today_legend}</div>
        <div class="spotlight-grid">{today_cards}</div>
      </div>

      <div class="section">
        <h2>Role</h2>
        <div class="section-sub">Structural role in the basket. This section answers whether an asset is a primary line, a reference context line, or still research-only.</div>
        <div class="legend">{role_legend}</div>
        <div class="role-grid">{role_cards}</div>
      </div>
    </div>
  </div>
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
