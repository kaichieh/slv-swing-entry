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


def render_spotlight_card(row: pd.Series) -> str:
    color = card_color(str(row["action"]))
    latest = "n/a" if pd.isna(row["latest_value"]) else f"{float(row['latest_value']):.4f}"
    cutoff = "n/a" if pd.isna(row["cutoff"]) else f"{float(row['cutoff']):.4f}"
    last_date = "n/a" if pd.isna(row["last_selected_date"]) else str(row["last_selected_date"])
    days = "n/a" if pd.isna(row["days_since_last_selected"]) else str(int(float(row["days_since_last_selected"])))
    latest_date = "n/a" if pd.isna(row["latest_date"]) else str(row["latest_date"])
    recent_count = int(row["recent_selected_count"])
    return f"""
    <div class="spotlight-card" style="--accent:{color}">
      <div class="spotlight-date">{escape(latest_date)}</div>
      <div class="spotlight-symbol" style="color:{color}">{escape(str(row["symbol"]))}</div>
      <div class="spotlight-line">{escape(str(row["preferred_line"]))}</div>
      <div class="spotlight-metric">action={escape(str(row["action"]))}</div>
      <div class="spotlight-metric">status={escape(str(row["status"]))}</div>
      <div class="spotlight-metric">recent={recent_count}</div>
      <div class="spotlight-metric">latest={latest}</div>
      <div class="spotlight-metric">cutoff={cutoff}</div>
      <div class="spotlight-metric">last_selected={escape(last_date)}</div>
      <div class="spotlight-metric">days_since_last={escape(days)}</div>
      <div class="spotlight-note">{escape(str(row["action_note"]))}</div>
    </div>
    """


def build_html(board: pd.DataFrame) -> str:
    counts = board["action"].value_counts().to_dict()
    summary = " | ".join(f"{key}={value}" for key, value in counts.items())
    spotlight_rows = board.head(5)
    spotlight_cards = "\n".join(render_spotlight_card(row) for _, row in spotlight_rows.iterrows())
    payload = json.dumps(
        [
            {
                "symbol": str(row["symbol"]),
                "action": str(row["action"]),
                "preferred_line": str(row["preferred_line"]),
                "recent_selected_count": int(row["recent_selected_count"]),
                "latest_date": "" if pd.isna(row["latest_date"]) else str(row["latest_date"]),
                "latest_value": None if pd.isna(row["latest_value"]) else float(row["latest_value"]),
                "last_selected_date": "" if pd.isna(row["last_selected_date"]) else str(row["last_selected_date"]),
                "days_since_last_selected": None if pd.isna(row["days_since_last_selected"]) else int(float(row["days_since_last_selected"])),
                "action_note": str(row["action_note"]),
            }
            for _, row in board.iterrows()
        ],
        ensure_ascii=False,
    )
    legend = "".join(
        f'<span class="legend-item"><span class="swatch" style="background:{card_color(action)}"></span>{escape(action)}</span>'
        for action in ["selected_now", "watchlist_wait", "inactive_wait", "reference_only", "research_only"]
    )
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
      font-family: "Segoe UI", "Noto Sans TC", Arial, sans-serif;
      background: linear-gradient(180deg, #f7f4ed 0%, #efe8d8 100%);
      color: var(--text);
    }}
    h1 {{ margin: 0 0 8px; font-size: 32px; }}
    .summary {{ color: var(--muted); margin-bottom: 20px; }}
    .card {{
      background: var(--card);
      border: 1px solid var(--line);
      border-radius: 18px;
      box-shadow: 0 10px 24px rgba(15, 23, 42, 0.06);
      padding: 20px 20px 12px;
    }}
    .legend {{
      display: flex;
      flex-wrap: wrap;
      gap: 14px;
      margin: 12px 0 18px;
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
    .spotlight-grid {{
      display: grid;
      grid-template-columns: repeat(5, minmax(180px, 1fr));
      gap: 12px;
      margin-bottom: 18px;
    }}
    .spotlight-card {{
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
    #chart {{
      width: 100%;
      overflow-x: auto;
      border-top: 1px solid #efe8db;
      padding-top: 10px;
    }}
    svg {{
      display: block;
      height: 420px;
    }}
    .axis-label {{
      fill: var(--muted);
      font-size: 12px;
    }}
    .tooltip {{
      position: fixed;
      pointer-events: none;
      background: rgba(17, 24, 39, 0.94);
      color: #fff;
      padding: 10px 12px;
      border-radius: 10px;
      font-size: 12px;
      line-height: 1.45;
      transform: translate(12px, 12px);
      display: none;
      white-space: pre-line;
      box-shadow: 0 10px 30px rgba(0,0,0,0.2);
      max-width: 320px;
    }}
  </style>
</head>
<body>
  <div class="card">
    <h1>Monitor Board</h1>
    <div class="summary">非 `SLV` 標的目前監控摘要。{escape(summary)}</div>
    <div class="spotlight-grid">{spotlight_cards}</div>
    <div class="legend">{legend}</div>
    <div id="chart"></div>
  </div>
  <div id="tooltip" class="tooltip"></div>
  <script>
    const rows = {payload};
    const colors = {{
      selected_now: "{card_color("selected_now")}",
      watchlist_wait: "{card_color("watchlist_wait")}",
      inactive_wait: "{card_color("inactive_wait")}",
      reference_only: "{card_color("reference_only")}",
      research_only: "{card_color("research_only")}",
    }};
    const chart = document.getElementById('chart');
    const tooltip = document.getElementById('tooltip');
    const width = Math.max(1200, rows.length * 120);
    const height = 420;
    const topPad = 40;
    const leftPad = 56;
    const rightPad = 24;
    const bottomPad = 56;
    const innerWidth = width - leftPad - rightPad;
    const innerHeight = height - topPad - bottomPad;
    const maxRecent = Math.max(...rows.map(r => r.recent_selected_count), 1);
    const barWidth = innerWidth / rows.length * 0.72;

    const svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
    svg.setAttribute('viewBox', `0 0 ${{width}} ${{height}}`);
    svg.setAttribute('width', String(width));
    svg.setAttribute('height', String(height));

    const bg = document.createElementNS('http://www.w3.org/2000/svg', 'rect');
    bg.setAttribute('x', '0');
    bg.setAttribute('y', '0');
    bg.setAttribute('width', String(width));
    bg.setAttribute('height', String(height));
    bg.setAttribute('fill', '#fffdf8');
    svg.appendChild(bg);

    for (let i = 0; i < 5; i += 1) {{
      const y = topPad + (innerHeight / 4) * i;
      const line = document.createElementNS('http://www.w3.org/2000/svg', 'line');
      line.setAttribute('x1', String(leftPad));
      line.setAttribute('x2', String(width - rightPad));
      line.setAttribute('y1', String(y));
      line.setAttribute('y2', String(y));
      line.setAttribute('stroke', '#d6d3d1');
      line.setAttribute('stroke-width', '1');
      line.setAttribute('stroke-dasharray', '3 5');
      svg.appendChild(line);

      const label = document.createElementNS('http://www.w3.org/2000/svg', 'text');
      label.setAttribute('x', '8');
      label.setAttribute('y', String(y + 4));
      label.setAttribute('class', 'axis-label');
      label.textContent = String(Math.round(maxRecent - (maxRecent / 4) * i));
      svg.appendChild(label);
    }}

    rows.forEach((row, index) => {{
      const slotWidth = innerWidth / rows.length;
      const x = leftPad + index * slotWidth + (slotWidth - barWidth) / 2;
      const barHeight = (row.recent_selected_count / maxRecent) * innerHeight;
      const y = topPad + innerHeight - barHeight;
      const rect = document.createElementNS('http://www.w3.org/2000/svg', 'rect');
      rect.setAttribute('x', String(x));
      rect.setAttribute('y', String(y));
      rect.setAttribute('width', String(barWidth));
      rect.setAttribute('height', String(Math.max(barHeight, 6)));
      rect.setAttribute('rx', '6');
      rect.setAttribute('fill', colors[row.action] || '#475569');
      rect.setAttribute('opacity', row.action === 'inactive_wait' ? '0.55' : '0.95');
      rect.addEventListener('mousemove', event => {{
        tooltip.style.display = 'block';
        tooltip.style.left = (event.clientX + 14) + 'px';
        tooltip.style.top = (event.clientY + 14) + 'px';
        tooltip.innerHTML = `<strong>${{row.symbol}}</strong><br>action=${{row.action}}<br>line=${{row.preferred_line}}<br>recent=${{row.recent_selected_count}}<br>latest=${{row.latest_date || 'n/a'}}<br>last_selected=${{row.last_selected_date || 'n/a'}}<br>${{row.action_note}}`;
      }});
      rect.addEventListener('mouseleave', () => {{
        tooltip.style.display = 'none';
      }});
      svg.appendChild(rect);

      const label = document.createElementNS('http://www.w3.org/2000/svg', 'text');
      label.setAttribute('x', String(x + barWidth / 2));
      label.setAttribute('y', String(height - 24));
      label.setAttribute('text-anchor', 'middle');
      label.setAttribute('class', 'axis-label');
      label.textContent = row.symbol;
      svg.appendChild(label);
    }});

    chart.appendChild(svg);
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
