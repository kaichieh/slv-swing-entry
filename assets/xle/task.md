# XLE Backlog

## Round 1 Baseline

- [x] Run `AR_ASSET=xle python prepare.py` and confirm dataset shape. Performance: `rows=5752`, `train/validation/test=4026/862/864`, `positive_rate=0.3390`, `date_range=1999-12-21 -> 2026-03-11`, label config `60d +10%/-5% drop-neutral`.
- [x] Run `AR_ASSET=xle python train.py` and capture baseline metrics for `60d +10%/-5% drop-neutral`. Performance: `validation_f1=0.4030`, `validation_bal_acc=0.5046`, `test_f1=0.5319`, `test_bal_acc=0.5000`, `threshold=0.315`, `headline_score=0.4936`, `promotion_gate=fail`, `test_positive_rate=1.0000`.
- [x] Run `AR_ASSET=xle python predict_latest.py` for the baseline live snapshot. Performance: `latest_date=2026-03-11`, `signal=no_entry`, `raw_model_signal=weak_bullish`, `predicted_probability=0.4317`, `decision_threshold=0.3150`, `top_20pct_reference=false`, `buy_point_ok=false`.
- [x] Run `AR_ASSET=xle python chart_signals.py` and confirm chart output. Performance: `bars_rendered=1260`, `latest_date=2026-03-11`, `output=.cache/xle-swing-entry/signal_chart.html`.
- [x] Write the baseline row into `assets/xle/results.tsv`. Performance: baseline row recorded.

## Round 2 Label Sanity

- [ ] Compare `drop-neutral` versus `keep-all binary`.
- [ ] Compare `60d +10%/-5%`, `60d +12%/-6%`, and `60d +8%/-4%`.
- [ ] Compare `40d +10%/-5%` versus `60d +10%/-5%`.
- [ ] Review whether XLE is more interpretable than broad equities under the current barrier workflow.

## Round 3 Feature Sweep

- [ ] Test `ret_60`.
- [ ] Test `sma_gap_60`.
- [ ] Test `rolling_vol_60`.
- [ ] Test `atr_pct_20`.
- [ ] Test `distance_to_252_high`.
- [ ] Test `drawdown_60`.

## Next Round

- [ ] If XLE finds a credible candidate, compare threshold versus top-percentile rules.
- [ ] If XLE stays too regime-sensitive, use walk-forward validation before any adoption decision.

## Notes

- XLE is intended to cover inflation and commodity-driven equity regimes that are underrepresented in the current set.
- The first baseline acted like a commodity-beta always-long model, so the next round should focus on label redesign or stronger regime filters before broader feature sweeps.
