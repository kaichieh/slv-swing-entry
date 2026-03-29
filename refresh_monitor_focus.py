from __future__ import annotations

import json
from html import escape

import pandas as pd

import asset_config as ac

FOCUS_ACTIONS = {"selected_now", "watchlist_wait"}


def load_focus() -> pd.DataFrame:
    frame = pd.read_csv(ac.get_monitor_priority_path(), sep="\t")
    focus = frame.loc[frame["action"].isin(FOCUS_ACTIONS)].copy()
    focus["focus_reason"] = focus["action"].map(
        {
            "selected_now": "Currently selected and actionable.",
            "watchlist_wait": "Valid watchlist line that is close enough to keep front-of-mind.",
        }
    )
    focus["review_order"] = range(1, len(focus) + 1)
    return focus[
        [
            "review_order",
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
            "focus_reason",
            "suggested_next_step",
        ]
    ]


def color(action: str) -> str:
    return "#0f766e" if action == "selected_now" else "#d97706"


def build_html(frame: pd.DataFrame) -> str:
    cards = []
    for _, row in frame.iterrows():
        accent = color(str(row["action"]))
        last_date = "n/a" if pd.isna(row["last_selected_date"]) else str(row["last_selected_date"])
        days = "n/a" if pd.isna(row["days_since_last_selected"]) else str(int(float(row["days_since_last_selected"])))
        cards.append(
            f"""
            <section class="card" style="--accent:{accent}">
              <div class="top">
                <div>
                  <div class="order">Review {int(row["review_order"])}</div>
                  <h2>{escape(str(row["symbol"]))}</h2>
                  <p class="line">{escape(str(row["preferred_line"]))}</p>
                </div>
                <span class="badge">{escape(str(row["action"]))}</span>
              </div>
              <p class="reason">{escape(str(row["focus_reason"]))}</p>
              <p class="next">{escape(str(row["suggested_next_step"]))}</p>
              <dl>
                <div><dt>tier</dt><dd>{int(row["priority_tier"])}</dd></div>
                <div><dt>status</dt><dd>{escape(str(row["status"]))}</dd></div>
                <div><dt>recent count</dt><dd>{int(row["recent_selected_count"])}</dd></div>
                <div><dt>latest date</dt><dd>{escape(str(row["latest_date"]))}</dd></div>
                <div><dt>last selected</dt><dd>{escape(last_date)}</dd></div>
                <div><dt>days since last</dt><dd>{escape(days)}</dd></div>
              </dl>
            </section>
            """
        )
    cards_html = "\n".join(cards)
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>Monitor Focus</title>
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
    .grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 16px; }}
    .card {{
      background: #fffdf8;
      border: 1px solid #e8dfcf;
      border-top: 5px solid var(--accent);
      border-radius: 18px;
      padding: 18px;
      box-shadow: 0 10px 24px rgba(15, 23, 42, 0.06);
    }}
    .top {{ display:flex; justify-content:space-between; gap:12px; align-items:start; }}
    .order {{ color:#5b6474; font-size:12px; text-transform:uppercase; letter-spacing:.08em; }}
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
    .reason {{ margin:14px 0 8px; line-height:1.5; }}
    .next {{ margin:0 0 14px; color:#5b6474; line-height:1.5; }}
    dl {{ display:grid; grid-template-columns:1fr 1fr; gap:10px 12px; margin:0; }}
    dl div {{ background:#faf6ee; border:1px solid #efe5d4; border-radius:12px; padding:10px 12px; }}
    dt {{ margin-bottom:4px; font-size:12px; color:#5b6474; text-transform:uppercase; letter-spacing:.06em; }}
    dd {{ margin:0; font-weight:600; }}
  </style>
</head>
<body>
  <h1>Monitor Focus</h1>
  <div class="summary">Daily review shortlist generated from the current priority board.</div>
  <div class="grid">{cards_html}</div>
</body>
</html>"""


def main() -> None:
    frame = load_focus()
    frame.to_csv(ac.get_monitor_focus_path(), sep="\t", index=False)
    ac.get_monitor_focus_chart_path().write_text(build_html(frame), encoding="utf-8")
    print(
        json.dumps(
            {
                "output_path": str(ac.get_monitor_focus_path()),
                "html_path": str(ac.get_monitor_focus_chart_path()),
                "rows": len(frame),
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
