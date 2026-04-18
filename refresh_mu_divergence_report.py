from __future__ import annotations

import json
from html import escape
from pathlib import Path

import pandas as pd

import prepare as pr
import refresh_mu_shadow_board as shadow

ASSET_KEY = shadow.ASSET_KEY
RECENT_LIMIT = 25
OUTCOME_HORIZONS = (20, 60)
MIN_CASES_FOR_DIRECTIONAL_VERDICT = 8


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


def normalize_price_frame(raw_prices: pd.DataFrame) -> pd.DataFrame:
    frame = raw_prices.copy()
    frame.columns = [column.lower() for column in frame.columns]
    frame["date"] = pd.to_datetime(frame["date"]).dt.strftime("%Y-%m-%d")
    frame = frame.sort_values("date").reset_index(drop=True)
    for horizon in OUTCOME_HORIZONS:
        frame[f"future_return_{horizon}d"] = frame["close"].shift(-horizon) / frame["close"] - 1.0
    keep_columns = ["date", "close"] + [f"future_return_{horizon}d" for horizon in OUTCOME_HORIZONS]
    return frame[keep_columns]


def classify_outcome_bucket(row: pd.Series) -> str:
    live_state = str(row["live_state"])
    shadow_state = str(row["shadow_state"])
    if live_state == "selected" and shadow_state == "selected":
        return "both_selected"
    if live_state == "selected":
        return "live_selected_while_shadow_not"
    if shadow_state == "selected":
        return "shadow_selected_while_live_not"
    if live_state == "blocked" and shadow_state == "blocked":
        return "both_blocked"
    if live_state == "blocked" and shadow_state == "idle":
        return "live_blocked_shadow_idle"
    if live_state == "idle" and shadow_state == "blocked":
        return "shadow_blocked_live_idle"
    return "both_idle"


def verdict_for_bucket(bucket: str) -> str:
    verdicts = {
        "both_selected": "Shared conviction supports the current live line, not a challenger-only upgrade.",
        "live_selected_while_shadow_not": "Supports the current live line; the shadow challenger is still too restrictive here.",
        "shadow_selected_while_live_not": "Shadow catches some live misses, but this bucket alone is not strong enough to justify promotion.",
        "both_blocked": "Both models are interested but overlays block entry, so this stays in monitoring rather than promotion territory.",
        "live_blocked_shadow_idle": "Mostly an overlay asymmetry on the live side; this is not promotion evidence for the challenger.",
        "shadow_blocked_live_idle": "Mostly an overlay asymmetry on the shadow side; this currently adds more monitoring value than strategy value.",
        "both_idle": "Neither line is active, so this bucket is baseline context rather than promotion evidence.",
    }
    return verdicts.get(bucket, "Monitoring only.")


def comparison_owner(bucket: str) -> str:
    if bucket in {"live_selected_shadow_idle", "shadow_blocked_live_selected"}:
        return "live"
    if bucket in {"live_blocked_shadow_selected", "shadow_selected_live_idle"}:
        return "challenger"
    return "shared"


def bucket_promotion_verdict(owner: str, matured_cases: int, avg_future_return_60: float, hit_rate_60: float) -> str:
    if owner == "shared" or matured_cases < 3:
        return "inconclusive"
    supports_owner = avg_future_return_60 > 0.0 and hit_rate_60 >= 0.5
    if owner == "live":
        return "supports_live" if supports_owner else "supports_challenger"
    return "supports_challenger" if supports_owner else "supports_live"


def verdict_confidence(owner: str, matured_cases: int) -> str:
    if owner == "shared":
        return "context_only"
    if matured_cases < 3:
        return "very_low"
    if matured_cases < MIN_CASES_FOR_DIRECTIONAL_VERDICT:
        return "low"
    return "moderate"


def bucket_note(owner: str, verdict: str, matured_cases: int, bullish_pocket_cases: int) -> str:
    if owner == "shared":
        return "Shared-conviction or shared-idle bucket. This is context, not promotion evidence."
    if matured_cases < 3:
        return "Sample is too thin to treat this bucket as real promotion evidence."
    pocket_clause = (
        f" {bullish_pocket_cases} matured rows happened inside the bullish pocket."
        if bullish_pocket_cases
        else " Recent evidence does not lean on the bullish pocket."
    )
    if owner == "live" and verdict == "supports_live":
        return "When live diverges in its own favor, realized outcomes still back the official live line." + pocket_clause
    if owner == "live":
        return "Live-only divergence is underperforming, so this bucket currently helps the challenger case." + pocket_clause
    if owner == "challenger" and verdict == "supports_challenger":
        return "Challenger-only divergence is working well enough to add promotion pressure." + pocket_clause
    return "Challenger-only divergence is not strong enough, so this bucket currently helps the live case." + pocket_clause


def load_compare_frame() -> pd.DataFrame:
    raw_prices = pr.download_asset_prices()
    live_rows = shadow.read_live_rows(lookback_days=None)
    shadow_rows, _ = shadow.build_shadow_rows(lookback_days=None, raw_prices=raw_prices)
    context_frame = shadow.build_context_frame(raw_prices)
    compare = shadow.build_compare_frame(live_rows, shadow_rows, context_frame=context_frame)
    if compare.empty:
        raise ValueError("MU divergence compare frame is empty.")
    return compare


def attach_outcomes(compare_frame: pd.DataFrame, price_frame: pd.DataFrame) -> pd.DataFrame:
    merged = compare_frame.copy()
    merged["date"] = merged["date"].astype(str)
    merged = merged.merge(price_frame.drop(columns=["close"]), on="date", how="left")
    for horizon in OUTCOME_HORIZONS:
        value_column = f"future_return_{horizon}d"
        matured_column = f"matured_{horizon}d"
        hit_column = f"hit_{horizon}d"
        merged[matured_column] = merged[value_column].notna()
        merged[hit_column] = merged[value_column] > 0.0
    merged["outcome_bucket"] = merged.apply(classify_outcome_bucket, axis=1)
    merged["promotion_verdict"] = merged["outcome_bucket"].map(verdict_for_bucket)
    merged["promotion_bucket"] = merged["divergence_case"].astype(str).where(
        merged["divergence_case"].astype(str).str.strip() != "",
        merged["outcome_bucket"].astype(str),
    )
    merged["comparison_owner"] = merged["promotion_bucket"].astype(str).map(comparison_owner)
    return merged


def build_summary_frame(compare_with_outcomes: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    for bucket, group in compare_with_outcomes.groupby("outcome_bucket", sort=False):
        row: dict[str, object] = {
            "outcome_bucket": bucket,
            "row_count": int(len(group)),
            "avg_live_confidence_gap": round(float(group["live_confidence_gap"].mean()), 4),
            "avg_shadow_confidence_gap": round(float(group["shadow_confidence_gap"].mean()), 4),
            "avg_gap_delta": round(float(group["confidence_gap_delta"].mean()), 4),
            "promotion_verdict": verdict_for_bucket(bucket),
            "bullish_pocket_count": int(group["bullish_pocket"].fillna(False).sum()),
            "bullish_pocket_confirmed_count": int(group["bullish_pocket_confirmed"].fillna(False).sum()),
        }
        for horizon in OUTCOME_HORIZONS:
            value_column = f"future_return_{horizon}d"
            matured_column = f"matured_{horizon}d"
            matured = group.loc[group[matured_column]]
            row[f"matured_{horizon}d_count"] = int(len(matured))
            row[f"avg_return_{horizon}d"] = round(float(matured[value_column].mean()), 4) if not matured.empty else ""
            row[f"hit_rate_{horizon}d"] = round(float((matured[value_column] > 0.0).mean()), 4) if not matured.empty else ""
        rows.append(row)
    summary = pd.DataFrame(rows)
    order = [
        "both_selected",
        "live_selected_while_shadow_not",
        "shadow_selected_while_live_not",
        "both_blocked",
        "live_blocked_shadow_idle",
        "shadow_blocked_live_idle",
        "both_idle",
    ]
    if summary.empty:
        return summary
    summary["sort_key"] = summary["outcome_bucket"].map({name: idx for idx, name in enumerate(order)}).fillna(999)
    return summary.sort_values(["sort_key", "outcome_bucket"]).drop(columns=["sort_key"]).reset_index(drop=True)


def build_recent_frame(compare_with_outcomes: pd.DataFrame) -> pd.DataFrame:
    recent = compare_with_outcomes.loc[compare_with_outcomes["divergence_case"].astype(str) != ""].copy()
    if recent.empty:
        return recent
    columns = [
        "date",
        "comparison_state",
        "comparison_note",
        "comparison_owner",
        "divergence_case",
        "outcome_bucket",
        "bullish_pocket",
        "bullish_pocket_confirmed",
        "bullish_pocket_label",
        "live_signal",
        "shadow_signal",
        "live_probability",
        "shadow_probability",
        "live_confidence_gap",
        "shadow_confidence_gap",
        "confidence_gap_delta",
        "future_return_20d",
        "future_return_60d",
        "matured_20d",
        "matured_60d",
        "promotion_verdict",
    ]
    return recent[columns].tail(RECENT_LIMIT).reset_index(drop=True)


def build_bucket_summary(compare_with_outcomes: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    for bucket, bucket_frame in compare_with_outcomes.groupby("promotion_bucket", sort=False):
        matured = bucket_frame.loc[bucket_frame["matured_60d"]].copy()
        matured_cases = int(len(matured))
        avg_return = float(matured["future_return_60d"].mean()) if matured_cases else 0.0
        hit_rate = float((matured["future_return_60d"] > 0).mean()) if matured_cases else 0.0
        owner = comparison_owner(str(bucket))
        verdict = bucket_promotion_verdict(owner, matured_cases, avg_return, hit_rate)
        pocket_matured = matured.loc[matured["bullish_pocket"].fillna(False)]
        rows.append(
            {
                "row_type": "bucket",
                "promotion_bucket": str(bucket),
                "owner_side": owner,
                "promotion_verdict": verdict,
                "verdict_confidence": verdict_confidence(owner, matured_cases),
                "case_count": int(len(bucket_frame)),
                "matured_cases": matured_cases,
                "avg_future_return_60": round(avg_return, 4),
                "hit_rate_60": round(hit_rate, 4),
                "bullish_pocket_case_count": int(bucket_frame["bullish_pocket"].fillna(False).sum()),
                "bullish_pocket_matured_count": int(len(pocket_matured)),
                "bullish_pocket_avg_future_return_60": (
                    round(float(pocket_matured["future_return_60d"].mean()), 4) if not pocket_matured.empty else ""
                ),
                "bullish_pocket_hit_rate_60": (
                    round(float((pocket_matured["future_return_60d"] > 0).mean()), 4) if not pocket_matured.empty else ""
                ),
                "latest_date": str(bucket_frame["date"].iloc[-1]),
                "note": bucket_note(owner, verdict, matured_cases, int(len(pocket_matured))),
            }
        )
    summary = pd.DataFrame(rows)
    if summary.empty:
        return summary
    order = {
        "both_selected": 0,
        "live_selected_shadow_idle": 1,
        "shadow_blocked_live_selected": 2,
        "live_blocked_shadow_selected": 3,
        "shadow_selected_live_idle": 4,
        "both_blocked": 5,
        "both_idle": 6,
    }
    summary["sort_key"] = summary["promotion_bucket"].map(order).fillna(999)
    return summary.sort_values(["sort_key", "promotion_bucket"]).drop(columns=["sort_key"]).reset_index(drop=True)


def build_rollup_row(summary: pd.DataFrame) -> dict[str, object]:
    directional = summary.loc[summary["owner_side"].isin(["live", "challenger"])].copy()
    live_rows = directional.loc[directional["owner_side"] == "live"]
    challenger_rows = directional.loc[directional["owner_side"] == "challenger"]

    live_cases = int(live_rows["matured_cases"].sum())
    challenger_cases = int(challenger_rows["matured_cases"].sum())
    live_return = (
        float((live_rows["avg_future_return_60"] * live_rows["matured_cases"]).sum() / live_cases) if live_cases else 0.0
    )
    challenger_return = (
        float((challenger_rows["avg_future_return_60"] * challenger_rows["matured_cases"]).sum() / challenger_cases)
        if challenger_cases
        else 0.0
    )
    live_hit_rate = (
        float((live_rows["hit_rate_60"] * live_rows["matured_cases"]).sum() / live_cases) if live_cases else 0.0
    )
    challenger_hit_rate = (
        float((challenger_rows["hit_rate_60"] * challenger_rows["matured_cases"]).sum() / challenger_cases)
        if challenger_cases
        else 0.0
    )
    live_pocket_cases = int(live_rows["bullish_pocket_matured_count"].sum())
    challenger_pocket_cases = int(challenger_rows["bullish_pocket_matured_count"].sum())

    if min(live_cases, challenger_cases) < MIN_CASES_FOR_DIRECTIONAL_VERDICT:
        if live_return > challenger_return and live_hit_rate >= challenger_hit_rate:
            verdict = "supports_live"
            note = "Directional sample is still thin, so treat this as a live-leaning hold rather than a switch-ready call."
        elif challenger_return > live_return and challenger_hit_rate >= live_hit_rate:
            verdict = "supports_challenger"
            note = "Directional sample is still thin, so treat this as challenger pressure rather than a switch-ready call."
        else:
            verdict = "inconclusive"
            note = "Directional sample is still thin, and the evidence is mixed."
        confidence = "low"
    elif live_return > challenger_return and live_hit_rate >= challenger_hit_rate:
        verdict = "supports_live"
        note = "Live-favored divergence buckets are still stronger than challenger-favored buckets, so no promotion case yet."
        confidence = "moderate"
    elif challenger_return > live_return and challenger_hit_rate >= live_hit_rate:
        verdict = "supports_challenger"
        note = "Challenger-favored divergence buckets are now stronger, so promotion pressure is building."
        confidence = "moderate"
    else:
        verdict = "inconclusive"
        note = "Divergence evidence is mixed, so the promotion call stays inconclusive."
        confidence = "low"

    return {
        "row_type": "rollup",
        "promotion_bucket": "promotion_case_rollup",
        "owner_side": "aggregate",
        "promotion_verdict": verdict,
        "verdict_confidence": confidence,
        "case_count": live_cases + challenger_cases,
        "matured_cases": live_cases + challenger_cases,
        "avg_future_return_60": round(live_return - challenger_return, 4),
        "hit_rate_60": round(live_hit_rate - challenger_hit_rate, 4),
        "bullish_pocket_case_count": live_pocket_cases + challenger_pocket_cases,
        "bullish_pocket_matured_count": live_pocket_cases + challenger_pocket_cases,
        "bullish_pocket_avg_future_return_60": "",
        "bullish_pocket_hit_rate_60": "",
        "latest_date": "",
        "note": (
            f"live_cases={live_cases}, challenger_cases={challenger_cases}, "
            f"live_avg={live_return:.4f}, challenger_avg={challenger_return:.4f}, "
            f"live_hit={live_hit_rate:.4f}, challenger_hit={challenger_hit_rate:.4f}, "
            f"live_bullish_pocket_cases={live_pocket_cases}, challenger_bullish_pocket_cases={challenger_pocket_cases}. "
            f"{note}"
        ),
    }


def build_recent_divergence(compare_with_outcomes: pd.DataFrame) -> pd.DataFrame:
    recent = compare_with_outcomes.loc[compare_with_outcomes["comparison_owner"].isin(["live", "challenger"])].copy()
    if recent.empty:
        return recent
    recent["promotion_verdict"] = [
        "supports_live" if owner == "live" else "supports_challenger" for owner in recent["comparison_owner"]
    ]
    recent["verdict_confidence"] = recent["comparison_owner"].map(lambda _: "case_level")
    columns = [
        "date",
        "promotion_bucket",
        "comparison_owner",
        "divergence_case",
        "comparison_state",
        "bullish_pocket",
        "bullish_pocket_confirmed",
        "bullish_pocket_label",
        "live_signal",
        "shadow_signal",
        "future_return_20d",
        "future_return_60d",
        "matured_20d",
        "matured_60d",
        "promotion_verdict",
        "verdict_confidence",
    ]
    return recent[columns].tail(RECENT_LIMIT).reset_index(drop=True)


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
        recent_rows = "<tr><td colspan='9'>No recent divergence rows are available yet.</td></tr>"
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
                "</tr>"
            )
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>MU Divergence Outcome Report</title>
  <style>
    :root {{
      --bg: #f6f1e8;
      --card: #fffdf8;
      --line: #e7dcc9;
      --text: #1e2530;
      --muted: #5c6879;
      --accent: #9a6237;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      padding: 28px;
      font-family: "Segoe UI", Arial, sans-serif;
      background: linear-gradient(180deg, #f6f1e8 0%, #ede4d6 100%);
      color: var(--text);
    }}
    .hero {{
      margin-bottom: 24px;
    }}
    .hero h1 {{ margin: 0 0 8px; }}
    .hero p {{ margin: 0; color: var(--muted); line-height: 1.5; }}
    table {{
      width: 100%;
      border-collapse: collapse;
      background: rgba(255,255,255,0.86);
      border: 1px solid var(--line);
      border-radius: 16px;
      overflow: hidden;
      margin-bottom: 24px;
    }}
    th, td {{
      padding: 10px 12px;
      border-bottom: 1px solid var(--line);
      text-align: left;
      vertical-align: top;
      font-size: 14px;
    }}
    th {{
      background: #f5ecdf;
      color: var(--muted);
      font-size: 12px;
      text-transform: uppercase;
      letter-spacing: 0.04em;
    }}
    .callout {{
      padding: 16px 18px;
      border-radius: 16px;
      background: var(--card);
      border-left: 6px solid var(--accent);
      box-shadow: 0 10px 24px rgba(15, 23, 42, 0.05);
      margin-bottom: 24px;
    }}
  </style>
</head>
<body>
  <section class="hero">
    <h1>MU Divergence Outcome Report</h1>
    <p>Live stays on <strong>tb30 + top_12.5pct</strong>. The main challenger remains <strong>plain tb20 + top_12.5pct</strong>, and divergence monitoring is here to judge it rather than promote it early.</p>
    <p>Latest date: <strong>{escape(str(latest_row['date']))}</strong>. Latest comparison state: <strong>{escape(str(latest_row['comparison_state']))}</strong>. Latest divergence case: <strong>{escape(latest_divergence)}</strong>. Latest pocket lens: <strong>{escape(str(latest_row['bullish_pocket_label']))}</strong>.</p>
  </section>
  <section class="callout">
    Shadow has some edge on certain divergence days, but it is still not strong enough to justify a live switch. The bullish pocket is useful context, not a promotion trigger.
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
          <th>Shadow</th>
          <th>20d</th>
          <th>60d</th>
          <th>Verdict</th>
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
        recent_rows = "<tr><td colspan='8'>No recent directional divergences are available yet.</td></tr>"
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
  <title>MU Divergence Verdict</title>
  <style>
    body {{
      margin: 0;
      padding: 28px;
      font-family: "Segoe UI", Arial, sans-serif;
      background: #f6f1e8;
      color: #1e2530;
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
    .callout {{
      margin-bottom: 24px;
      padding: 16px 18px;
      background: #fffdf8;
      border-left: 6px solid #9a6237;
    }}
  </style>
</head>
<body>
  <h1>MU Divergence Verdict</h1>
  <div class="callout">
    This verdict layer is promotion-oriented monitoring only. It does not imply a live switch. The bullish pocket is tracked as added context because challenger-only disagreements look more credible there, but the current rollup still needs stronger evidence before any promotion call changes.
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
    compare = load_compare_frame()
    prices = normalize_price_frame(pr.download_asset_prices())
    with_outcomes = attach_outcomes(compare, prices)
    summary = build_summary_frame(with_outcomes)
    recent = build_recent_frame(with_outcomes)
    verdict_summary = build_bucket_summary(with_outcomes)
    verdict_rollup = pd.DataFrame([build_rollup_row(verdict_summary)])
    verdict_summary = pd.concat([verdict_summary, verdict_rollup], ignore_index=True)
    verdict_recent = build_recent_divergence(with_outcomes)

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
