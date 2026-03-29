"""
Compare multiple ridge-regression ranking feature sets on future_return_60.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass

import pandas as pd

import asset_config as ac
import research_regression as rr

OUTPUT_PATH = str(ac.get_regression_compare_output_path())


@dataclass
class RegressionCompareRow:
    name: str
    feature_count: int
    rows: int
    validation_corr: float
    test_corr: float
    validation_top15_avg_return: float
    validation_bottom15_avg_return: float
    test_top15_avg_return: float
    test_bottom15_avg_return: float
    sign_match: bool
    preferred_direction: str


def feature_specs() -> list[tuple[str, tuple[str, ...]]]:
    return [
        ("baseline", ()),
        ("ret_60", ("ret_60",)),
        ("sma_gap_60", ("sma_gap_60",)),
        ("atr_pct_20", ("atr_pct_20",)),
        ("distance_to_252_high", ("distance_to_252_high",)),
        ("ret_60_plus_sma_gap_60", ("ret_60", "sma_gap_60")),
        ("ret_60_plus_sma_gap_60_plus_atr_pct_20", ("ret_60", "sma_gap_60", "atr_pct_20")),
        (
            "ret_60_plus_sma_gap_60_plus_distance_to_252_high",
            ("ret_60", "sma_gap_60", "distance_to_252_high"),
        ),
    ]


def build_feature_names(frame: pd.DataFrame, extras: tuple[str, ...]) -> list[str]:
    feature_names = list(rr.pr.FEATURE_COLUMNS)
    for column in extras:
        if column in frame.columns and column not in feature_names:
            feature_names.append(column)
    return feature_names


def run_one(frame: pd.DataFrame, name: str, extras: tuple[str, ...]) -> RegressionCompareRow:
    feature_names = build_feature_names(frame, extras)
    clean = frame.dropna(subset=feature_names + ["future_return_60"]).reset_index(drop=True)
    splits = rr.split_frame(clean)
    train_x = splits["train"][feature_names].to_numpy(dtype=float)
    valid_x = splits["validation"][feature_names].to_numpy(dtype=float)
    test_x = splits["test"][feature_names].to_numpy(dtype=float)
    train_y = splits["train"]["future_return_60"].to_numpy(dtype=float)
    valid_y = splits["validation"]["future_return_60"].to_numpy(dtype=float)
    test_y = splits["test"]["future_return_60"].to_numpy(dtype=float)

    train_x, [valid_x, test_x] = rr.standardize(train_x, [valid_x, test_x])
    weights = rr.fit_ridge_regression(train_x, train_y, rr.DEFAULT_L2_REG)
    valid_pred = rr.predict(valid_x, weights)
    test_pred = rr.predict(test_x, weights)

    valid_top = rr.compute_bucket_stat("validation", "top", valid_pred, valid_y, 15.0)
    valid_bottom = rr.compute_bucket_stat("validation", "bottom", valid_pred, valid_y, 15.0)
    test_top = rr.compute_bucket_stat("test", "top", test_pred, test_y, 15.0)
    test_bottom = rr.compute_bucket_stat("test", "bottom", test_pred, test_y, 15.0)

    sign_match = (valid_top.avg_return >= valid_bottom.avg_return and test_top.avg_return >= test_bottom.avg_return) or (
        valid_top.avg_return <= valid_bottom.avg_return and test_top.avg_return <= test_bottom.avg_return
    )
    preferred_direction = "top" if test_top.avg_return >= test_bottom.avg_return else "bottom"

    return RegressionCompareRow(
        name=name,
        feature_count=len(feature_names),
        rows=len(clean),
        validation_corr=rr.safe_corr(valid_pred, valid_y),
        test_corr=rr.safe_corr(test_pred, test_y),
        validation_top15_avg_return=valid_top.avg_return,
        validation_bottom15_avg_return=valid_bottom.avg_return,
        test_top15_avg_return=test_top.avg_return,
        test_bottom15_avg_return=test_bottom.avg_return,
        sign_match=sign_match,
        preferred_direction=preferred_direction,
    )


def main() -> None:
    frame, _feature_names = rr.build_dataset()
    rows = [run_one(frame, name, extras) for name, extras in feature_specs()]
    table = pd.DataFrame([asdict(row) for row in rows]).sort_values(
        by=["sign_match", "test_bottom15_avg_return", "test_top15_avg_return"],
        ascending=[False, False, False],
    )
    table.to_csv(OUTPUT_PATH, sep="\t", index=False)
    print(json.dumps(table.to_dict(orient="records"), indent=2))


if __name__ == "__main__":
    main()
