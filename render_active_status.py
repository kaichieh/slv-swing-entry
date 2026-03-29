from __future__ import annotations

import json
from html import escape

import pandas as pd

import asset_config as ac


def load_rows() -> list[dict[str, object]]:
    frame = pd.read_csv(ac.get_active_status_output_path(), sep="\t")
    rows: list[dict[str, object]] = []
    for _, row in frame.iterrows():
        rows.append(
            {
                "line_id": str(row["line_id"]),
                "lane_type": str(row["lane_type"]),
                "role": str(row["role"]),
                "preferred": bool(row["preferred"]),
                "status": str(row["status"]),
                "recent_selected_count": int(row["recent_selected_count"]),
                "latest_date": "" if pd.isna(row["latest_date"]) else str(row["latest_date"]),
                "latest_value": None if pd.isna(row["latest_value"]) else float(row["latest_value"]),
                "latest_selected": bool(row["latest_selected"]),
                "cutoff": None if pd.isna(row["cutoff"]) else float(row["cutoff"]),
                "last_selected_date": "" if pd.isna(row["last_selected_date"]) else str(row["last_selected_date"]),
                "usage_note": str(row["usage_note"]),
            }
        )
    return rows


def status_color(status: str, preferred: bool) -> str:
    if preferred:
        return "#0f766e"
    if "inactive" in status:
        return "#94a3b8"
    if "secondary" in status:
        return "#d97706"
    return "#2563eb"


def build_card(row: dict[str, object]) -> str:
    color = status_color(str(row["status"]), bool(row["preferred"]))
    latest_value = "n/a" if row["latest_value"] is None else f"{float(row['latest_value']):.6f}"
    cutoff = "n/a" if row["cutoff"] is None else f"{float(row['cutoff']):.6f}"
    latest_selected = "yes" if row["latest_selected"] else "no"
    preferred_badge = "Preferred" if row["preferred"] else "Secondary"
    return f"""
    <section class="card" style="--accent:{color}">
      <div class="card-top">
        <div>
          <div class="eyebrow">{escape(str(row["lane_type"]))}</div>
          <h2>{escape(str(row["line_id"]))}</h2>
        </div>
        <div class="badge">{escape(preferred_badge)}</div>
      </div>
      <p class="note">{escape(str(row["usage_note"]))}</p>
      <dl class="stats">
        <div><dt>role</dt><dd>{escape(str(row["role"]))}</dd></div>
        <div><dt>status</dt><dd>{escape(str(row["status"]))}</dd></div>
        <div><dt>recent count</dt><dd>{row["recent_selected_count"]}</dd></div>
        <div><dt>latest date</dt><dd>{escape(str(row["latest_date"]) or "n/a")}</dd></div>
        <div><dt>latest value</dt><dd>{latest_value}</dd></div>
        <div><dt>latest selected</dt><dd>{latest_selected}</dd></div>
        <div><dt>cutoff</dt><dd>{cutoff}</dd></div>
        <div><dt>last selected</dt><dd>{escape(str(row["last_selected_date"]) or "n/a")}</dd></div>
      </dl>
    </section>
    """


def build_html(rows: list[dict[str, object]]) -> str:
    title = f"{ac.get_asset_symbol()} Active Status"
    cards = "\n".join(build_card(row) for row in rows)
    preferred = next((row for row in rows if row["preferred"]), None)
    summary = (
        f"Preferred line: {preferred['line_id']} | status={preferred['status']} | recent_count={preferred['recent_selected_count']}"
        if preferred
        else "No preferred line"
    )
    payload = json.dumps(rows, ensure_ascii=False)
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>{escape(title)}</title>
  <style>
    :root {{
      color-scheme: light;
      --bg: #f7f4ed;
      --text: #172033;
      --muted: #5b6474;
      --card: #fffdf8;
      --line: #e8dfcf;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      font-family: "Segoe UI", Arial, sans-serif;
      background: linear-gradient(180deg, #f7f4ed 0%, #efe8d8 100%);
      color: var(--text);
      padding: 28px;
    }}
    .hero {{
      margin-bottom: 20px;
    }}
    .hero h1 {{
      margin: 0 0 8px;
      font-size: 30px;
    }}
    .hero p {{
      margin: 0;
      color: var(--muted);
      font-size: 15px;
    }}
    .grid {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
      gap: 16px;
      margin-top: 20px;
    }}
    .card {{
      background: var(--card);
      border: 1px solid var(--line);
      border-top: 5px solid var(--accent);
      border-radius: 18px;
      padding: 18px;
      box-shadow: 0 10px 24px rgba(15, 23, 42, 0.06);
    }}
    .card-top {{
      display: flex;
      justify-content: space-between;
      gap: 12px;
      align-items: start;
      margin-bottom: 12px;
    }}
    .eyebrow {{
      color: var(--muted);
      font-size: 12px;
      text-transform: uppercase;
      letter-spacing: 0.08em;
      margin-bottom: 4px;
    }}
    h2 {{
      margin: 0;
      font-size: 21px;
      line-height: 1.2;
    }}
    .badge {{
      background: color-mix(in srgb, var(--accent) 14%, white);
      color: var(--accent);
      border-radius: 999px;
      padding: 6px 10px;
      font-size: 12px;
      font-weight: 700;
      white-space: nowrap;
    }}
    .note {{
      margin: 0 0 14px;
      color: var(--muted);
      line-height: 1.5;
      min-height: 48px;
    }}
    .stats {{
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 10px 12px;
      margin: 0;
    }}
    .stats div {{
      padding: 10px 12px;
      background: #faf6ee;
      border-radius: 12px;
      border: 1px solid #efe5d4;
    }}
    dt {{
      font-size: 12px;
      color: var(--muted);
      text-transform: uppercase;
      letter-spacing: 0.06em;
      margin-bottom: 4px;
    }}
    dd {{
      margin: 0;
      font-size: 14px;
      font-weight: 600;
    }}
    .dump {{
      margin-top: 22px;
      padding: 14px 16px;
      background: rgba(255,255,255,0.65);
      border-radius: 16px;
      border: 1px solid var(--line);
      color: var(--muted);
      font-size: 13px;
      overflow: auto;
      white-space: pre-wrap;
    }}
  </style>
</head>
<body>
  <div class="hero">
    <h1>{escape(title)}</h1>
    <p>{escape(summary)}</p>
  </div>
  <div class="grid">
    {cards}
  </div>
  <div class="dump">{escape(payload)}</div>
</body>
</html>"""


def main() -> None:
    rows = load_rows()
    output_path = ac.get_active_status_chart_path()
    output_path.write_text(build_html(rows), encoding="utf-8")
    preferred = next((row for row in rows if row["preferred"]), None)
    print(
        json.dumps(
            {
                "asset_key": ac.get_asset_key(),
                "output_path": str(output_path),
                "rows": len(rows),
                "preferred_line": preferred["line_id"] if preferred else None,
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
