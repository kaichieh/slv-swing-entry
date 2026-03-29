"""
Render a lightweight HTML chart for recent regression ranking signals.
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
    title = f"{ac.get_asset_symbol()} Regression Recent Ranking"
    payload = json.dumps(rows, ensure_ascii=False)
    selected_count = sum(1 for row in rows if row["selected"])
    latest = rows[-1] if rows else None
    latest_text = (
        f"Latest {latest['date']} | pred={latest['predicted_return']:.4f} | selected={'yes' if latest['selected'] else 'no'}"
        if latest
        else "No rows"
    )
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>{escape(title)}</title>
  <style>
    body {{ font-family: Arial, sans-serif; background: #f7f4ed; color: #1f2937; margin: 0; padding: 24px; }}
    .summary {{ margin-bottom: 18px; }}
    .summary h1 {{ margin: 0 0 8px; font-size: 28px; }}
    .summary p {{ margin: 4px 0; }}
    .legend {{ display: flex; gap: 18px; margin: 12px 0 20px; }}
    .legend span::before {{ content: ""; display: inline-block; width: 14px; height: 14px; margin-right: 8px; border-radius: 3px; vertical-align: -2px; }}
    .yes::before {{ background: #0f766e; }}
    .no::before {{ background: #cbd5e1; }}
    svg {{ width: 100%; height: 520px; background: white; border-radius: 16px; box-shadow: 0 8px 30px rgba(15, 23, 42, 0.08); }}
    .tooltip {{ position: fixed; pointer-events: none; background: rgba(15, 23, 42, 0.92); color: white; padding: 10px 12px; border-radius: 10px; font-size: 13px; line-height: 1.5; display: none; max-width: 240px; }}
  </style>
</head>
<body>
  <div class="summary">
    <h1>{escape(title)}</h1>
    <p>{escape(latest_text)}</p>
    <p>Selected rows in current window: {selected_count} / {len(rows)}</p>
  </div>
  <div class="legend">
    <span class="yes">selected</span>
    <span class="no">not selected</span>
  </div>
  <svg id="chart" viewBox="0 0 1200 520" preserveAspectRatio="none"></svg>
  <div id="tooltip" class="tooltip"></div>
  <script>
    const rows = {payload};
    const svg = document.getElementById('chart');
    const tooltip = document.getElementById('tooltip');
    const width = 1200;
    const height = 520;
    const pad = {{ left: 70, right: 30, top: 30, bottom: 60 }};
    const innerW = width - pad.left - pad.right;
    const innerH = height - pad.top - pad.bottom;

    const closes = rows.map(r => r.close);
    const preds = rows.map(r => r.predicted_return);
    const minClose = Math.min(...closes);
    const maxClose = Math.max(...closes);
    const minPred = Math.min(...preds);
    const maxPred = Math.max(...preds);

    const x = i => pad.left + (i / Math.max(rows.length - 1, 1)) * innerW;
    const yClose = v => pad.top + (1 - (v - minClose) / Math.max(maxClose - minClose, 1e-6)) * (innerH * 0.62);
    const yPred = v => pad.top + innerH * 0.72 + (1 - (v - minPred) / Math.max(maxPred - minPred, 1e-6)) * (innerH * 0.22);

    let closePath = "";
    let predPath = "";
    rows.forEach((row, i) => {{
      closePath += (i === 0 ? "M" : "L") + x(i) + "," + yClose(row.close) + " ";
      predPath += (i === 0 ? "M" : "L") + x(i) + "," + yPred(row.predicted_return) + " ";
    }});

    svg.innerHTML = `
      <path d="${{closePath}}" fill="none" stroke="#64748b" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"></path>
      <path d="${{predPath}}" fill="none" stroke="#f59e0b" stroke-width="2.5" stroke-dasharray="5 4" stroke-linecap="round"></path>
      <line x1="${{pad.left}}" y1="${{pad.top + innerH * 0.72}}" x2="${{width - pad.right}}" y2="${{pad.top + innerH * 0.72}}" stroke="#e5e7eb" stroke-width="1.5"></line>
    `;

    rows.forEach((row, i) => {{
      const circle = document.createElementNS("http://www.w3.org/2000/svg", "circle");
      circle.setAttribute("cx", x(i));
      circle.setAttribute("cy", yClose(row.close));
      circle.setAttribute("r", row.selected ? 6 : 4);
      circle.setAttribute("fill", row.selected ? "#0f766e" : "#cbd5e1");
      circle.setAttribute("stroke", row.selected ? "#ffffff" : "none");
      circle.setAttribute("stroke-width", row.selected ? "2" : "0");
      circle.addEventListener("mousemove", event => {{
        tooltip.style.display = "block";
        tooltip.style.left = (event.clientX + 14) + "px";
        tooltip.style.top = (event.clientY + 14) + "px";
        tooltip.innerHTML = `
          <strong>${{row.date}}</strong><br>
          close=${{row.close}}<br>
          predicted_return=${{row.predicted_return}}<br>
          percentile=${{row.prediction_percentile}}<br>
          selected=${{row.selected ? 'yes' : 'no'}}<br>
          bucket=${{row.bucket_direction}} ${{row.bucket_pct}}%
        `;
      }});
      circle.addEventListener("mouseleave", () => {{ tooltip.style.display = "none"; }});
      svg.appendChild(circle);
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
