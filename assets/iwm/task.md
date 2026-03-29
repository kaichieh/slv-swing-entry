# IWM Backlog

## Round 1 Baseline

- [x] Run `AR_ASSET=iwm python prepare.py` and confirm dataset shape. Performance: `rows=4769`, `train/validation/test=3338/715/716`, `positive_rate=0.3330`, `date_range=2001-05-25 -> 2026-03-10`, label config `60d +10%/-5% drop-neutral`.
- [x] Run `AR_ASSET=iwm python train.py` and capture baseline metrics for `60d +10%/-5% drop-neutral`. Performance: `validation_f1=0.5501`, `validation_bal_acc=0.6058`, `test_f1=0.5804`, `test_bal_acc=0.5560`, `threshold=0.450`, `headline_score=0.5730`, `promotion_gate=pass`, `test_positive_rate=0.7374`.
- [x] Run `AR_ASSET=iwm python predict_latest.py` for the baseline live snapshot. Performance: `latest_date=2026-03-10`, `signal=weak_bullish`, `predicted_probability=0.4731`, `decision_threshold=0.4500`, `top_20pct_reference=false`.
- [x] Run `AR_ASSET=iwm python chart_signals.py` and confirm chart output. Performance: `bars_rendered=1260`, `latest_date=2026-03-10`, `output=.cache/iwm-swing-entry/signal_chart.html`.
- [x] Write the baseline row into `assets/iwm/results.tsv`. Performance: baseline row recorded.

## Round 2 Label Sanity

- [ ] Compare `drop-neutral` versus `keep-all binary`.
- [x] Compare `60d +10%/-5%`, `60d +12%/-6%`, and `60d +8%/-4%`. Performance: neither alternative beat the default baseline. `60d +8%/-4%` reached `test_bal_acc=0.5605` but only `headline_score=0.5482`, while `60d +12%/-6%` reached `test_bal_acc=0.5633` but `headline_score=0.5429`. The default `60d +10%/-5%` line remained strongest at `headline_score=0.5730`.
- [x] Compare `40d +10%/-5%` versus `60d +10%/-5%`. Performance: `40d +10%/-5%` weakened too much on test quality with `test_f1=0.4028`, `test_bal_acc=0.5316`, `headline_score=0.4917`.
- [x] Review whether IWM is cleaner than SPY or simply a noisier broad-beta line. Performance: IWM is clearly cleaner than SPY on the current workflow. It already passed the gate on the baseline and the nearby label sweep did not reveal a better replacement, which means the baseline itself is a credible reference line rather than a degenerate market-beta model.

## Round 3 Feature Sweep

- [x] Test `ret_60`, `sma_gap_60`, `rolling_vol_60`, `atr_pct_20`, `distance_to_252_high`, and `rs_vs_benchmark_60` versus `SPY`. Performance: the strongest add-on was `rs_vs_benchmark_60`, reaching `validation_f1=0.5270`, `validation_bal_acc=0.5753`, `test_f1=0.5924`, `test_bal_acc=0.5643`, `headline_score=0.5692`. `distance_to_252_high` and `ret_60 + sma_gap_60` were close behind at `0.5655` and `0.5647`, and `rolling_vol_60` was the cleanest validation-side add-on at `validation_bal_acc=0.6256`. But the key conclusion is that the baseline itself still remained strongest at `headline_score=0.5730`, so the feature sweep did not dislodge it.

## Next Round

- [ ] Because IWM already has a pass-level baseline and no better feature extension yet, compare threshold versus top-percentile rules on the default baseline before trying more features.
- [ ] Add walk-forward validation on the baseline and the `rs_vs_benchmark_60` side candidate to confirm whether the edge is robust.

## Notes

- IWM is the repo's intended small-cap cycle line, so relative performance versus SPY matters.
- IWM immediately looks like the strongest of the new macro basket, so the next round should focus on validation and simplification rather than rescue work.
- Because the baseline already passed, the next IWM round should move to feature and rule validation rather than more label tuning.
- The first feature sweep suggests `rs_vs_benchmark_60` is the only IWM add-on clearly worth keeping around for later validation.
