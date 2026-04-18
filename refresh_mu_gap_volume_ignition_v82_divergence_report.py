from __future__ import annotations

import json
from html import escape
from pathlib import Path

import pandas as pd

import refresh_mu_divergence_report as base_report
import refresh_mu_gap_volume_ignition_v82_shadow as shadow

ASSET_KEY = shadow.ASSET_KEY


def get_output_dir() -> Path:
    return shadow.get_output_dir()


def get_summary_path() -> Path:
    return get_output_dir() / "divergence_outcome_summary.tsv"


def get_recent_path() -> Path:
    return get_output_dir() / "divergence_outcome_recent.tsv"


def get_html_path() -> Path:
    return get_output_dir() / "divergence_outcome_report.html"


def get_verdict_summary_path() -> Path:
    return get_output_dir() / "divergence_verdict_summary.tsv"


def get_verdict_recent_path() -> Path:
    return get_output_dir() / "divergence_verdict_recent.tsv"


def get_verdict_html_path() -> Path:
    return get_output_dir() / "divergence_verdict_report.html"


def load_compare_frame() -> pd.DataFrame:
    raw_prices = shadow.download_asset_prices()
    live_rows = shadow.read_live_rows(lookback_days=None)
    shadow_rows, _ = shadow.build_shadow_rows(lookback_days=None, raw_prices=raw_prices)
    context_frame = shadow.build_context_frame(raw_prices)
    compare = shadow.build_compare_frame(live_rows, shadow_rows, context_frame=context_frame)
    if compare.empty:
        raise ValueError("MU v82 divergence compare frame is empty.")
    return compare


def build_recent_frame(compare_with_outcomes: pd.DataFrame) -> pd.DataFrame:
    recent = base_report.build_recent_frame(compare_with_outcomes)
    if recent.empty:
        return recent
    evidence = compare_with_outcomes.loc[
        compare_with_outcomes["divergence_case"].astype(str) != "",
        ["date", "shadow_criteria_pass_count", "shadow_criteria_pass_rate"],
    ].copy()
    evidence["date"] = evidence["date"].astype(str)
    recent["date"] = recent["date"].astype(str)
    return recent.merge(evidence, on="date", how="left")


def render_html(summary: pd.DataFrame, recent: pd.DataFrame, latest_row: pd.Series) -> str:
    latest_divergence = str(latest_row.get("divergence_case", "")).strip() or "none"
    summary_rows = ""
    for _, row in summary.iterrows():
        summary_rows += (
            "<tr>"
            f"<td>{escape(str(row['outcome_bucket']))}</td>"
            f"<td>{int(row['row_count'])}</td>"
            f"<td>{escape(str(row['matured_20d_count']))}</td>"
            f"<td>{escape(str(row['avg_return_20d']))}</td>"
            f"<td>{escape(str(row['hit_rate_20d']))}</td>"
            f"<td>{escape(str(row['matured_60d_count']))}</td>"
            f"<td>{escape(str(row['avg_return_60d']))}</td>"
            f"<td>{escape(str(row['hit_rate_60d']))}</td>"
            f"<td>{escape(str(row['bullish_pocket_count']))}</td>"
            f"<td>{escape(str(row['promotion_verdict']))}</td>"
            "</tr>"
        )

    recent_rows = ""
    if recent.empty:
        recent_rows = "<tr><td colspan='10'>No recent live-vs-v82 divergence rows are available yet.</td></tr>"
    else:
        for _, row in recent.iloc[::-1].iterrows():
            recent_rows += (
                "<tr>"
                f"<td>{escape(str(row['date']))}</td>"
                f"<td>{escape(str(row['divergence_case']))}</td>"
                f"<td>{escape(str(row['comparison_owner']))}</td>"
                f"<td>{escape(str(row['bullish_pocket_label']))}</td>"
                f"<td>{escape(str(row['live_signal']))}</td>"
                f"<td>{escape(str(row['shadow_signal']))}</td>"
                f"<td>{escape(str(row['future_return_20d']))}</td>"
                f"<td>{escape(str(row['future_return_60d']))}</td>"
                f"<td>{escape(str(row['promotion_verdict']))}</td>"
                f"<td>{escape(str(row.get('shadow_criteria_pass_count', '')))}</td>"
                "</tr>"
            )

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>MU Gap Volume Ignition v82 Divergence Report</title>
  <style>
    body {{
      margin: 0;
      padding: 28px;
      font-family: "Segoe UI", Arial, sans-serif;
      background: #f6f1e8;
      color: #1e2530;
    }}
    .hero {{
      margin-bottom: 24px;
    }}
    .hero p {{
      margin: 6px 0 0;
      color: #5c6879;
      line-height: 1.5;
    }}
    .callout {{
      padding: 16px 18px;
      border-radius: 16px;
      background: #fffdf8;
      border-left: 6px solid #9a6237;
      margin-bottom: 24px;
    }}
    table {{
      width: 100%;
      border-collapse: collapse;
      background: #fffdf8;
      border: 1px solid #e7dcc9;
      margin-bottom: 24px;
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
    <h1>MU Gap Volume Ignition v82 Divergence Report</h1>
    <p>Live stays on the official MU lane. This report measures the exact v82 event rule as a research challenger only: overnight_gap>=0.5%, volume_vs_20>=0.50, range_z_20>=0.50, intraday_return>=0, breakout_20==1.</p>
    <p>Latest date: <strong>{escape(str(latest_row['date']))}</strong>. Latest comparison state: <strong>{escape(str(latest_row['comparison_state']))}</strong>. Latest divergence case: <strong>{escape(latest_divergence)}</strong>. Latest pocket lens: <strong>{escape(str(latest_row['bullish_pocket_label']))}</strong>.</p>
  </section>
  <section class="callout">
    This is evidence collection only. The v82 lane can pressure the live call if its challenger-only rows mature well, but it does not change live by itself.
  </section>
  <section>
    <h2>Outcome Summary</h2>
    <table>
      <thead>
        <tr>
          <th>Bucket</th>
          <th>Rows</th>
          <th>Matured 20d</th>
          <th>Avg 20d</th>
          <th>Hit 20d</th>
          <th>Matured 60d</th>
          <th>Avg 60d</th>
          <th>Hit 60d</th>
          <th>Bullish Pocket Rows</th>
          <th>Promotion Verdict</th>
        </tr>
      </thead>
      <tbody>{summary_rows}</tbody>
    </table>
  </section>
  <section>
    <h2>Recent Divergence Rows</h2>
    <table>
      <thead>
        <tr>
          <th>Date</th>
          <th>Case</th>
          <th>Owner</th>
          <th>Pocket</th>
          <th>Live</th>
          <th>v82</th>
          <th>20d</th>
          <th>60d</th>
          <th>Verdict</th>
          <th>Pass Count</th>
        </tr>
      </thead>
      <tbody>{recent_rows}</tbody>
    </table>
  </section>
</body>
</html>"""


def render_verdict_html(summary: pd.DataFrame, recent: pd.DataFrame) -> str:
    summary_rows = ""
    for _, row in summary.iterrows():
        summary_rows += (
            "<tr>"
            f"<td>{escape(str(row['promotion_bucket']))}</td>"
            f"<td>{escape(str(row['owner_side']))}</td>"
            f"<td>{escape(str(row['promotion_verdict']))}</td>"
            f"<td>{escape(str(row['verdict_confidence']))}</td>"
            f"<td>{escape(str(row['matured_cases']))}</td>"
            f"<td>{escape(str(row['avg_future_return_60']))}</td>"
            f"<td>{escape(str(row['hit_rate_60']))}</td>"
            f"<td>{escape(str(row['bullish_pocket_matured_count']))}</td>"
            f"<td>{escape(str(row['note']))}</td>"
            "</tr>"
        )

    recent_rows = ""
    if recent.empty:
        recent_rows = "<tr><td colspan='8'>No recent directional live-vs-v82 divergences are available yet.</td></tr>"
    else:
        for _, row in recent.iloc[::-1].iterrows():
            recent_rows += (
                "<tr>"
                f"<td>{escape(str(row['date']))}</td>"
                f"<td>{escape(str(row['promotion_bucket']))}</td>"
                f"<td>{escape(str(row['comparison_owner']))}</td>"
                f"<td>{escape(str(row['bullish_pocket_label']))}</td>"
                f"<td>{escape(str(row['future_return_20d']))}</td>"
                f"<td>{escape(str(row['future_return_60d']))}</td>"
                f"<td>{escape(str(row['promotion_verdict']))}</td>"
                f"<td>{escape(str(row['verdict_confidence']))}</td>"
                "</tr>"
            )

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>MU Gap Volume Ignition v82 Divergence Verdict</title>
  <style>
    body {{
      margin: 0;
      padding: 28px;
      font-family: "Segoe UI", Arial, sans-serif;
      background: #f6f1e8;
      color: #1e2530;
    }}
    .callout {{
      margin-bottom: 24px;
      padding: 16px 18px;
      background: #fffdf8;
      border-left: 6px solid #9a6237;
    }}
    table {{
      width: 100%;
      border-collapse: collapse;
      margin-bottom: 24px;
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
  <h1>MU Gap Volume Ignition v82 Divergence Verdict</h1>
  <div class="callout">
    Promotion-oriented monitoring only. This keeps the exact v82 event rule separate from live while we judge whether its directional divergences actually mature better than the official MU line.
  </div>
  <h2>Verdict Summary</h2>
  <table>
    <thead>
      <tr>
        <th>Bucket</th>
        <th>Owner</th>
        <th>Verdict</th>
        <th>Confidence</th>
        <th>Matured 60d</th>
        <th>Avg 60d</th>
        <th>Hit 60d</th>
        <th>Bullish Pocket Matured</th>
        <th>Note</th>
      </tr>
    </thead>
    <tbody>{summary_rows}</tbody>
  </table>
  <h2>Recent Directional Divergences</h2>
  <table>
    <thead>
      <tr>
        <th>Date</th>
        <th>Bucket</th>
        <th>Owner</th>
        <th>Pocket</th>
        <th>20d</th>
        <th>60d</th>
        <th>Verdict</th>
        <th>Confidence</th>
      </tr>
    </thead>
    <tbody>{recent_rows}</tbody>
  </table>
</body>
</html>"""


def main() -> None:
    shadow.ensure_output_dir()
    compare = load_compare_frame()
    prices = base_report.normalize_price_frame(shadow.download_asset_prices())
    with_outcomes = base_report.attach_outcomes(compare, prices)
    summary = base_report.build_summary_frame(with_outcomes)
    recent = build_recent_frame(with_outcomes)
    verdict_summary = base_report.build_bucket_summary(with_outcomes)
    verdict_rollup = pd.DataFrame([base_report.build_rollup_row(verdict_summary)])
    verdict_summary = pd.concat([verdict_summary, verdict_rollup], ignore_index=True)
    verdict_recent = base_report.build_recent_divergence(with_outcomes)

    summary.to_csv(get_summary_path(), sep="\t", index=False)
    recent.to_csv(get_recent_path(), sep="\t", index=False)
    get_html_path().write_text(render_html(summary, recent, with_outcomes.iloc[-1]), encoding="utf-8")

    verdict_summary.to_csv(get_verdict_summary_path(), sep="\t", index=False)
    verdict_recent.to_csv(get_verdict_recent_path(), sep="\t", index=False)
    get_verdict_html_path().write_text(render_verdict_html(verdict_summary, verdict_recent), encoding="utf-8")

    latest = with_outcomes.iloc[-1]
    rollup = verdict_summary.loc[verdict_summary["row_type"] == "rollup"].iloc[0]
    print(
        json.dumps(
            {
                "asset_key": ASSET_KEY,
                "summary_path": str(get_summary_path()),
                "recent_path": str(get_recent_path()),
                "html_path": str(get_html_path()),
                "verdict_summary_path": str(get_verdict_summary_path()),
                "verdict_recent_path": str(get_verdict_recent_path()),
                "verdict_html_path": str(get_verdict_html_path()),
                "latest_date": str(latest["date"]),
                "latest_comparison_state": str(latest["comparison_state"]),
                "latest_divergence_case": str(latest["divergence_case"]),
                "latest_bullish_pocket_label": str(latest["bullish_pocket_label"]),
                "promotion_case_rollup": str(rollup["promotion_verdict"]),
                "verdict_confidence": str(rollup["verdict_confidence"]),
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
