# TSLA Backlog

## Round 1 Baseline

- [x] Run `AR_ASSET=tsla python prepare.py` and confirm dataset shape. Performance: `rows=3705`, `train/validation/test=2593/555/557`, `positive_rate=0.4000`, `date_range=2011-06-27 -> 2026-03-25`, label config `60d +12%/-6% drop-neutral`.
- [x] Run `AR_ASSET=tsla python train.py` and capture baseline metrics. Performance: `validation_f1=0.4622`, `validation_bal_acc=0.5077`, `test_f1=0.4986`, `test_bal_acc=0.4987`, `threshold=0.382`, `headline_score=0.4923`, `promotion_gate=fail`.
- [x] Run `AR_ASSET=tsla python predict_latest.py` for the baseline live snapshot. Performance: `latest_date=2026-03-25`, `signal=weak_bullish`, `predicted_probability=0.4350`, `decision_threshold=0.3820`, `top_20pct_reference=false`.
- [x] Run `AR_ASSET=tsla python chart_signals.py` and confirm chart output. Performance: `bars_rendered=1260`, `latest_date=2026-03-25`, `output=.cache/tsla-swing-entry/signal_chart.html`.
- [x] Write the baseline row into `assets/tsla/results.tsv`. Performance: baseline row recorded.

## Round 2 Label Sanity

- [x] Compare `drop-neutral` with `keep-all binary`. Performance: `keep-all binary` stayed almost identical to baseline at `validation_f1=0.4551`, `validation_bal_acc=0.5076`, `test_f1=0.5000`, `test_bal_acc=0.5000`, `headline_score=0.4918`, so neutral filtering did not materially change the outcome.
- [x] Compare `60d +12%/-6%`, `60d +10%/-5%`, and `60d +15%/-8%`. Performance: `60d +10%/-5%` slightly improved `validation_f1` to `0.4946` but weakened `test_bal_acc` to `0.4936`; `60d +15%/-8%` raised `test_f1` to `0.5455` and headline score to `0.5063`, so it became the best label to carry into feature testing.
- [x] Compare `40d +12%/-6%` versus `60d +12%/-6%`. Performance: `40d +12%/-6%` reached `validation_f1=0.4492`, `validation_bal_acc=0.5095`, `test_f1=0.5048`, `test_bal_acc=0.5056`, `headline_score=0.4944`; still too weak overall.
- [x] Review the current failure mode. Performance: the raw label sweep still leaned heavily positive, but `60d +15%/-8%` was the first TSLA label that looked worth extending with additional features.

## Round 3 Feature Sweep On `60d +15%/-8%`

- [x] Test `ret_60`. Performance: `validation_f1=0.4353`, `validation_bal_acc=0.5038`, `test_f1=0.5483`, `test_bal_acc=0.5086`, `headline_score=0.5093`; modest improvement, but still near-all-positive.
- [x] Test `sma_gap_60`. Performance: `validation_f1=0.4353`, `validation_bal_acc=0.5038`, `test_f1=0.5471`, `test_bal_acc=0.5077`, `headline_score=0.5086`; similar to `ret_60`.
- [x] Test `atr_pct_20`. Performance: `validation_f1=0.4340`, `validation_bal_acc=0.5012`, `test_f1=0.5476`, `test_bal_acc=0.5072`, `headline_score=0.5081`; little change.
- [x] Test `distance_to_252_high`. Performance: `validation_f1=0.5101`, `validation_bal_acc=0.6475`, `test_f1=0.5499`, `test_bal_acc=0.6266`, `headline_score=0.5747`, `promotion_gate=pass`; this was the first TSLA feature that genuinely broke the near-all-positive pattern.
- [x] Test `close_location_20`. Performance: `validation_f1=0.4340`, `validation_bal_acc=0.5012`, `test_f1=0.5455`, `test_bal_acc=0.5029`, `headline_score=0.5068`; no real lift.
- [x] Test `drawdown_60`. Performance: `validation_f1=0.4345`, `validation_bal_acc=0.5047`, `test_f1=0.5450`, `test_bal_acc=0.5033`, `headline_score=0.5073`; still weak.

## Round 4 Combo And Rule

- [x] Test `ret_60 + distance_to_252_high`. Performance: `validation_f1=0.5103`, `validation_bal_acc=0.6485`, `test_f1=0.5502`, `test_bal_acc=0.6242`, `headline_score=0.5743`, `promotion_gate=pass`; very close to the single-feature distance model.
- [x] Test `sma_gap_60 + distance_to_252_high`. Performance: `validation_f1=0.5063`, `validation_bal_acc=0.6488`, `test_f1=0.5124`, `test_bal_acc=0.6162`, `headline_score=0.5560`, `promotion_gate=pass`; useful but clearly weaker.
- [x] Test `ret_60 + sma_gap_60 + distance_to_252_high`. Performance: `validation_f1=0.4989`, `validation_bal_acc=0.6375`, `test_f1=0.5714`, `test_bal_acc=0.6440`, `headline_score=0.5853`, `promotion_gate=pass`; this is the strongest TSLA candidate so far.
- [x] Test `neg_weight=1.10/1.20` on the distance model. Performance: `neg_weight=1.10` gave `validation_f1=0.5101`, `validation_bal_acc=0.6475`, `test_f1=0.5511`, `test_bal_acc=0.6280`, `headline_score=0.5756`, `promotion_gate=pass`; the gain was tiny and still below the 3-feature combo.

## Next Round

- [ ] Re-run live prediction and chart for the adopted TSLA candidate `60d +15%/-8% + ret_60 + sma_gap_60 + distance_to_252_high`.
- [ ] Compare threshold versus top-percentile rules on the winning TSLA combo, because TSLA may benefit from a smaller set of higher-conviction entries.
- [ ] Add a 4-fold walk-forward check to confirm the TSLA combo is not only exploiting one market regime.

## Notes

- TSLA is no longer purely label-limited; `distance_to_252_high` unlocked a meaningful separation signal.
- The current best TSLA path is `60d +15%/-8% + ret_60 + sma_gap_60 + distance_to_252_high`.
