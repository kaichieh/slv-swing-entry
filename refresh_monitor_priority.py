from __future__ import annotations

import json
from html import escape

import pandas as pd

import asset_config as ac

ACTION_RANK = {
    "selected_now": 0,
    "watchlist_wait": 1,
    "inactive_wait": 2,
    "reference_only": 3,
    "research_only": 4,
}


def priority_note(action: str, symbol: str) -> str:
    if action == "selected_now":
        return f"{symbol} is the current highest-priority live-like line."
    if action == "watchlist_wait":
        return f"{symbol} stays on the active watchlist and is the next place to look if price action improves."
    if action == "inactive_wait":
        return f"{symbol} has a valid preferred line, but there is no current trigger."
    if action == "reference_only":
        return f"{symbol} should only be used as market context."
    return f"{symbol} remains research-only until a stronger formulation appears."


def suggested_next_step(action: str, symbol: str) -> str:
    if action == "selected_now":
        return "Review chart and current context first."
    if action == "watchlist_wait":
        return "Keep on shortlist and watch for renewed selection."
    if action == "inactive_wait":
        return "Monitor passively; no immediate action."
    if action == "reference_only":
        return "Use only for background regime read."
    return "No live action; research only."


def load_priority() -> pd.DataFrame:
    board = pd.read_csv(ac.get_monitor_board_path(), sep="\t")
    board["priority_rank"] = board["action"].map(lambda value: ACTION_RANK.get(str(value), 99))
    board["priority_tier"] = board["priority_rank"] + 1
    board["priority_note"] = board.apply(lambda row: priority_note(str(row["action"]), str(row["symbol"])), axis=1)
    board["suggested_next_step"] = board.apply(lambda row: suggested_next_step(str(row["action"]), str(row["symbol"])), axis=1)
    board = board.sort_values(["priority_rank", "days_since_last_selected", "symbol"], na_position="last")
    return board[
        [
            "priority_tier",
            "asset_key",
            "symbol",
            "action",
            "preferred_line",
            "status",
            "recent_selected_count",
            "latest_date",
            "last_selected_date",
            "days_since_last_selected",
            "priority_note",
            "suggested_next_step",
        ]
    ]


def color(action: str) -> str:
    if action == "selected_now":
        return "#0f766e"
    if action == "watchlist_wait":
        return "#d97706"
    if action == "inactive_wait":
        return "#64748b"
    if action == "reference_only":
        return "#2563eb"
    return "#7c3aed"


def build_html(frame: pd.DataFrame) -> str:
    rows = []
    for _, row in frame.iterrows():
        accent = color(str(row["action"]))
        last_date = "n/a" if pd.isna(row["last_selected_date"]) else str(row["last_selected_date"])
        days = "n/a" if pd.isna(row["days_since_last_selected"]) else str(int(float(row["days_since_last_selected"])))
        rows.append(
            f"""
            <section class="card" style="--accent:{accent}">
              <div class="top">
                <div>
                  <div class="tier">Tier {int(row["priority_tier"])}</div>
                  <h2>{escape(str(row["symbol"]))}</h2>
                  <p class="line">{escape(str(row["preferred_line"]))}</p>
                </div>
                <span class="badge">{escape(str(row["action"]))}</span>
              </div>
              <p class="note">{escape(str(row["priority_note"]))}</p>
              <p class="next">{escape(str(row["suggested_next_step"]))}</p>
              <dl>
                <div><dt>status</dt><dd>{escape(str(row["status"]))}</dd></div>
                <div><dt>recent count</dt><dd>{int(row["recent_selected_count"])}</dd></div>
                <div><dt>latest date</dt><dd>{escape(str(row["latest_date"]))}</dd></div>
                <div><dt>last selected</dt><dd>{escape(last_date)}</dd></div>
                <div><dt>days since last</dt><dd>{escape(days)}</dd></div>
              </dl>
            </section>
            """
        )
    cards = "\n".join(rows)
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>Monitor Priority</title>
  <style>
    body {{
      margin: 0;
      padding: 28px;
      font-family: "Segoe UI", Arial, sans-serif;
      background: linear-gradient(180deg, #f7f4ed 0%, #efe8d8 100%);
      color: #172033;
    }}
    h1 {{ margin: 0 0 8px; font-size: 32px; }}
    .summary {{ color: #5b6474; margin-bottom: 20px; }}
    .grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 16px; }}
    .card {{
      background: #fffdf8;
      border: 1px solid #e8dfcf;
      border-top: 5px solid var(--accent);
      border-radius: 18px;
      padding: 18px;
      box-shadow: 0 10px 24px rgba(15, 23, 42, 0.06);
    }}
    .top {{ display:flex; justify-content:space-between; gap:12px; align-items:start; }}
    .tier {{ color:#5b6474; font-size:12px; text-transform:uppercase; letter-spacing:.08em; }}
    h2 {{ margin:4px 0 2px; font-size:28px; }}
    .line {{ margin:0; color:#5b6474; font-size:14px; }}
    .badge {{
      background: color-mix(in srgb, var(--accent) 14%, white);
      color: var(--accent);
      border-radius:999px;
      padding:6px 10px;
      font-size:12px;
      font-weight:700;
      white-space:nowrap;
    }}
    .note {{ color:#172033; line-height:1.5; margin:14px 0 8px; }}
    .next {{ color:#5b6474; line-height:1.5; margin:0 0 14px; }}
    dl {{ display:grid; grid-template-columns:1fr 1fr; gap:10px 12px; margin:0; }}
    dl div {{ background:#faf6ee; border:1px solid #efe5d4; border-radius:12px; padding:10px 12px; }}
    dt {{ margin-bottom:4px; font-size:12px; color:#5b6474; text-transform:uppercase; letter-spacing:.06em; }}
    dd {{ margin:0; font-weight:600; }}
  </style>
</head>
<body>
  <h1>Monitor Priority</h1>
  <div class="summary">Cross-asset order for daily review based on the current preferred line and operating action.</div>
  <div class="grid">{cards}</div>
</body>
</html>"""


def main() -> None:
    frame = load_priority()
    frame.to_csv(ac.get_monitor_priority_path(), sep="\t", index=False)
    ac.get_monitor_priority_chart_path().write_text(build_html(frame), encoding="utf-8")
    print(
        json.dumps(
            {
                "output_path": str(ac.get_monitor_priority_path()),
                "html_path": str(ac.get_monitor_priority_chart_path()),
                "rows": len(frame),
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
