from __future__ import annotations

import json
from html import escape

import pandas as pd

import asset_config as ac

ASSET_KEYS = ["gld", "slv", "iwm", "spy", "tlt", "xle", "nvda", "qqq", "tsla"]
ACTION_PRIORITY = {
    "selected_now": 0,
    "watchlist_wait": 1,
    "inactive_wait": 2,
    "reference_only": 3,
    "research_only": 4,
}


def safe_text(value: object, fallback: str = "unknown") -> str:
    if value is None or pd.isna(value):
        return fallback
    text = str(value).strip()
    if not text or text.lower() == "nan":
        return fallback
    return text


def load_board() -> pd.DataFrame:
    frames: list[pd.DataFrame] = []
    for key in ASSET_KEYS:
        frame = pd.read_csv(ac.get_monitor_snapshot_path(key), sep="\t")
        frame["sort_priority"] = frame["action"].map(lambda value: ACTION_PRIORITY.get(str(value), 99))
        frame["chart_href"] = ac.get_primary_chart_path(key).relative_to(ac.REPO_DIR).as_posix()
        frame["display_latest_date"] = load_display_latest_date(key)
        frame["signal_color"] = load_signal_color(key)
        frames.append(frame)
    board = pd.concat(frames, ignore_index=True)
    return board.sort_values(["sort_priority", "symbol"]).drop(columns=["sort_priority"])


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
        if bool(row["selected"]):
            return "#065f46"
        percentile = float(row["prediction_percentile"])
        bucket_pct = float(row["bucket_pct"])
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
    tokens = " ".join(
        [
            str(row.get("role", "")),
            str(row.get("lane_type", "")),
            str(row.get("status", "")),
        ]
    ).lower()
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


def render_triage_card(row: pd.Series) -> str:
    chart_href = escape(str(row["chart_href"]))
    return f"""
    <a class="triage-card" href="{chart_href}">
      <div class="triage-symbol">{escape(str(row["symbol"]))}</div>
      <div class="triage-lane">{escape(safe_text(row.get("research_lane", "unknown")))}</div>
      <div class="triage-state">viability={escape(safe_text(row.get("viability", "unknown")))}</div>
      <div class="triage-state">adoption={escape(safe_text(row.get("adoption_state", "unknown")))}</div>
      <div class="triage-note">{escape(str(row["action_note"]))}</div>
    </a>
    """


def build_html(board: pd.DataFrame) -> str:
    counts = board["action"].value_counts().to_dict()
    summary = " | ".join(f"{key}={value}" for key, value in counts.items())
    today_board = board.loc[board["action"].isin(["selected_now", "watchlist_wait", "inactive_wait"])].copy()
    today_cards = "\n".join(render_today_card(row) for _, row in today_board.iterrows())
    role_cards = "\n".join(render_role_card(row) for _, row in board.iterrows())
    triage_cards = "\n".join(render_triage_card(row) for _, row in board.iterrows())
    today_legend = "".join(
        [
            '<span class="legend-item"><span class="swatch" style="background:#9ca3af"></span>no_entry</span>',
            '<span class="legend-item"><span class="swatch" style="background:#fde68a"></span>weak_bullish</span>',
            '<span class="legend-item"><span class="swatch" style="background:#f59e0b"></span>bullish</span>',
            '<span class="legend-item"><span class="swatch" style="background:#16a34a"></span>strong_bullish</span>',
            '<span class="legend-item"><span class="swatch" style="background:#065f46"></span>very_strong_bullish / selected</span>',
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
    .triage-card {{
      display: block;
      text-decoration: none;
      background: #f8f4ec;
      border: 1px solid #eadfcb;
      border-radius: 12px;
      padding: 12px;
    }}
    .triage-symbol {{
      font-size: 18px;
      font-weight: 700;
      margin-bottom: 6px;
    }}
    .triage-lane {{
      font-size: 12px;
      color: var(--muted);
      margin-bottom: 6px;
      text-transform: uppercase;
      letter-spacing: 0.05em;
    }}
    .triage-state {{
      font-size: 12px;
      color: var(--ink);
      line-height: 1.45;
    }}
    .triage-note {{
      font-size: 12px;
      color: var(--muted);
      line-height: 1.45;
      margin-top: 8px;
    }}
  </style>
</head>
<body>
  <div class="wrap">
    <div class="card">
      <h1>Monitor Board</h1>
      <div class="sub">Single homepage for non-SLV assets. Read it top-down: first who matters today, then what role each asset plays in the research set. {escape(summary)}</div>

      <div class="section">
        <h2>Today</h2>
        <div class="section-sub">Only current operating states. Card accent colors match the latest bar color inside each asset chart; the textual today_status still tells you whether it is selected_now, watchlist_wait, or inactive_wait.</div>
        <div class="legend">{today_legend}</div>
        <div class="spotlight-grid">{today_cards}</div>
      </div>

      <div class="section">
        <h2>Role</h2>
        <div class="section-sub">Structural role in the basket. This section answers whether an asset is a primary line, a reference context line, or still research-only.</div>
        <div class="legend">{role_legend}</div>
        <div class="role-grid">{role_cards}</div>
      </div>

      <div class="section">
        <h2>Research Triage</h2>
        <div class="section-sub">Use this section to decide where new research effort belongs.</div>
        <div class="role-grid">{triage_cards}</div>
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
