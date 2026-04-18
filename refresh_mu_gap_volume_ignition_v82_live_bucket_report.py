from __future__ import annotations

import json
from html import escape
from pathlib import Path

import pandas as pd

import refresh_mu_divergence_report as base_divergence
import refresh_mu_gap_volume_ignition_v82_shadow as shadow

ASSET_KEY = shadow.ASSET_KEY
CASE_NAME = "live_selected_shadow_idle"
RECENT_LIMIT = 20


def get_output_dir() -> Path:
    return shadow.get_output_dir()


def get_summary_path() -> Path:
    return get_output_dir() / "live_bucket_summary.tsv"


def get_recent_path() -> Path:
    return get_output_dir() / "live_bucket_recent.tsv"


def get_html_path() -> Path:
    return get_output_dir() / "live_bucket_report.html"


def load_compare_with_outcomes() -> pd.DataFrame:
    raw_prices = shadow.download_asset_prices()
    live_rows = shadow.read_live_rows(lookback_days=None)
    shadow_rows, _ = shadow.build_shadow_rows(lookback_days=None, raw_prices=raw_prices)
    context_frame = shadow.build_context_frame(raw_prices)
    compare = shadow.build_compare_frame(live_rows, shadow_rows, context_frame=context_frame)
    if compare.empty:
        raise ValueError("MU v82 live bucket compare frame is empty.")
    prices = base_divergence.normalize_price_frame(raw_prices)
    return base_divergence.attach_outcomes(compare, prices)


def collect_non_overlap_episodes(frame: pd.DataFrame, min_gap_days: int = 60) -> pd.DataFrame:
    episodes: list[pd.Series] = []
    for _, row in frame.sort_values("date").iterrows():
        current_date = pd.to_datetime(row["date"])
        if not episodes:
            episodes.append(row)
            continue
        previous_date = pd.to_datetime(episodes[-1]["date"])
        if int((current_date - previous_date).days) >= min_gap_days:
            episodes.append(row)
    if not episodes:
        return frame.iloc[0:0].copy()
    return pd.DataFrame(episodes).reset_index(drop=True)


def summarize_bucket(compare_with_outcomes: pd.DataFrame, bucket: pd.DataFrame) -> pd.DataFrame:
    matured_20 = bucket.loc[bucket["matured_20d"]].copy()
    matured_60 = bucket.loc[bucket["matured_60d"]].copy()
    episodes = collect_non_overlap_episodes(matured_60, min_gap_days=60)
    year_counts = bucket["date"].astype(str).str[:4].value_counts().sort_values(ascending=False)
    latest_case_date = str(bucket["date"].iloc[-1]) if not bucket.empty else ""
    summary_rows = [
        {
            "metric": "monitor_verdict",
            "value": "hold_anchor_watch",
            "note": "Monitoring only. This bucket tracks dates where live fired while the exact v82 event rule stayed idle.",
        },
        {
            "metric": "shared_rows",
            "value": int(len(compare_with_outcomes)),
            "note": "Rows on the shared live-versus-v82 comparison axis.",
        },
        {
            "metric": "bucket_rows",
            "value": int(len(bucket)),
            "note": "Dates where live selected while the v82 rule did not match.",
        },
        {
            "metric": "bucket_non_overlap_60d_episodes",
            "value": int(len(episodes)),
            "note": "Greedy 60-day non-overlap episodes, used as a sample-quality sanity check.",
        },
        {
            "metric": "latest_case_date",
            "value": latest_case_date,
            "note": "Most recent live-selected, v82-idle date.",
        },
        {
            "metric": "future_return_20_avg",
            "value": round(float(matured_20["future_return_20d"].mean()), 4) if not matured_20.empty else "",
            "note": "Average 20-day realized return after live-only selection, using matured rows only.",
        },
        {
            "metric": "future_return_20_hit_rate",
            "value": round(float((matured_20["future_return_20d"] > 0).mean()), 4) if not matured_20.empty else "",
            "note": "Share of matured live-only rows with positive 20-day realized return.",
        },
        {
            "metric": "matured_20_count",
            "value": int(len(matured_20)),
            "note": "Number of live-only rows with 20-day outcomes available.",
        },
        {
            "metric": "future_return_60_avg",
            "value": round(float(matured_60["future_return_60d"].mean()), 4) if not matured_60.empty else "",
            "note": "Average 60-day realized return after live-only selection, using matured rows only.",
        },
        {
            "metric": "future_return_60_hit_rate",
            "value": round(float((matured_60["future_return_60d"] > 0).mean()), 4) if not matured_60.empty else "",
            "note": "Share of matured live-only rows with positive 60-day realized return.",
        },
        {
            "metric": "matured_60_count",
            "value": int(len(matured_60)),
            "note": "Number of live-only rows with 60-day outcomes available.",
        },
        {
            "metric": "episode_future_return_60_avg",
            "value": round(float(episodes["future_return_60d"].mean()), 4) if not episodes.empty else "",
            "note": "Average 60-day realized return across non-overlap episodes.",
        },
        {
            "metric": "max_year_share",
            "value": round(float(year_counts.iloc[0] / len(bucket)), 4) if not bucket.empty else "",
            "note": (
                f"Largest year concentration: {year_counts.index[0]} with {int(year_counts.iloc[0])} rows."
                if not bucket.empty
                else "No live-only bucket rows yet."
            ),
        },
        {
            "metric": "above_200dma_share",
            "value": round(float(bucket["above_200dma"].mean()), 4) if not bucket.empty else "",
            "note": "Share of live-only bucket rows above the 200-day moving average.",
        },
        {
            "metric": "slope_60_positive_share",
            "value": round(float(bucket["slope_60_positive"].mean()), 4) if not bucket.empty else "",
            "note": "Share of live-only bucket rows with positive 60-day slope.",
        },
        {
            "metric": "v82_full_match_share",
            "value": round(float((bucket["shadow_criteria_pass_count"] == 5).mean()), 4) if not bucket.empty else "",
            "note": "Should remain 0.0000 in this bucket because these are v82-idle rows.",
        },
        {
            "metric": "v82_four_of_five_share",
            "value": round(float((bucket["shadow_criteria_pass_count"] == 4).mean()), 4) if not bucket.empty else "",
            "note": "Share of live-only rows where v82 missed by exactly one rule leg.",
        },
        {
            "metric": "v82_pass_rate_median",
            "value": round(float(bucket["shadow_criteria_pass_rate"].median()), 4) if not bucket.empty else "",
            "note": "Median fraction of v82 rule legs that passed on live-only dates.",
        },
    ]
    return pd.DataFrame(summary_rows)


def build_recent_frame(bucket: pd.DataFrame) -> pd.DataFrame:
    columns = [
        "date",
        "close",
        "future_return_20d",
        "future_return_60d",
        "live_signal",
        "live_probability",
        "live_cutoff",
        "live_confidence_gap",
        "shadow_signal",
        "shadow_criteria_pass_count",
        "shadow_criteria_pass_rate",
        "shadow_overnight_gap",
        "shadow_volume_vs_20",
        "shadow_range_z_20",
        "shadow_intraday_return",
        "shadow_breakout_20",
        "bullish_pocket_label",
    ]
    if bucket.empty:
        return bucket.iloc[0:0].copy()
    recent = bucket[columns].sort_values("date").tail(RECENT_LIMIT).reset_index(drop=True)
    recent["date"] = pd.to_datetime(recent["date"]).dt.strftime("%Y-%m-%d")
    return recent


def render_html(summary: pd.DataFrame, recent: pd.DataFrame) -> str:
    summary_map = dict(zip(summary["metric"], summary["value"]))
    rows = ""
    if recent.empty:
        rows = "<tr><td colspan='10'>No live-only anchor rows are available yet.</td></tr>"
    else:
        for _, row in recent.iloc[::-1].iterrows():
            rows += (
                "<tr>"
                f"<td>{escape(str(row['date']))}</td>"
                f"<td>{escape(str(row['bullish_pocket_label']))}</td>"
                f"<td>{escape(str(row['live_signal']))}</td>"
                f"<td>{escape(str(row['shadow_signal']))}</td>"
                f"<td>{escape(str(row['shadow_criteria_pass_count']))}/5</td>"
                f"<td>{escape(str(row['shadow_overnight_gap']))}</td>"
                f"<td>{escape(str(row['shadow_volume_vs_20']))}</td>"
                f"<td>{escape(str(row['future_return_20d']))}</td>"
                f"<td>{escape(str(row['future_return_60d']))}</td>"
                f"<td>{escape(str(row['live_confidence_gap']))}</td>"
                "</tr>"
            )

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>MU Gap Volume Ignition v82 Live Bucket Monitor</title>
  <style>
    body {{
      margin: 0;
      padding: 28px;
      font-family: "Segoe UI", Arial, sans-serif;
      background: #f6f1e8;
      color: #1e2530;
    }}
    .hero {{
      margin-bottom: 22px;
      padding: 18px 20px;
      background: #fffdf8;
      border-left: 6px solid #9a6237;
    }}
    .hero p {{
      margin: 8px 0 0;
      line-height: 1.5;
      color: #5c6879;
    }}
    .grid {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
      gap: 12px;
      margin-bottom: 24px;
    }}
    .card {{
      background: #fffdf8;
      border: 1px solid #e7dcc9;
      padding: 14px;
    }}
    .card .label {{
      font-size: 12px;
      text-transform: uppercase;
      color: #5c6879;
      margin-bottom: 6px;
    }}
    .card .value {{
      font-size: 24px;
      font-weight: 700;
    }}
    table {{
      width: 100%;
      border-collapse: collapse;
      background: #fffdf8;
      border: 1px solid #e7dcc9;
    }}
    th, td {{
      padding: 10px 12px;
      border-bottom: 1px solid #e7dcc9;
      text-align: left;
      vertical-align: top;
    }}
    th {{
      background: #f5ecdf;
      font-size: 12px;
      text-transform: uppercase;
      color: #5c6879;
    }}
  </style>
</head>
<body>
  <section class="hero">
    <h1>MU Gap Volume Ignition v82 Live Bucket Monitor</h1>
    <p>This is the live-supporting hold-anchor bucket for the exact v82 sidecar: dates where live selected while the v82 ignition rule stayed idle.</p>
    <p>Latest live-only anchor date: <strong>{escape(str(summary_map.get('latest_case_date', '')))}</strong>. Current verdict: <strong>{escape(str(summary_map.get('monitor_verdict', 'hold_anchor_watch')))}</strong>.</p>
  </section>
  <section class="grid">
    <div class="card"><div class="label">Bucket Rows</div><div class="value">{escape(str(summary_map.get('bucket_rows', '')))}</div></div>
    <div class="card"><div class="label">60d Episodes</div><div class="value">{escape(str(summary_map.get('bucket_non_overlap_60d_episodes', '')))}</div></div>
    <div class="card"><div class="label">60d Avg</div><div class="value">{escape(str(summary_map.get('future_return_60_avg', '')))}</div></div>
    <div class="card"><div class="label">60d Hit Rate</div><div class="value">{escape(str(summary_map.get('future_return_60_hit_rate', '')))}</div></div>
    <div class="card"><div class="label">4 of 5 Share</div><div class="value">{escape(str(summary_map.get('v82_four_of_five_share', '')))}</div></div>
    <div class="card"><div class="label">Pocket Share</div><div class="value">{escape(str(summary_map.get('above_200dma_share', '')))}</div></div>
  </section>
  <section>
    <h2>Recent Live-Only Anchor Rows</h2>
    <table>
      <thead>
        <tr>
          <th>Date</th>
          <th>Pocket</th>
          <th>Live</th>
          <th>v82</th>
          <th>Pass Count</th>
          <th>Gap</th>
          <th>Volume</th>
          <th>20d</th>
          <th>60d</th>
          <th>Live Gap</th>
        </tr>
      </thead>
      <tbody>{rows}</tbody>
    </table>
  </section>
</body>
</html>"""


def main() -> None:
    shadow.ensure_output_dir()
    compare_with_outcomes = load_compare_with_outcomes()
    bucket = compare_with_outcomes.loc[compare_with_outcomes["divergence_case"] == CASE_NAME].copy().reset_index(drop=True)
    summary = summarize_bucket(compare_with_outcomes, bucket)
    recent = build_recent_frame(bucket)

    summary.to_csv(get_summary_path(), sep="\t", index=False)
    recent.to_csv(get_recent_path(), sep="\t", index=False)
    get_html_path().write_text(render_html(summary, recent), encoding="utf-8")

    print(
        json.dumps(
            {
                "asset_key": ASSET_KEY,
                "summary_path": str(get_summary_path()),
                "recent_path": str(get_recent_path()),
                "html_path": str(get_html_path()),
                "bucket_rows": int(len(bucket)),
                "latest_case_date": str(summary.loc[summary["metric"] == "latest_case_date", "value"].iloc[0]),
                "monitor_verdict": str(summary.loc[summary["metric"] == "monitor_verdict", "value"].iloc[0]),
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
