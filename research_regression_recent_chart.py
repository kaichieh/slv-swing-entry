"""
Render a gold-style local HTML chart for recent regression ranking signals.
"""

from __future__ import annotations

import json
from html import escape

import pandas as pd

import asset_config as ac

INPUT_PATH = str(ac.get_regression_recent_output_path())
OUTPUT_PATH = str(ac.get_regression_recent_chart_path())


def load_rows() -> list[dict[str, object]]:
    frame = pd.read_csv(INPUT_PATH, sep="\t", parse_dates=["date"])
    rows: list[dict[str, object]] = []
    for _, row in frame.iterrows():
        rows.append(
            {
                "date": row["date"].strftime("%Y-%m-%d"),
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


def build_html(rows: list[dict[str, object]]) -> str:
    title = f"{ac.get_asset_symbol()} Ranking Watchlist"
    payload = json.dumps(rows, ensure_ascii=False)
    selected_count = sum(1 for row in rows if row["selected"])
    latest = rows[-1] if rows else None
    latest_text = (
        f"最近資料 {latest['date']} | 預測報酬={latest['predicted_return']:.4f} | selected={'yes' if latest['selected'] else 'no'}"
        if latest
        else "No rows"
    )
    recent_rows = rows[-5:]
    recent_cards = "".join(
        f"""
        <div class="recent-card">
          <div class="recent-date">{escape(str(row["date"]))}</div>
          <div class="recent-signal" style="color:{'#065f46' if row['selected'] else '#f59e0b'}">{'selected' if row['selected'] else 'watch'}</div>
          <div class="recent-metric">pred={escape(f"{row['predicted_return']:.4f}")}</div>
          <div class="recent-metric">pct={escape(f"{row['prediction_percentile']:.4f}")}</div>
          <div class="recent-metric">cutoff={escape(f"{row['bucket_cutoff']:.4f}")}</div>
          <div class="recent-metric">bucket={escape(str(row["bucket_direction"]))} {escape(str(row["bucket_pct"]))}%</div>
          <div class="recent-metric">selected={'yes' if row['selected'] else 'no'}</div>
          <div class="recent-metric">close={escape(f"{row['close']:.2f}")}</div>
        </div>
        """
        for row in recent_rows
    )
    return f"""<!DOCTYPE html>
<html lang="zh-Hant">
<head>
  <meta charset="utf-8">
  <title>{escape(title)}</title>
  <style>
    :root {{
      --bg: #f6f3ec;
      --ink: #1f2937;
      --muted: #6b7280;
      --grid: #d6d3d1;
      --panel: #fffdf8;
    }}
    body {{
      margin: 0;
      font-family: "Segoe UI", "Noto Sans TC", sans-serif;
      background: linear-gradient(180deg, #f6f3ec 0%, #ebe5da 100%);
      color: var(--ink);
    }}
    .wrap {{
      max-width: 1400px;
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
      gap: 18px;
      margin: 12px 0 18px;
      font-size: 14px;
    }}
    .legend span::before {{
      content: "";
      display: inline-block;
      width: 14px;
      height: 14px;
      margin-right: 8px;
      border-radius: 3px;
      vertical-align: -2px;
    }}
    .selected::before {{ background: #065f46; }}
    .watch::before {{ background: #f59e0b; }}
    .idle::before {{ background: #f8d9a0; }}
    .recent-panel {{
      display: grid;
      gap: 12px;
      margin-bottom: 18px;
    }}
    .recent-summary {{
      font-size: 14px;
      color: var(--muted);
    }}
    .recent-grid {{
      display: grid;
      grid-template-columns: repeat(5, minmax(150px, 1fr));
      gap: 10px;
    }}
    .recent-card {{
      background: #faf6ee;
      border: 1px solid #eadfcb;
      border-radius: 12px;
      padding: 10px 12px;
    }}
    .recent-date {{
      font-size: 12px;
      color: var(--muted);
      margin-bottom: 4px;
    }}
    .recent-signal {{
      font-size: 16px;
      font-weight: 700;
      margin-bottom: 6px;
    }}
    .recent-metric {{
      font-size: 12px;
      color: var(--ink);
      line-height: 1.45;
    }}
    #chart {{
      width: 100%;
      overflow-x: auto;
      border-top: 1px solid #efe8db;
      padding-top: 10px;
    }}
    svg {{
      display: block;
      height: 560px;
    }}
    .axis-label {{
      fill: var(--muted);
      font-size: 11px;
    }}
    .tooltip {{
      position: fixed;
      pointer-events: none;
      background: rgba(15, 23, 42, 0.92);
      color: white;
      padding: 10px 12px;
      border-radius: 10px;
      font-size: 13px;
      line-height: 1.5;
      display: none;
      max-width: 280px;
      white-space: pre-line;
    }}
  </style>
</head>
<body>
  <div class="wrap">
  <div class="card">
    <h1>{escape(title)}</h1>
    <div class="sub">{escape(latest_text)}。目前視窗內 selected 共 <strong>{selected_count}</strong> 筆。</div>
    <div class="recent-panel">
      <div class="recent-summary">最近 5 筆會先用卡片看 selected 狀態、pred、percentile 與 cutoff；下方長條圖則用收盤價高度配合顏色看整段 watchlist 節奏。</div>
      <div class="recent-grid">{recent_cards}</div>
    </div>
    <div class="legend">
      <span class="selected">selected</span>
      <span class="watch">watch</span>
      <span class="idle">idle</span>
    </div>
    <div id="chart">
      <svg id="chartSvg"></svg>
    </div>
  </div>
  </div>
  <div id="tooltip" class="tooltip"></div>
  <script>
    const rows = {payload};
    const chart = document.getElementById('chart');
    const svg = document.getElementById('chartSvg');
    const tooltip = document.getElementById('tooltip');
    const width = Math.max(2400, rows.length * 12);
    const height = 560;
    const topPad = 24;
    const priceHeight = 410;
    const leftPad = 56;
    const rightPad = 24;
    const innerWidth = width - leftPad - rightPad;
    const barWidth = innerWidth / rows.length;
    const closes = rows.map(r => r.close);
    const minClose = Math.min(...closes);
    const maxClose = Math.max(...closes);
    const closeRange = Math.max(maxClose - minClose, 1);

    svg.setAttribute('viewBox', `0 0 ${{width}} ${{height}}`);
    svg.setAttribute('width', String(width));
    svg.setAttribute('height', String(height));

    const bg = document.createElementNS("http://www.w3.org/2000/svg", "rect");
    bg.setAttribute('x', '0');
    bg.setAttribute('y', '0');
    bg.setAttribute('width', String(width));
    bg.setAttribute('height', String(height));
    bg.setAttribute('fill', '#fffdf8');
    svg.appendChild(bg);

    for (let i = 0; i < 5; i += 1) {{
      const y = topPad + (priceHeight / 4) * i;
      const line = document.createElementNS("http://www.w3.org/2000/svg", "line");
      line.setAttribute('x1', String(leftPad));
      line.setAttribute('x2', String(width - rightPad));
      line.setAttribute('y1', String(y));
      line.setAttribute('y2', String(y));
      line.setAttribute('stroke', '#d6d3d1');
      line.setAttribute('stroke-width', '1');
      line.setAttribute('stroke-dasharray', '3 5');
      svg.appendChild(line);

      const price = maxClose - (closeRange / 4) * i;
      const label = document.createElementNS("http://www.w3.org/2000/svg", "text");
      label.setAttribute('x', '8');
      label.setAttribute('y', String(y + 4));
      label.setAttribute('class', 'axis-label');
      label.textContent = price.toFixed(2);
      svg.appendChild(label);
    }}

    rows.forEach((row, i) => {{
      const x = leftPad + i * barWidth;
      const y = topPad + (1 - (row.close - minClose) / closeRange) * priceHeight;
      const rect = document.createElementNS("http://www.w3.org/2000/svg", "rect");
      rect.setAttribute("x", String(x + 1));
      rect.setAttribute("y", String(y));
      rect.setAttribute("width", String(Math.max(barWidth - 2, 1)));
      rect.setAttribute("height", String(topPad + priceHeight - y));
      rect.setAttribute("rx", "2");
      let fill = "#f8d9a0";
      if (row.selected) {{
        fill = "#065f46";
      }} else if (row.prediction_percentile <= row.bucket_pct / 100 * 2) {{
        fill = "#f59e0b";
      }} else if (row.prediction_percentile <= 0.35) {{
        fill = "#fde68a";
      }}
      rect.setAttribute("fill", fill);
      rect.addEventListener("mousemove", event => {{
        tooltip.style.display = "block";
        tooltip.style.left = (event.clientX + 14) + "px";
        tooltip.style.top = (event.clientY + 14) + "px";
        tooltip.innerHTML = `
          <strong>${{row.date}}</strong><br>
          close=${{row.close}}<br>
          predicted_return=${{row.predicted_return}}<br>
          percentile=${{row.prediction_percentile}}<br>
          selected=${{row.selected ? 'yes' : 'no'}}<br>
          bucket=${{row.bucket_direction}} ${{row.bucket_pct}}%<br>
          cutoff=${{row.bucket_cutoff}}
        `;
      }});
      rect.addEventListener("mouseleave", () => {{ tooltip.style.display = "none"; }});
      svg.appendChild(rect);
    }});

    const latestLabel = document.createElementNS("http://www.w3.org/2000/svg", "text");
    latestLabel.setAttribute("x", String(width - rightPad));
    latestLabel.setAttribute("y", String(height - 20));
    latestLabel.setAttribute("text-anchor", "end");
    latestLabel.setAttribute("class", "axis-label");
    latestLabel.textContent = rows[rows.length - 1]?.date || "";
    svg.appendChild(latestLabel);

    const midLabel = document.createElementNS("http://www.w3.org/2000/svg", "text");
    midLabel.setAttribute("x", String(width / 2));
    midLabel.setAttribute("y", String(height - 20));
    midLabel.setAttribute("text-anchor", "middle");
    midLabel.setAttribute("class", "axis-label");
    midLabel.textContent = rows[Math.floor(rows.length / 2)]?.date || "";
    svg.appendChild(midLabel);

    const firstLabel = document.createElementNS("http://www.w3.org/2000/svg", "text");
    firstLabel.setAttribute("x", String(leftPad));
    firstLabel.setAttribute("y", String(height - 20));
    firstLabel.setAttribute("text-anchor", "start");
    firstLabel.setAttribute("class", "axis-label");
    firstLabel.textContent = rows[0]?.date || "";
    svg.appendChild(firstLabel);
    requestAnimationFrame(() => {{
      chart.scrollLeft = chart.scrollWidth;
    }});
  </script>
</body>
</html>"""


def main() -> None:
    rows = load_rows()
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        f.write(build_html(rows))
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
