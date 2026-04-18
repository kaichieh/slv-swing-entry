from __future__ import annotations

import json
from dataclasses import dataclass
from html import escape
from pathlib import Path

import numpy as np
import pandas as pd

import asset_config as ac
import predict_latest as pl
from prepare import DatasetSplit, FEATURE_COLUMNS, TARGET_COLUMN, apply_label_mode, load_dataset_frame, split_indices

ASSET_KEY = "mu"
LIVE_LABEL_MODE = "future-return-top-bottom-30pct"
SHADOW_LABEL_MODE = "future-return-top-bottom-20pct"
EXECUTION_RULE = "top_11_5pct"
EXTRA_FEATURES = ("ret_60", "vol_ratio_20_120")
CASE_NAME = "live_selected_shadow_idle"
RECENT_LIMIT = 20


@dataclass(frozen=True)
class ModelBundle:
    label_mode: str
    feature_names: list[str]
    splits: dict[str, DatasetSplit]
    artifacts: dict[str, object]
    historical_probabilities: np.ndarray
    execution_cutoff: float


def get_output_dir() -> Path:
    return ac.get_asset_dir(ASSET_KEY)


def get_summary_path() -> Path:
    return get_output_dir() / "live_bucket_summary.tsv"


def get_recent_path() -> Path:
    return get_output_dir() / "live_bucket_recent.tsv"


def get_html_path() -> Path:
    return get_output_dir() / "live_bucket_report.html"


def build_frame_for_label(base_frame: pd.DataFrame, label_mode: str) -> pd.DataFrame:
    train_end, _ = split_indices(len(base_frame))
    labels = apply_label_mode(
        base_frame[TARGET_COLUMN].to_numpy(dtype=float),
        base_frame["future_return_60"].to_numpy(dtype=float),
        label_mode,
        train_end=train_end,
    )
    frame = base_frame.copy()
    frame[TARGET_COLUMN] = labels
    return frame.dropna(subset=[TARGET_COLUMN]).reset_index(drop=True)


def build_splits(frame: pd.DataFrame, feature_names: list[str]) -> dict[str, DatasetSplit]:
    train_end, valid_end = split_indices(len(frame))
    split_map = {
        "train": frame.iloc[:train_end].copy(),
        "validation": frame.iloc[train_end:valid_end].copy(),
        "test": frame.iloc[valid_end:].copy(),
    }
    output: dict[str, DatasetSplit] = {}
    for name, split_frame in split_map.items():
        output[name] = DatasetSplit(
            features=split_frame[feature_names].to_numpy(dtype=np.float32),
            labels=split_frame[TARGET_COLUMN].to_numpy(dtype=np.float32),
            frame=split_frame,
        )
    return output


def fit_bundle(base_frame: pd.DataFrame, label_mode: str) -> ModelBundle:
    feature_names = list(FEATURE_COLUMNS) + list(EXTRA_FEATURES)
    frame = build_frame_for_label(base_frame, label_mode)
    splits = build_splits(frame, feature_names)
    artifacts = pl.fit_logistic_model(splits, feature_names)
    historical_probabilities = pl.build_history_probabilities(artifacts, splits, feature_names)
    execution_cutoff = float(
        pl.resolve_execution_cutoff(EXECUTION_RULE, float(artifacts["threshold"]), historical_probabilities)
    )
    return ModelBundle(
        label_mode=label_mode,
        feature_names=feature_names,
        splits=splits,
        artifacts=artifacts,
        historical_probabilities=historical_probabilities,
        execution_cutoff=execution_cutoff,
    )


def build_snapshot(row: pd.Series) -> dict[str, float]:
    return {name: float(row[name]) for name in row.index if name != "date"}


def derive_state(
    probability: float,
    execution_cutoff: float,
    historical_probabilities: np.ndarray,
    row: pd.Series,
) -> tuple[str, str, float]:
    raw_signal, _ = pl.classify_signal(float(probability), float(execution_cutoff), historical_probabilities)
    adjusted_signal, _ = pl.apply_buy_point_overlay(raw_signal, build_snapshot(row), asset_key=ASSET_KEY)
    confidence_gap = float(probability) - float(execution_cutoff)
    if probability < execution_cutoff:
        return "idle", adjusted_signal, confidence_gap
    if adjusted_signal == "no_entry":
        return "blocked", adjusted_signal, confidence_gap
    return "selected", adjusted_signal, confidence_gap


def score_bundle(bundle: ModelBundle, frame: pd.DataFrame, prefix: str) -> pd.DataFrame:
    matrix, _ = pl.score_latest_row(bundle.artifacts, bundle.feature_names, bundle.artifacts["train_frame"], frame)
    probabilities = pl.predict_probabilities(bundle.artifacts, matrix)
    rows: list[dict[str, object]] = []
    for probability, (_, row) in zip(probabilities, frame.iterrows()):
        state, signal, gap = derive_state(
            float(probability),
            bundle.execution_cutoff,
            bundle.historical_probabilities,
            row,
        )
        rows.append(
            {
                f"{prefix}_probability": round(float(probability), 6),
                f"{prefix}_cutoff": round(float(bundle.execution_cutoff), 6),
                f"{prefix}_gap": round(float(gap), 6),
                f"{prefix}_state": state,
                f"{prefix}_signal": signal,
            }
        )
    return pd.DataFrame(rows)


def build_compare_frame(base_frame: pd.DataFrame, live_bundle: ModelBundle, shadow_bundle: ModelBundle) -> pd.DataFrame:
    shared_start = max(
        live_bundle.splits["validation"].frame["date"].iloc[0],
        shadow_bundle.splits["validation"].frame["date"].iloc[0],
    )
    compare = base_frame.loc[base_frame["date"] >= shared_start].copy().reset_index(drop=True)
    compare["future_return_20"] = compare["close"].shift(-20) / compare["close"] - 1.0
    compare["future_return_60"] = compare["close"].shift(-60) / compare["close"] - 1.0
    compare = pd.concat(
        [compare, score_bundle(live_bundle, compare, "live"), score_bundle(shadow_bundle, compare, "shadow")],
        axis=1,
    )
    compare["above_200dma"] = compare["above_200dma_flag"].fillna(0.0) >= 0.5
    compare["slope_60_positive"] = compare["slope_60"].fillna(0.0) > 0.0
    compare["bullish_pocket_label"] = np.where(
        compare["above_200dma"] & compare["slope_60_positive"],
        "above_200dma_and_slope_60_positive",
        np.where(compare["above_200dma"], "above_200dma", "outside_bullish_pocket"),
    )
    compare["gap_spread"] = compare["live_gap"] - compare["shadow_gap"]
    compare["case"] = "live_" + compare["live_state"].astype(str) + "_shadow_" + compare["shadow_state"].astype(str)
    return compare


def collect_non_overlap_episodes(frame: pd.DataFrame, min_gap_days: int = 60) -> pd.DataFrame:
    episodes: list[pd.Series] = []
    for _, row in frame.sort_values("date").iterrows():
        if not episodes or int((row["date"] - episodes[-1]["date"]).days) >= min_gap_days:
            episodes.append(row)
    if not episodes:
        return frame.iloc[0:0].copy()
    return pd.DataFrame(episodes).reset_index(drop=True)


def summarize_bucket(compare: pd.DataFrame, bucket: pd.DataFrame) -> pd.DataFrame:
    matured_20 = bucket.loc[bucket["future_return_20"].notna()].copy()
    matured_60 = bucket.loc[bucket["future_return_60"].notna()].copy()
    episodes = collect_non_overlap_episodes(matured_60, min_gap_days=60)
    year_counts = bucket["date"].dt.year.value_counts().sort_values(ascending=False)
    quarter_counts = bucket["date"].dt.to_period("Q").astype(str).value_counts().sort_values(ascending=False)
    latest_case_date = bucket["date"].max().strftime("%Y-%m-%d") if not bucket.empty else ""
    summary_rows = [
        {
            "metric": "monitor_verdict",
            "value": "hold_anchor_watch",
            "note": "This is a monitoring-only hold anchor for the current live line, not a promotion signal.",
        },
        {
            "metric": "shared_oos_rows",
            "value": len(compare),
            "note": "Rows on the shared out-of-sample date axis used for live-versus-shadow comparison.",
        },
        {
            "metric": "bucket_rows",
            "value": len(bucket),
            "note": "Dates where live selected while shadow stayed idle.",
        },
        {
            "metric": "bucket_non_overlap_60d_episodes",
            "value": len(episodes),
            "note": "Greedy 60-day non-overlap episodes, used as a sample-quality sanity check.",
        },
        {
            "metric": "latest_case_date",
            "value": latest_case_date,
            "note": "Most recent date where live selected while shadow stayed idle.",
        },
        {
            "metric": "future_return_20_avg",
            "value": round(float(matured_20["future_return_20"].mean()), 4) if not matured_20.empty else "",
            "note": "Average 20-day realized return after the live-only selection, using matured rows only.",
        },
        {
            "metric": "future_return_20_hit_rate",
            "value": round(float((matured_20["future_return_20"] > 0).mean()), 4) if not matured_20.empty else "",
            "note": "Share of matured bucket rows with positive 20-day realized return.",
        },
        {
            "metric": "matured_20_count",
            "value": len(matured_20),
            "note": "Number of bucket rows with realized 20-day outcomes available.",
        },
        {
            "metric": "future_return_60_avg",
            "value": round(float(matured_60["future_return_60"].mean()), 4) if not matured_60.empty else "",
            "note": "Average 60-day realized return after the live-only selection, using matured rows only.",
        },
        {
            "metric": "future_return_60_hit_rate",
            "value": round(float((matured_60["future_return_60"] > 0).mean()), 4) if not matured_60.empty else "",
            "note": "Share of matured bucket rows with positive 60-day realized return.",
        },
        {
            "metric": "matured_60_count",
            "value": len(matured_60),
            "note": "Number of bucket rows with realized 60-day outcomes available.",
        },
        {
            "metric": "episode_future_return_60_avg",
            "value": round(float(episodes["future_return_60"].mean()), 4) if not episodes.empty else "",
            "note": "Average 60-day realized return across non-overlap episodes.",
        },
        {
            "metric": "episode_future_return_60_ex_best_avg",
            "value": (
                round(float(episodes.nsmallest(max(len(episodes) - 1, 1), "future_return_60")["future_return_60"].mean()), 4)
                if not episodes.empty
                else ""
            ),
            "note": "Episode average after dropping the single best 60-day episode.",
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
            "metric": "max_quarter_share",
            "value": round(float(quarter_counts.iloc[0] / len(bucket)), 4) if not bucket.empty else "",
            "note": (
                f"Largest quarter concentration: {quarter_counts.index[0]} with {int(quarter_counts.iloc[0])} rows."
                if not bucket.empty
                else "No live-only bucket rows yet."
            ),
        },
        {
            "metric": "above_200dma_share",
            "value": round(float(bucket["above_200dma"].mean()), 4) if not bucket.empty else "",
            "note": "Share of bucket rows above the 200-day moving average.",
        },
        {
            "metric": "slope_60_positive_share",
            "value": round(float(bucket["slope_60_positive"].mean()), 4) if not bucket.empty else "",
            "note": "Share of bucket rows with positive 60-day slope.",
        },
        {
            "metric": "shadow_gap_median",
            "value": round(float(bucket["shadow_gap"].median()), 6) if not bucket.empty else "",
            "note": "Median challenger margin versus its own execution cutoff.",
        },
        {
            "metric": "shadow_near_cutoff_share_lt_0_005",
            "value": round(float(((bucket["shadow_gap"] > -0.005) & (bucket["shadow_gap"] < 0)).mean()), 4)
            if not bucket.empty
            else "",
            "note": "Share of bucket rows where shadow missed by less than 0.5 percentage points of probability.",
        },
    ]
    return pd.DataFrame(summary_rows)


def build_recent_frame(bucket: pd.DataFrame) -> pd.DataFrame:
    columns = [
        "date",
        "close",
        "future_return_20",
        "future_return_60",
        "live_probability",
        "live_cutoff",
        "live_gap",
        "live_signal",
        "shadow_probability",
        "shadow_cutoff",
        "shadow_gap",
        "shadow_signal",
        "gap_spread",
        "above_200dma",
        "slope_60_positive",
        "bullish_pocket_label",
        "ret_60",
        "distance_from_60d_low",
        "vol_ratio_20_120",
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
        rows = "<tr><td colspan='9'>No live-only anchor rows are available yet.</td></tr>"
    else:
        for _, row in recent.iloc[::-1].iterrows():
            rows += (
                "<tr>"
                f"<td>{escape(str(row['date']))}</td>"
                f"<td>{escape(str(row['bullish_pocket_label']))}</td>"
                f"<td>{escape(str(row['live_signal']))}</td>"
                f"<td>{float(row['live_gap']):.4f}</td>"
                f"<td>{escape(str(row['shadow_signal']))}</td>"
                f"<td>{float(row['shadow_gap']):.4f}</td>"
                f"<td>{escape(str(row['future_return_20']))}</td>"
                f"<td>{escape(str(row['future_return_60']))}</td>"
                f"<td>{float(row['gap_spread']):.4f}</td>"
                "</tr>"
            )
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>MU Live Bucket Monitor</title>
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
    <h1>MU Live Bucket Monitor</h1>
    <p>This is a low-risk monitor for <strong>live_selected_shadow_idle</strong>, one of the strongest current hold anchors for the live MU line. It is monitoring-only and does not imply a strategy switch.</p>
    <p>Latest live-only anchor date: <strong>{escape(str(summary_map.get('latest_case_date', '')))}</strong>. Current verdict: <strong>{escape(str(summary_map.get('monitor_verdict', 'hold_anchor_watch')))}</strong>.</p>
  </section>
  <section class="grid">
    <div class="card"><div class="label">Bucket Rows</div><div class="value">{escape(str(summary_map.get('bucket_rows', '')))}</div></div>
    <div class="card"><div class="label">60d Episodes</div><div class="value">{escape(str(summary_map.get('bucket_non_overlap_60d_episodes', '')))}</div></div>
    <div class="card"><div class="label">60d Avg</div><div class="value">{escape(str(summary_map.get('future_return_60_avg', '')))}</div></div>
    <div class="card"><div class="label">60d Hit Rate</div><div class="value">{escape(str(summary_map.get('future_return_60_hit_rate', '')))}</div></div>
    <div class="card"><div class="label">Ex-Best Episode Avg</div><div class="value">{escape(str(summary_map.get('episode_future_return_60_ex_best_avg', '')))}</div></div>
    <div class="card"><div class="label">Bullish Pocket Share</div><div class="value">{escape(str(summary_map.get('above_200dma_share', '')))}</div></div>
  </section>
  <section>
    <h2>Recent Live-Only Anchor Rows</h2>
    <table>
      <thead>
        <tr>
          <th>Date</th>
          <th>Pocket</th>
          <th>Live</th>
          <th>Live Gap</th>
          <th>Shadow</th>
          <th>Shadow Gap</th>
          <th>20d</th>
          <th>60d</th>
          <th>Gap Spread</th>
        </tr>
      </thead>
      <tbody>{rows}</tbody>
    </table>
  </section>
</body>
</html>"""


def main() -> None:
    if ac.get_asset_key() != ASSET_KEY:
        raise ValueError(f"Run with AR_ASSET={ASSET_KEY}")

    base_frame = load_dataset_frame().copy()
    live_bundle = fit_bundle(base_frame, LIVE_LABEL_MODE)
    shadow_bundle = fit_bundle(base_frame, SHADOW_LABEL_MODE)
    compare = build_compare_frame(base_frame, live_bundle, shadow_bundle)
    bucket = compare.loc[compare["case"] == CASE_NAME].copy().reset_index(drop=True)

    summary = summarize_bucket(compare, bucket)
    recent = build_recent_frame(bucket)

    get_summary_path().write_text(summary.to_csv(sep="\t", index=False), encoding="utf-8")
    get_recent_path().write_text(recent.to_csv(sep="\t", index=False), encoding="utf-8")
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
