# XLE Backlog

## Round 1 Baseline

- [x] Run `AR_ASSET=xle python prepare.py` and confirm dataset shape. Performance: `rows=5752`, `train/validation/test=4026/862/864`, `positive_rate=0.3390`, `date_range=1999-12-21 -> 2026-03-11`, label config `60d +10%/-5% drop-neutral`.
- [x] Run `AR_ASSET=xle python train.py` and capture baseline metrics for `60d +10%/-5% drop-neutral`. Performance: `validation_f1=0.4030`, `validation_bal_acc=0.5046`, `test_f1=0.5319`, `test_bal_acc=0.5000`, `threshold=0.315`, `headline_score=0.4936`, `promotion_gate=fail`, `test_positive_rate=1.0000`.
- [x] Run `AR_ASSET=xle python predict_latest.py` for the baseline live snapshot. Performance: `latest_date=2026-03-11`, `signal=no_entry`, `raw_model_signal=weak_bullish`, `predicted_probability=0.4317`, `decision_threshold=0.3150`, `top_20pct_reference=false`, `buy_point_ok=false`.
- [x] Run `AR_ASSET=xle python chart_signals.py` and confirm chart output. Performance: `bars_rendered=1260`, `latest_date=2026-03-11`, `output=.cache/xle-swing-entry/signal_chart.html`.
- [x] Write the baseline row into `assets/xle/results.tsv`. Performance: baseline row recorded.

## Round 2 Label Sanity

- [ ] Compare `drop-neutral` versus `keep-all binary`.
- [x] Compare `60d +10%/-5%`, `60d +12%/-6%`, and `60d +8%/-4%`. Performance: none of the nearby barriers fixed the collapse. `60d +8%/-4%` posted the best headline score at `0.5079`, but `test_positive_rate` was still `1.0000`; `60d +12%/-6%` also stayed fully degenerate with `headline_score=0.4952`.
- [x] Compare `40d +10%/-5%` versus `60d +10%/-5%`. Performance: `40d +10%/-5%` did not help, with `test_f1=0.5191`, `test_bal_acc=0.5000`, `headline_score=0.4897`.
- [x] Review whether XLE is more interpretable than broad equities under the current barrier workflow. Performance: not yet. XLE still behaves more like an all-positive commodity-beta classifier than a usable swing-entry line.

## Round 3 Feature Sweep

- [x] Run a first regression prototype instead of a normal feature sweep. Performance: `assets/xle/regression_prototype_summary.tsv` showed that XLE is at least more recoverable than TLT under a ranking formulation. The best current prototype was `ret_60 + sma_gap_60`, with `validation_corr=0.0344`, `test_corr=-0.0599`, `test_bottom10_avg_return=5.72%`, and `test_avg_return=3.30%`. `distance_to_252_high` and `atr_pct_20` were slightly weaker but still directionally useful. This does not rescue the binary line, but it gives XLE a credible ranking-style path.

## Next Round

- [ ] If XLE finds a credible candidate, compare threshold versus top-percentile rules.
- [ ] If XLE stays too regime-sensitive, use walk-forward validation before any adoption decision.

## Notes

- XLE is intended to cover inflation and commodity-driven equity regimes that are underrepresented in the current set.
- The first baseline acted like a commodity-beta always-long model, so the next round should focus on label redesign or stronger regime filters before broader feature sweeps.
- The label sanity pass confirmed that no nearby barrier fixes the problem, so the next useful XLE step is regime or formulation change, not more of the same binary tuning.
- The first regression prototype now points to `ret_60 + sma_gap_60` as the cleanest XLE side path if the asset stays on a ranking-style workflow.
