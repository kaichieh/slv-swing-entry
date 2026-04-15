from __future__ import annotations

import json
from pathlib import Path

import asset_config as ac
import prepare as pr
import research_batch as rb

ASSET_KEY = "nvda"
HORIZON_DAYS = 60
UPPER_BARRIER = 0.15
LOWER_BARRIER = -0.08
LABEL_MODE = "future-return-top-bottom-15pct"
MODEL_FAMILY = "regime_dual_logistic"
GATE_FEATURE = "above_200dma_flag"
EXTRA_FEATURES = (
    "ret_60",
    "sma_gap_60",
    "atr_pct_20",
    "close_location_20",
)


def evaluate_winning_algorithm() -> dict[str, float | str | bool | tuple[str, ...]]:
    symbol = ac.get_asset_symbol(ASSET_KEY)
    raw = pr.download_symbol_prices(symbol, ac.stooq_url(symbol), str(ac.get_raw_data_path(ASSET_KEY)))
    frame = rb.build_labeled_frame(
        raw,
        horizon_days=HORIZON_DAYS,
        upper_barrier=UPPER_BARRIER,
        lower_barrier=LOWER_BARRIER,
        label_mode=LABEL_MODE,
    )
    result, _artifacts = rb.train_model(
        frame,
        "nvda_topbottom15_regime_dual_logistic",
        extra_features=EXTRA_FEATURES,
        model_family=MODEL_FAMILY,
        gate_feature=GATE_FEATURE,
    )
    return {
        "asset": ASSET_KEY,
        "symbol": symbol,
        "horizon_days": HORIZON_DAYS,
        "upper_barrier": round(UPPER_BARRIER, 4),
        "lower_barrier": round(LOWER_BARRIER, 4),
        "label_mode": LABEL_MODE,
        "model_family": MODEL_FAMILY,
        "gate_feature": GATE_FEATURE,
        "extra_features": EXTRA_FEATURES,
        "threshold": round(float(result.threshold), 4),
        "validation_f1": round(float(result.validation_f1), 4),
        "validation_bal_acc": round(float(result.validation_bal_acc), 4),
        "test_f1": round(float(result.test_f1), 4),
        "test_bal_acc": round(float(result.test_bal_acc), 4),
        "test_positive_rate": round(float(result.test_positive_rate), 4),
        "headline_score": round(
            float(
                rb.compute_headline_score(
                    result.validation_f1,
                    result.validation_bal_acc,
                    result.test_f1,
                    result.test_bal_acc,
                )
            ),
            4,
        ),
        "promotion_gate_passed": rb.passes_promotion_gate(
            float(result.validation_bal_acc),
            float(result.test_bal_acc),
        ),
    }


def main() -> None:
    payload = evaluate_winning_algorithm()
    output_path = Path(ac.get_cache_dir(ASSET_KEY)) / "nvda_topbottom15_regime_dual_logistic.json"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(json.dumps({"output_path": str(output_path), **payload}, indent=2))


if __name__ == "__main__":
    main()
