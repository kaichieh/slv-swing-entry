from __future__ import annotations

import json
from html import escape

import pandas as pd

import asset_config as ac

ASSET_KEYS = ["iwm", "spy", "tlt", "xle", "nvda", "qqq", "tsla"]
ACTION_PRIORITY = {
    "selected_now": 0,
    "watchlist_wait": 1,
    "inactive_wait": 2,
    "reference_only": 3,
    "research_only": 4,
}


def load_board() -> pd.DataFrame:
    frames: list[pd.DataFrame] = []
    for key in ASSET_KEYS:
        path = ac.get_monitor_snapshot_path(key)
        frame = pd.read_csv(path, sep="\t")
        frame["sort_priority"] = frame["action"].map(lambda value: ACTION_PRIORITY.get(str(value), 99))
        frames.append(frame)
    board = pd.concat(frames, ignore_index=True)
    board = board.sort_values(["sort_priority", "symbol"]).drop(columns=["sort_priority"])
    return board


def card_color(action: str) -> str:
    if action == "selected_now":
        return "#0f766e"
    if action == "watchlist_wait":
        return "#d97706"
    if action == "inactive_wait":
        return "#64748b"
    if action == "reference_only":
        return "#2563eb"
    if action == "research_only":
        return "#7c3aed"
    return "#475569"


def render_card(row: pd.Series) -> str:
    color = card_color(str(row["action"]))
    latest = "n/a" if pd.isna(row["latest_value"]) else f"{float(row['latest_value']):.6f}"
    cutoff = "n/a" if pd.isna(row["cutoff"]) else f"{float(row['cutoff']):.6f}"
    last_date = "n/a" if pd.isna(row["last_selected_date"]) else str(row["last_selected_date"])
    days = "n/a" if pd.isna(row["days_since_last_selected"]) else str(int(float(row["days_since_last_selected"])))
    return f"""
    <section class="card" style="--accent:{color}">
      <div class="top">
        <div>
          <div class="symbol">{escape(str(row["symbol"]))}</div>
          <div class="line">{escape(str(row["preferred_line"]))}</div>
        </div>
        <div class="badge">{escape(str(row["action"]))}</div>
      </div>
      <p class="note">{escape(str(row["action_note"]))}</p>
      <dl>
        <div><dt>lane</dt><dd>{escape(str(row["lane_type"]))}</dd></div>
        <div><dt>status</dt><dd>{escape(str(row["status"]))}</dd></div>
        <div><dt>recent count</dt><dd>{int(row["recent_selected_count"])}</dd></div>
        <div><dt>latest date</dt><dd>{escape(str(row["latest_date"]))}</dd></div>
        <div><dt>latest value</dt><dd>{latest}</dd></div>
        <div><dt>latest selected</dt><dd>{"yes" if bool(row["latest_selected"]) else "no"}</dd></div>
        <div><dt>cutoff</dt><dd>{cutoff}</dd></div>
        <div><dt>last selected</dt><dd>{escape(last_date)}</dd></div>
        <div><dt>days since last</dt><dd>{days}</dd></div>
      </dl>
    </section>
    """


def build_html(board: pd.DataFrame) -> str:
    counts = board["action"].value_counts().to_dict()
    summary = " | ".join(f"{key}={value}" for key, value in counts.items())
    cards = "\n".join(render_card(row) for _, row in board.iterrows())
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>Monitor Board</title>
  <style>
    :root {{
      --bg: #f7f4ed;
      --text: #172033;
      --muted: #5b6474;
      --card: #fffdf8;
      --line: #e8dfcf;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      padding: 28px;
      font-family: "Segoe UI", Arial, sans-serif;
      background: linear-gradient(180deg, #f7f4ed 0%, #efe8d8 100%);
      color: var(--text);
    }}
    h1 {{ margin: 0 0 8px; font-size: 32px; }}
    .summary {{ color: var(--muted); margin-bottom: 20px; }}
    .grid {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
      gap: 16px;
    }}
    .card {{
      background: var(--card);
      border: 1px solid var(--line);
      border-top: 5px solid var(--accent);
      border-radius: 18px;
      padding: 18px;
      box-shadow: 0 10px 24px rgba(15, 23, 42, 0.06);
    }}
    .top {{
      display: flex;
      justify-content: space-between;
      gap: 12px;
      align-items: start;
    }}
    .symbol {{ font-size: 28px; font-weight: 700; }}
    .line {{ color: var(--muted); font-size: 14px; margin-top: 4px; }}
    .badge {{
      background: color-mix(in srgb, var(--accent) 14%, white);
      color: var(--accent);
      padding: 6px 10px;
      border-radius: 999px;
      font-size: 12px;
      font-weight: 700;
      white-space: nowrap;
    }}
    .note {{ color: var(--muted); line-height: 1.5; min-height: 44px; }}
    dl {{
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 10px 12px;
      margin: 0;
    }}
    dl div {{
      background: #faf6ee;
      border: 1px solid #efe5d4;
      border-radius: 12px;
      padding: 10px 12px;
    }}
    dt {{
      margin-bottom: 4px;
      font-size: 12px;
      color: var(--muted);
      text-transform: uppercase;
      letter-spacing: 0.06em;
    }}
    dd {{ margin: 0; font-weight: 600; }}
  </style>
</head>
<body>
  <h1>Monitor Board</h1>
  <div class="summary">{escape(summary)}</div>
  <div class="grid">{cards}</div>
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
