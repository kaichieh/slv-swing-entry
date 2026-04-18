from __future__ import annotations

import json
import os
from contextlib import contextmanager
from html import escape
from pathlib import Path
from typing import Iterator

import pandas as pd

import asset_config as ac
import predict_latest as pl
import prepare as pr
import train as tr

ASSET_KEY = "mu"
LOOKBACK_DAYS = 60
DIFF_RECENT_LIMIT = 20
SHADOW_LINE_ID = "mu_tb20_ret_60_vol_ratio_20_120_top11_5_shadow"
SHADOW_LABEL_MODE = "future-return-top-bottom-20pct"
SHADOW_EXECUTION_RULE = "top_11_5pct"
SHADOW_THRESHOLD_METRIC = "balanced_accuracy"
SHADOW_EXTRA_FEATURES = ("ret_60", "vol_ratio_20_120")


def get_output_dir() -> Path:
    return ac.get_asset_dir(ASSET_KEY)


def get_shadow_board_path() -> Path:
    return get_output_dir() / "shadow_board.tsv"


def get_shadow_recent_path() -> Path:
    return get_output_dir() / "shadow_board_recent.tsv"


def get_shadow_diff_path() -> Path:
    return get_output_dir() / "shadow_diff_recent.tsv"


def get_shadow_html_path() -> Path:
    return get_output_dir() / "shadow_board.html"


def get_live_rows_path() -> Path:
    return ac.get_cache_dir(ASSET_KEY) / "signal_rows.tsv"


@contextmanager
def temporary_env(overrides: dict[str, str]) -> Iterator[None]:
    sentinel = object()
    previous: dict[str, object] = {}
    for key, value in overrides.items():
        previous[key] = os.environ.get(key, sentinel)
        os.environ[key] = value
    try:
        yield
    finally:
        for key, old_value in previous.items():
            if old_value is sentinel:
                os.environ.pop(key, None)
            else:
                os.environ[key] = str(old_value)


def read_live_rows(lookback_days: int | None = LOOKBACK_DAYS) -> pd.DataFrame:
    path = get_live_rows_path()
    if not path.exists():
        raise FileNotFoundError(f"Missing MU live signal rows cache: {path}")
    frame = pd.read_csv(path, sep="\t")
    if frame.empty:
        raise ValueError(f"MU live signal rows cache is empty: {path}")
    if lookback_days is None:
        return frame.reset_index(drop=True)
    return frame.tail(lookback_days).reset_index(drop=True)


def build_shadow_splits(raw_prices: pd.DataFrame) -> dict[str, pr.DatasetSplit]:
    frame = pr.add_features(raw_prices)
    train_end, valid_end = pr.split_indices(len(frame))
    split_frames = {
        "train": frame.iloc[:train_end].copy(),
        "validation": frame.iloc[train_end:valid_end].copy(),
        "test": frame.iloc[valid_end:].copy(),
    }
    return {
        name: pr.DatasetSplit(
            features=split_frame[pr.FEATURE_COLUMNS].to_numpy(dtype="float32"),
            labels=split_frame[pr.TARGET_COLUMN].to_numpy(dtype="float32"),
            frame=split_frame,
        )
        for name, split_frame in split_frames.items()
    }


def build_context_frame(raw_prices: pd.DataFrame) -> pd.DataFrame:
    frame = pr.add_context_features(pr.add_relative_strength_features(pr.add_price_features(raw_prices), pr.BENCHMARK_SYMBOL))
    context = frame.loc[:, ["date", "above_200dma_flag", "slope_60", "drawdown_20"]].copy()
    context["date"] = pd.to_datetime(context["date"]).dt.strftime("%Y-%m-%d")
    context["above_200dma"] = context["above_200dma_flag"].fillna(0.0) >= 0.5
    context["slope_60_positive"] = context["slope_60"].fillna(0.0) > 0.0
    context["bullish_pocket"] = context["above_200dma"]
    context["bullish_pocket_confirmed"] = context["above_200dma"] & context["slope_60_positive"]
    context["bullish_pocket_label"] = [
        format_bullish_pocket_label(above_200dma, slope_60_positive)
        for above_200dma, slope_60_positive in zip(context["above_200dma"], context["slope_60_positive"])
    ]
    return context


def build_shadow_rows(
    lookback_days: int | None = LOOKBACK_DAYS,
    raw_prices: pd.DataFrame | None = None,
) -> tuple[pd.DataFrame, dict[str, object]]:
    env_overrides = {
        "AR_ASSET": ASSET_KEY,
        "AR_LABEL_MODE": SHADOW_LABEL_MODE,
        "AR_EXTRA_BASE_FEATURES": ",".join(SHADOW_EXTRA_FEATURES),
        "AR_THRESHOLD_PRIMARY_METRIC": SHADOW_THRESHOLD_METRIC,
    }
    with temporary_env(env_overrides):
        tr.set_seed(tr.get_env_int("AR_SEED", tr.SEED))
        raw_prices = pr.download_asset_prices() if raw_prices is None else raw_prices
        live_features = pr.add_context_features(
            pr.add_relative_strength_features(pr.add_price_features(raw_prices), pr.BENCHMARK_SYMBOL)
        )
        splits = build_shadow_splits(raw_prices)
        feature_names = pl.build_feature_names()
        model_artifacts = pl.fit_model(splits, feature_names, raw_prices=raw_prices)
        feature_names = list(model_artifacts["feature_names"])
        historical_probabilities = pl.build_history_probabilities(model_artifacts, splits, feature_names)
        model_threshold = float(model_artifacts["threshold"])
        execution_cutoff = float(
            pl.resolve_execution_cutoff(SHADOW_EXECUTION_RULE, model_threshold, historical_probabilities)
        )
        reference_top_pct = pl.parse_top_pct_rule(SHADOW_EXECUTION_RULE) or 11.5
        train_frame = model_artifacts["train_frame"]
        scored = live_features.dropna(subset=feature_names)
        if lookback_days is not None:
            scored = scored.tail(lookback_days)
        scored = scored.reset_index(drop=True)

        rows: list[dict[str, object]] = []
        for idx in range(len(scored)):
            row = scored.iloc[[idx]]
            vector, snapshot = pl.score_latest_row(model_artifacts, feature_names, train_frame, row)
            probability = float(pl.predict_probabilities(model_artifacts, vector)[0])
            raw_model_signal, band_info = pl.classify_signal(probability, execution_cutoff, historical_probabilities)
            signal, buy_point_summary = pl.apply_buy_point_overlay(raw_model_signal, snapshot, asset_key=ASSET_KEY)
            rule_summary = pl.summarize_rule(probability, historical_probabilities, reference_top_pct)
            rows.append(
                {
                    "date": row["date"].iloc[0].strftime("%Y-%m-%d"),
                    "close": round(float(row["close"].iloc[0]), 2),
                    "signal": signal,
                    "raw_model_signal": raw_model_signal,
                    "buy_point_ok": bool(buy_point_summary["buy_point_ok"]),
                    "probability": round(probability, 4),
                    "threshold": round(execution_cutoff, 4),
                    "model_threshold": round(model_threshold, 4),
                    "confidence_gap": round(float(band_info["confidence_gap"]), 4),
                    "rule_selected": bool(rule_summary["selected"]),
                    "rule_cutoff": round(float(rule_summary["cutoff"]), 4),
                    "rule_name": str(rule_summary["rule_name"]),
                    "percentile_rank": round(float(rule_summary["percentile_rank"]), 4),
                    "line_id": SHADOW_LINE_ID,
                    "label_mode": SHADOW_LABEL_MODE,
                    "execution_rule": SHADOW_EXECUTION_RULE,
                }
            )

    metadata = {
        "line_id": SHADOW_LINE_ID,
        "label_mode": SHADOW_LABEL_MODE,
        "execution_rule": SHADOW_EXECUTION_RULE,
        "threshold_metric": SHADOW_THRESHOLD_METRIC,
        "extra_features": list(SHADOW_EXTRA_FEATURES),
    }
    return pd.DataFrame(rows), metadata


def classify_stream_state(selected: bool, blocked: bool) -> str:
    if selected:
        return "selected"
    if blocked:
        return "blocked"
    return "idle"


def format_bullish_pocket_label(above_200dma: bool, slope_60_positive: bool) -> str:
    if above_200dma and slope_60_positive:
        return "above_200dma_and_slope_60_positive"
    if above_200dma:
        return "above_200dma"
    if slope_60_positive:
        return "slope_60_positive_only"
    return "outside_bullish_pocket"


def classify_divergence_case(row: pd.Series) -> str:
    live_selected = bool(row["live_selected"])
    shadow_selected = bool(row["shadow_selected"])
    live_blocked = bool(row["live_blocked"])
    shadow_blocked = bool(row["shadow_blocked"])

    if live_blocked and shadow_selected:
        return "live_blocked_shadow_selected"
    if shadow_blocked and live_selected:
        return "shadow_blocked_live_selected"
    if not live_selected and shadow_selected:
        return "shadow_selected_live_idle"
    if live_selected and not shadow_selected:
        return "live_selected_shadow_idle"
    if bool(row["live_model_ready"]) and not bool(row["shadow_model_ready"]):
        return "live_model_ready_shadow_not_ready"
    if bool(row["shadow_model_ready"]) and not bool(row["live_model_ready"]):
        return "shadow_model_ready_live_not_ready"
    return ""


def classify_comparison_owner(divergence_case: str) -> str:
    if divergence_case in {"live_selected_shadow_idle", "shadow_blocked_live_selected"}:
        return "live"
    if divergence_case in {"live_blocked_shadow_selected", "shadow_selected_live_idle"}:
        return "challenger"
    return "shared"


def describe_comparison_state(live_state: str, shadow_state: str) -> str:
    if live_state == shadow_state:
        if live_state == "selected":
            return "Both live and shadow would take the trade."
        if live_state == "blocked":
            return "Both live and shadow clear model thresholds, but overlays block entry."
        return "Both live and shadow stay idle."
    if live_state == "selected" and shadow_state == "idle":
        return "Live selects the trade while shadow stays idle."
    if live_state == "selected" and shadow_state == "blocked":
        return "Live selects the trade while shadow clears the model only and is blocked by its overlay."
    if live_state == "blocked" and shadow_state == "selected":
        return "Live is blocked by its overlay while shadow would take the trade."
    if live_state == "idle" and shadow_state == "selected":
        return "Shadow selects the trade while live stays idle."
    if live_state == "blocked" and shadow_state == "idle":
        return "Live clears the model only while shadow stays idle."
    if live_state == "idle" and shadow_state == "blocked":
        return "Shadow clears the model only while live stays idle."
    return "Live and shadow disagree on entry readiness."


def build_compare_frame(
    live_rows: pd.DataFrame,
    shadow_rows: pd.DataFrame,
    context_frame: pd.DataFrame | None = None,
) -> pd.DataFrame:
    live = live_rows.copy()
    shadow = shadow_rows.copy()

    live["date"] = live["date"].astype(str).str[:10]
    shadow["date"] = shadow["date"].astype(str).str[:10]

    live = live.rename(
        columns={
            "signal": "live_signal",
            "raw_model_signal": "live_raw_model_signal",
            "buy_point_ok": "live_buy_point_ok",
            "probability": "live_probability",
            "threshold": "live_cutoff",
            "confidence_gap": "live_confidence_gap",
            "rule_selected": "live_rule_selected",
            "rule_cutoff": "live_rule_cutoff",
            "percentile_rank": "live_percentile_rank",
        }
    )
    shadow = shadow.rename(
        columns={
            "signal": "shadow_signal",
            "raw_model_signal": "shadow_raw_model_signal",
            "buy_point_ok": "shadow_buy_point_ok",
            "probability": "shadow_probability",
            "threshold": "shadow_cutoff",
            "confidence_gap": "shadow_confidence_gap",
            "rule_selected": "shadow_rule_selected",
            "rule_cutoff": "shadow_rule_cutoff",
            "percentile_rank": "shadow_percentile_rank",
        }
    )

    merged = live.merge(
        shadow[
            [
                "date",
                "shadow_signal",
                "shadow_raw_model_signal",
                "shadow_buy_point_ok",
                "shadow_probability",
                "shadow_cutoff",
                "shadow_confidence_gap",
                "shadow_rule_selected",
                "shadow_rule_cutoff",
                "shadow_percentile_rank",
                "line_id",
                "label_mode",
                "execution_rule",
            ]
        ],
        on="date",
        how="inner",
    )
    if context_frame is not None:
        merged = merged.merge(context_frame, on="date", how="left")
    if "drawdown_20" not in merged.columns:
        drawdown_sources = [column for column in ("drawdown_20_x", "drawdown_20_y") if column in merged.columns]
        if drawdown_sources:
            merged["drawdown_20"] = merged[drawdown_sources].bfill(axis=1).iloc[:, 0]
    merged["live_selected"] = merged["live_signal"].astype(str) != "no_entry"
    merged["shadow_selected"] = merged["shadow_signal"].astype(str) != "no_entry"
    merged["live_model_ready"] = merged["live_raw_model_signal"].astype(str) != "no_entry"
    merged["shadow_model_ready"] = merged["shadow_raw_model_signal"].astype(str) != "no_entry"
    merged["live_blocked"] = merged["live_model_ready"] & ~merged["live_selected"]
    merged["shadow_blocked"] = merged["shadow_model_ready"] & ~merged["shadow_selected"]
    merged["live_state"] = [
        classify_stream_state(selected, blocked)
        for selected, blocked in zip(merged["live_selected"], merged["live_blocked"])
    ]
    merged["shadow_state"] = [
        classify_stream_state(selected, blocked)
        for selected, blocked in zip(merged["shadow_selected"], merged["shadow_blocked"])
    ]
    merged["comparison_state"] = merged["live_state"].astype(str) + "_" + merged["shadow_state"].astype(str)
    merged["comparison_note"] = [
        describe_comparison_state(live_state, shadow_state)
        for live_state, shadow_state in zip(merged["live_state"], merged["shadow_state"])
    ]
    merged["confidence_gap_delta"] = (
        merged["shadow_confidence_gap"].astype(float) - merged["live_confidence_gap"].astype(float)
    ).round(4)
    merged["divergence_case"] = merged.apply(classify_divergence_case, axis=1)
    merged["comparison_owner"] = merged["divergence_case"].astype(str).map(classify_comparison_owner)
    if "bullish_pocket" not in merged.columns:
        merged["bullish_pocket"] = False
        merged["bullish_pocket_confirmed"] = False
        merged["bullish_pocket_label"] = "outside_bullish_pocket"
    return merged


def build_shadow_board(compare_frame: pd.DataFrame, shadow_metadata: dict[str, object]) -> pd.DataFrame:
    latest = compare_frame.iloc[-1]
    live_line = str(ac.load_asset_config(ASSET_KEY).get("live_operator_line_id", "mu_live"))
    latest_case = str(latest["divergence_case"]).strip()
    latest_regime = str(latest.get("bullish_pocket_label", "outside_bullish_pocket"))

    def row_status(selected: bool, blocked: bool) -> str:
        if selected:
            return "selected"
        if blocked:
            return "blocked"
        return "idle"

    return pd.DataFrame(
        [
            {
                "stream": "live",
                "line_id": live_line,
                "status": row_status(bool(latest["live_selected"]), bool(latest["live_blocked"])),
                "signal": str(latest["live_signal"]),
                "model_ready": bool(latest["live_model_ready"]),
                "buy_point_ok": bool(latest["live_buy_point_ok"]),
                "probability": round(float(latest["live_probability"]), 4),
                "cutoff": round(float(latest["live_cutoff"]), 4),
                "confidence_gap": round(float(latest["live_confidence_gap"]), 4),
                "latest_date": str(latest["date"]),
                "decision_note": (
                    "Official live line is above threshold but still blocked by the buy-point overlay."
                    if bool(latest["live_blocked"])
                    else "Official live line is the current operating reference."
                ),
            },
            {
                "stream": "shadow",
                "line_id": str(shadow_metadata["line_id"]),
                "status": row_status(bool(latest["shadow_selected"]), bool(latest["shadow_blocked"])),
                "signal": str(latest["shadow_signal"]),
                "model_ready": bool(latest["shadow_model_ready"]),
                "buy_point_ok": bool(latest["shadow_buy_point_ok"]),
                "probability": round(float(latest["shadow_probability"]), 4),
                "cutoff": round(float(latest["shadow_cutoff"]), 4),
                "confidence_gap": round(float(latest["shadow_confidence_gap"]), 4),
                "latest_date": str(latest["date"]),
                "decision_note": (
                    f"Research-only challenger on {shadow_metadata['label_mode']} with {shadow_metadata['execution_rule']}."
                    + (f" Current divergence: {latest_case}." if latest_case else "")
                    + f" Regime lens: {latest_regime}."
                ),
            },
        ]
    )


def build_diff_frame(compare_frame: pd.DataFrame) -> pd.DataFrame:
    diff = compare_frame.loc[compare_frame["divergence_case"].astype(str) != ""].copy()
    if diff.empty:
        return diff
    keep_columns = [
        "date",
        "divergence_case",
        "comparison_owner",
        "bullish_pocket",
        "bullish_pocket_confirmed",
        "bullish_pocket_label",
        "live_signal",
        "live_raw_model_signal",
        "live_probability",
        "live_cutoff",
        "live_confidence_gap",
        "shadow_signal",
        "shadow_raw_model_signal",
        "shadow_probability",
        "shadow_cutoff",
        "shadow_confidence_gap",
        "confidence_gap_delta",
    ]
    return diff[keep_columns].tail(DIFF_RECENT_LIMIT).reset_index(drop=True)


def render_shadow_html(board: pd.DataFrame, diff_frame: pd.DataFrame) -> str:
    latest_live = board.loc[board["stream"] == "live"].iloc[0]
    latest_shadow = board.loc[board["stream"] == "shadow"].iloc[0]
    headline = (
        f"Latest: live={latest_live['status']} ({latest_live['signal']}) vs "
        f"shadow={latest_shadow['status']} ({latest_shadow['signal']})"
    )
    diff_rows = ""
    if diff_frame.empty:
        diff_rows = "<tr><td colspan='9'>No recent decision-relevant divergences in the current lookback window.</td></tr>"
    else:
        for _, row in diff_frame.iloc[::-1].iterrows():
            diff_rows += (
                "<tr>"
                f"<td>{escape(str(row['date']))}</td>"
                f"<td>{escape(str(row['divergence_case']))}</td>"
                f"<td>{escape(str(row['comparison_owner']))}</td>"
                f"<td>{escape(str(row['bullish_pocket_label']))}</td>"
                f"<td>{escape(str(row['live_signal']))}</td>"
                f"<td>{float(row['live_confidence_gap']):.4f}</td>"
                f"<td>{escape(str(row['shadow_signal']))}</td>"
                f"<td>{float(row['shadow_confidence_gap']):.4f}</td>"
                f"<td>{float(row['confidence_gap_delta']):.4f}</td>"
                "</tr>"
            )
    cards = ""
    for _, row in board.iterrows():
        cards += f"""
        <section class="card">
          <div class="card-top">
            <h2>{escape(str(row["stream"]).upper())}</h2>
            <span class="badge">{escape(str(row["status"]))}</span>
          </div>
          <p class="line-id">{escape(str(row["line_id"]))}</p>
          <p class="note">{escape(str(row["decision_note"]))}</p>
          <dl class="stats">
            <div><dt>signal</dt><dd>{escape(str(row["signal"]))}</dd></div>
            <div><dt>model ready</dt><dd>{"yes" if bool(row["model_ready"]) else "no"}</dd></div>
            <div><dt>buy point ok</dt><dd>{"yes" if bool(row["buy_point_ok"]) else "no"}</dd></div>
            <div><dt>probability</dt><dd>{float(row["probability"]):.4f}</dd></div>
            <div><dt>cutoff</dt><dd>{float(row["cutoff"]):.4f}</dd></div>
            <div><dt>confidence gap</dt><dd>{float(row["confidence_gap"]):.4f}</dd></div>
          </dl>
        </section>
        """
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>MU Shadow Board</title>
  <style>
    :root {{
      color-scheme: light;
      --bg: #f4efe6;
      --card: #fffdf8;
      --line: #e8decc;
      --text: #18212f;
      --muted: #586272;
      --accent: #8b5e34;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      padding: 28px;
      font-family: "Segoe UI", Arial, sans-serif;
      background: linear-gradient(180deg, #f4efe6 0%, #ece3d4 100%);
      color: var(--text);
    }}
    .hero h1 {{ margin: 0 0 8px; font-size: 30px; }}
    .hero p {{ margin: 0; color: var(--muted); }}
    .grid {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
      gap: 16px;
      margin: 20px 0 24px;
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
      align-items: center;
      gap: 12px;
    }}
    .card-top h2 {{ margin: 0; font-size: 20px; }}
    .badge {{
      background: #f4e6d5;
      color: #8b5e34;
      border-radius: 999px;
      padding: 6px 10px;
      font-size: 12px;
      font-weight: 700;
    }}
    .line-id {{
      margin: 10px 0 8px;
      font-family: Consolas, monospace;
      font-size: 13px;
      color: var(--muted);
    }}
    .note {{ margin: 0 0 14px; color: var(--muted); line-height: 1.5; }}
    .stats {{
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 10px 12px;
      margin: 0;
    }}
    .stats div {{
      padding: 10px 12px;
      background: #faf6ee;
      border: 1px solid #eee1cd;
      border-radius: 12px;
    }}
    dt {{
      margin-bottom: 4px;
      font-size: 12px;
      text-transform: uppercase;
      color: var(--muted);
    }}
    dd {{ margin: 0; font-weight: 600; }}
    table {{
      width: 100%;
      border-collapse: collapse;
      background: rgba(255, 255, 255, 0.8);
      border: 1px solid var(--line);
      border-radius: 16px;
      overflow: hidden;
    }}
    th, td {{
      padding: 10px 12px;
      border-bottom: 1px solid var(--line);
      text-align: left;
      font-size: 14px;
    }}
    th {{
      background: #f5ecdf;
      font-size: 12px;
      text-transform: uppercase;
      letter-spacing: 0.04em;
      color: var(--muted);
    }}
  </style>
</head>
<body>
  <section class="hero">
    <h1>MU Shadow Board</h1>
    <p>{escape(headline)}</p>
  </section>
  <section class="grid">
    {cards}
  </section>
  <section>
    <h2>Recent Divergences</h2>
    <table>
      <thead>
        <tr>
          <th>Date</th>
          <th>Case</th>
          <th>Owner</th>
          <th>Pocket</th>
          <th>Live Signal</th>
          <th>Live Gap</th>
          <th>Shadow Signal</th>
          <th>Shadow Gap</th>
          <th>Delta</th>
        </tr>
      </thead>
      <tbody>
        {diff_rows}
      </tbody>
    </table>
  </section>
</body>
</html>"""


def main() -> None:
    raw_prices = pr.download_asset_prices()
    live_rows = read_live_rows()
    shadow_rows, shadow_metadata = build_shadow_rows(raw_prices=raw_prices)
    context_frame = build_context_frame(raw_prices)
    compare_frame = build_compare_frame(live_rows, shadow_rows, context_frame=context_frame)
    if compare_frame.empty:
        raise ValueError("MU shadow board compare frame is empty.")

    board = build_shadow_board(compare_frame, shadow_metadata)
    diff_frame = build_diff_frame(compare_frame)

    board.to_csv(get_shadow_board_path(), sep="\t", index=False)
    compare_frame.to_csv(get_shadow_recent_path(), sep="\t", index=False)
    diff_frame.to_csv(get_shadow_diff_path(), sep="\t", index=False)
    get_shadow_html_path().write_text(render_shadow_html(board, diff_frame), encoding="utf-8")

    latest = compare_frame.iloc[-1]
    print(
        json.dumps(
            {
                "asset_key": ASSET_KEY,
                "shadow_board_path": str(get_shadow_board_path()),
                "shadow_recent_path": str(get_shadow_recent_path()),
                "shadow_diff_path": str(get_shadow_diff_path()),
                "shadow_html_path": str(get_shadow_html_path()),
                "latest_date": str(latest["date"]),
                "latest_divergence_case": str(latest["divergence_case"]),
                "latest_bullish_pocket_label": str(latest["bullish_pocket_label"]),
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
