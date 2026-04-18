from __future__ import annotations

import json
from html import escape
from pathlib import Path

import pandas as pd

import prepare as pr
import refresh_mu_shadow_board as base_shadow

ASSET_KEY = base_shadow.ASSET_KEY
LOOKBACK_DAYS = base_shadow.LOOKBACK_DAYS
DIFF_RECENT_LIMIT = base_shadow.DIFF_RECENT_LIMIT
OUTPUT_DIRNAME = "research_gap_volume_ignition_v82"
RULE_NAME = "gap_volume_ignition_v82"
SHADOW_LINE_ID = "mu_gap_volume_ignition_v82"
SHADOW_LABEL_MODE = "exact-event-rule"
SHADOW_EXECUTION_RULE = (
    "overnight_gap>=0.5%, volume_vs_20>=0.50, range_z_20>=0.50, intraday_return>=0, breakout_20==1"
)
RULE_COLUMNS = (
    "overnight_gap",
    "volume_vs_20",
    "range_z_20",
    "intraday_return",
    "breakout_20",
)
EVIDENCE_COLUMNS = (
    "criteria_pass_count",
    "criteria_pass_rate",
    "overnight_gap",
    "volume_vs_20",
    "range_z_20",
    "intraday_return",
    "breakout_20",
    "overnight_gap_pass",
    "volume_vs_20_pass",
    "range_z_20_pass",
    "intraday_return_pass",
    "breakout_20_pass",
)


def compare_evidence_name(column: str) -> str:
    return f"shadow_{column}"


def get_output_dir() -> Path:
    return base_shadow.get_output_dir() / OUTPUT_DIRNAME


def get_shadow_board_path() -> Path:
    return get_output_dir() / "shadow_board.tsv"


def get_shadow_recent_path() -> Path:
    return get_output_dir() / "shadow_board_recent.tsv"


def get_shadow_diff_path() -> Path:
    return get_output_dir() / "shadow_diff_recent.tsv"


def get_shadow_html_path() -> Path:
    return get_output_dir() / "shadow_board.html"


def ensure_output_dir() -> Path:
    path = get_output_dir()
    path.mkdir(parents=True, exist_ok=True)
    return path


def download_asset_prices() -> pd.DataFrame:
    with base_shadow.temporary_env({"AR_ASSET": ASSET_KEY}):
        return pr.download_asset_prices()


def read_live_rows(lookback_days: int | None = LOOKBACK_DAYS) -> pd.DataFrame:
    return base_shadow.read_live_rows(lookback_days=lookback_days)


def build_context_frame(raw_prices: pd.DataFrame) -> pd.DataFrame:
    return base_shadow.build_context_frame(raw_prices)


def build_rule_feature_frame(raw_prices: pd.DataFrame) -> pd.DataFrame:
    return pr.add_context_features(
        pr.add_relative_strength_features(pr.add_price_features(raw_prices), pr.BENCHMARK_SYMBOL)
    )


def evaluate_rule_row(row: pd.Series) -> dict[str, object]:
    overnight_gap = float(row.get("overnight_gap", float("nan")))
    volume_vs_20 = float(row.get("volume_vs_20", float("nan")))
    range_z_20 = float(row.get("range_z_20", float("nan")))
    intraday_return = float(row.get("intraday_return", float("nan")))
    breakout_20 = float(row.get("breakout_20", float("nan")))

    criteria = {
        "overnight_gap_pass": overnight_gap >= 0.005,
        "volume_vs_20_pass": volume_vs_20 >= 0.50,
        "range_z_20_pass": range_z_20 >= 0.50,
        "intraday_return_pass": intraday_return >= 0.0,
        "breakout_20_pass": breakout_20 >= 1.0,
    }
    pass_count = sum(bool(value) for value in criteria.values())
    pass_rate = pass_count / len(criteria)
    selected = pass_count == len(criteria)
    return {
        "selected": selected,
        "criteria_pass_count": pass_count,
        "criteria_pass_rate": round(pass_rate, 4),
        "overnight_gap": round(overnight_gap, 4),
        "volume_vs_20": round(volume_vs_20, 4),
        "range_z_20": round(range_z_20, 4),
        "intraday_return": round(intraday_return, 4),
        "breakout_20": round(breakout_20, 4),
        **criteria,
    }


def build_shadow_rows_from_feature_frame(
    feature_frame: pd.DataFrame,
    lookback_days: int | None = LOOKBACK_DAYS,
) -> tuple[pd.DataFrame, dict[str, object]]:
    scored = feature_frame.copy()
    if lookback_days is not None:
        scored = scored.tail(lookback_days)
    scored = scored.reset_index(drop=True)

    rows: list[dict[str, object]] = []
    for _, row in scored.iterrows():
        evaluation = evaluate_rule_row(row)
        selected = bool(evaluation["selected"])
        pass_rate = float(evaluation["criteria_pass_rate"])
        rows.append(
            {
                "date": pd.to_datetime(row["date"]).strftime("%Y-%m-%d"),
                "close": round(float(row["close"]), 2),
                "signal": "rule_match" if selected else "no_entry",
                "raw_model_signal": "rule_match" if selected else "no_entry",
                "buy_point_ok": selected,
                "probability": round(pass_rate, 4),
                "threshold": 1.0,
                "model_threshold": 1.0,
                "confidence_gap": round(pass_rate - 1.0, 4),
                "rule_selected": selected,
                "rule_cutoff": 1.0,
                "rule_name": RULE_NAME,
                "percentile_rank": round(pass_rate, 4),
                "line_id": SHADOW_LINE_ID,
                "label_mode": SHADOW_LABEL_MODE,
                "execution_rule": SHADOW_EXECUTION_RULE,
                **{column: evaluation[column] for column in EVIDENCE_COLUMNS},
            }
        )

    metadata = {
        "line_id": SHADOW_LINE_ID,
        "label_mode": SHADOW_LABEL_MODE,
        "execution_rule": SHADOW_EXECUTION_RULE,
        "rule_name": RULE_NAME,
        "rule_columns": list(RULE_COLUMNS),
    }
    return pd.DataFrame(rows), metadata


def build_shadow_rows(
    lookback_days: int | None = LOOKBACK_DAYS,
    raw_prices: pd.DataFrame | None = None,
) -> tuple[pd.DataFrame, dict[str, object]]:
    raw_prices = download_asset_prices() if raw_prices is None else raw_prices
    feature_frame = build_rule_feature_frame(raw_prices)
    return build_shadow_rows_from_feature_frame(feature_frame, lookback_days=lookback_days)


def build_compare_frame(
    live_rows: pd.DataFrame,
    shadow_rows: pd.DataFrame,
    context_frame: pd.DataFrame | None = None,
) -> pd.DataFrame:
    compare = base_shadow.build_compare_frame(live_rows, shadow_rows, context_frame=context_frame)
    evidence = shadow_rows.loc[:, ["date", *EVIDENCE_COLUMNS]].copy()
    evidence["date"] = evidence["date"].astype(str).str[:10]
    evidence = evidence.rename(columns={column: compare_evidence_name(column) for column in EVIDENCE_COLUMNS})
    compare = compare.merge(evidence, on="date", how="left")
    return compare


def build_shadow_board(compare_frame: pd.DataFrame, shadow_metadata: dict[str, object]) -> pd.DataFrame:
    board = base_shadow.build_shadow_board(compare_frame, shadow_metadata)
    latest = compare_frame.iloc[-1]
    latest_case = str(latest.get("divergence_case", "")).strip()
    latest_regime = str(latest.get("bullish_pocket_label", "outside_bullish_pocket"))
    shadow_mask = board["stream"] == "shadow"
    board.loc[shadow_mask, "decision_note"] = (
        "Research-only exact v82 event rule. "
        "Trigger only when overnight_gap>=0.5%, volume_vs_20>=0.50, range_z_20>=0.50, "
        "intraday_return>=0, and breakout_20==1. "
        + (f"Current divergence: {latest_case}. " if latest_case else "")
        + f"Regime lens: {latest_regime}."
    )
    return board


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
        *[compare_evidence_name(column) for column in EVIDENCE_COLUMNS],
    ]
    return diff[keep_columns].tail(DIFF_RECENT_LIMIT).reset_index(drop=True)


def render_shadow_html(board: pd.DataFrame, diff_frame: pd.DataFrame) -> str:
    latest_live = board.loc[board["stream"] == "live"].iloc[0]
    latest_shadow = board.loc[board["stream"] == "shadow"].iloc[0]
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
            <div><dt>score</dt><dd>{float(row["probability"]):.4f}</dd></div>
            <div><dt>cutoff</dt><dd>{float(row["cutoff"]):.4f}</dd></div>
            <div><dt>gap</dt><dd>{float(row["confidence_gap"]):.4f}</dd></div>
          </dl>
        </section>
        """

    rows = ""
    if diff_frame.empty:
        rows = "<tr><td colspan='11'>No recent live-vs-v82 divergences in the current lookback window.</td></tr>"
    else:
        for _, row in diff_frame.iloc[::-1].iterrows():
            rows += (
                "<tr>"
                f"<td>{escape(str(row['date']))}</td>"
                f"<td>{escape(str(row['divergence_case']))}</td>"
                f"<td>{escape(str(row['comparison_owner']))}</td>"
                f"<td>{int(row['shadow_criteria_pass_count'])}/5</td>"
                f"<td>{escape(str(row['shadow_overnight_gap']))}</td>"
                f"<td>{escape(str(row['shadow_volume_vs_20']))}</td>"
                f"<td>{escape(str(row['shadow_range_z_20']))}</td>"
                f"<td>{escape(str(row['shadow_intraday_return']))}</td>"
                f"<td>{escape(str(row['shadow_breakout_20']))}</td>"
                f"<td>{escape(str(row['live_signal']))}</td>"
                f"<td>{escape(str(row['shadow_signal']))}</td>"
                "</tr>"
            )

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>MU Gap Volume Ignition v82 Shadow Board</title>
  <style>
    :root {{
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
    .hero p {{
      color: var(--muted);
      line-height: 1.5;
    }}
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
    .badge {{
      background: #f4e6d5;
      color: #6d431e;
      border-radius: 999px;
      padding: 6px 12px;
      font-size: 12px;
      text-transform: uppercase;
    }}
    .line-id {{
      margin: 12px 0 8px;
      font-family: Consolas, "Courier New", monospace;
      font-size: 13px;
      color: var(--muted);
    }}
    .note {{
      color: var(--muted);
      line-height: 1.5;
    }}
    .stats {{
      display: grid;
      grid-template-columns: repeat(3, minmax(0, 1fr));
      gap: 12px;
      margin: 14px 0 0;
    }}
    .stats dt {{
      color: var(--muted);
      font-size: 12px;
      text-transform: uppercase;
    }}
    .stats dd {{
      margin: 6px 0 0;
      font-size: 18px;
      font-weight: 700;
    }}
    table {{
      width: 100%;
      border-collapse: collapse;
      background: rgba(255,255,255,0.86);
      border: 1px solid var(--line);
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
    }}
  </style>
</head>
<body>
  <section class="hero">
    <h1>MU Gap Volume Ignition v82 Shadow Board</h1>
    <p>Exact research-side event rule only. Live stays on the official MU lane while this sidecar tracks whether the v82 ignition pattern adds useful evidence on the same date axis.</p>
    <p>Latest snapshot: live=<strong>{escape(str(latest_live['status']))}</strong> ({escape(str(latest_live['signal']))}) vs v82=<strong>{escape(str(latest_shadow['status']))}</strong> ({escape(str(latest_shadow['signal']))}).</p>
  </section>
  <section class="grid">{cards}</section>
  <section>
    <h2>Recent Divergences</h2>
    <table>
      <thead>
        <tr>
          <th>Date</th>
          <th>Case</th>
          <th>Owner</th>
          <th>Pass Count</th>
          <th>Gap</th>
          <th>Volume</th>
          <th>Range z</th>
          <th>Intraday</th>
          <th>Breakout</th>
          <th>Live</th>
          <th>v82</th>
        </tr>
      </thead>
      <tbody>{rows}</tbody>
    </table>
  </section>
</body>
</html>"""


def main() -> None:
    ensure_output_dir()
    raw_prices = download_asset_prices()
    live_rows = read_live_rows(lookback_days=None)
    shadow_rows, metadata = build_shadow_rows(lookback_days=None, raw_prices=raw_prices)
    context_frame = build_context_frame(raw_prices)
    compare = build_compare_frame(live_rows, shadow_rows, context_frame=context_frame)
    if compare.empty:
        raise ValueError("MU v82 compare frame is empty.")

    board = build_shadow_board(compare, metadata)
    diff = build_diff_frame(compare)

    board.to_csv(get_shadow_board_path(), sep="\t", index=False)
    compare.to_csv(get_shadow_recent_path(), sep="\t", index=False)
    diff.to_csv(get_shadow_diff_path(), sep="\t", index=False)
    get_shadow_html_path().write_text(render_shadow_html(board, diff), encoding="utf-8")

    latest = compare.iloc[-1]
    print(
        json.dumps(
            {
                "asset_key": ASSET_KEY,
                "rule_name": RULE_NAME,
                "output_dir": str(get_output_dir()),
                "shadow_board_path": str(get_shadow_board_path()),
                "shadow_recent_path": str(get_shadow_recent_path()),
                "shadow_diff_path": str(get_shadow_diff_path()),
                "shadow_html_path": str(get_shadow_html_path()),
                "latest_date": str(latest["date"]),
                "latest_comparison_state": str(latest["comparison_state"]),
                "latest_divergence_case": str(latest["divergence_case"]),
                "latest_criteria_pass_count": int(latest["shadow_criteria_pass_count"]),
                "latest_rule_match": bool(latest["shadow_selected"]),
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
