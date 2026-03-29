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

## Round 5 Live Review

- [x] Re-run live prediction and chart for the adopted TSLA candidate `60d +15%/-8% + ret_60 + sma_gap_60 + distance_to_252_high`. Performance: `latest_date=2026-03-18`, `signal=no_entry`, `predicted_probability=0.4136`, `decision_threshold=0.5080`, `top_20pct_reference=false`, `buy_point_ok=true`, `output=.cache/tsla-swing-entry/signal_chart.html`; the adopted line no longer behaves like an always-long model.

## Next Round

- [x] Compare threshold versus top-percentile rules on the winning TSLA combo, because TSLA may benefit from a smaller set of higher-conviction entries. Performance: the clean rerun on `ret_60 + sma_gap_60 + distance_to_252_high` showed that threshold remains the best pure classifier rule, but the higher-conviction percentile rules improved forward trade quality. `threshold` reached `trade_count=33`, `hit_rate=60.61%`, `avg_return=13.41%`; `top_10pct` cut the sample to `16` trades and reached `hit_rate=75.00%`, `avg_return=19.63%`; `top_15pct` reached `20` trades with `avg_return=19.45%`; `top_20pct` was the strongest forward-return rule with `trade_count=21`, `hit_rate=66.67%`, `avg_return=22.90%`.
- [x] Add a 4-fold walk-forward check to confirm the TSLA combo is not only exploiting one market regime. Performance: the walk-forward rerun was not clean enough to promote the line. Fold 1 gave `test_f1=0.6520`, but `test_bal_acc=0.5000` with `test_positive_rate=1.0000`; fold 2 dropped to `test_bal_acc=0.4477`; fold 3 again collapsed to `test_positive_rate=1.0000`. This means the adopted TSLA line is still useful in the full-sample split, but it has not yet proven stable under rolling retraining.
- [x] Compare the adopted TSLA line against the simpler pass-level candidates to see whether a stability-first fallback should replace it. Performance: a dedicated candidate compare was saved to `assets/tsla/candidate_validation_summary.tsv`, `assets/tsla/candidate_forward_summary.tsv`, and `assets/tsla/candidate_walkforward_summary.tsv`. The adopted line `ret_60 + sma_gap_60 + distance_to_252_high` still led on full-sample quality with `headline_score=0.5853`, ahead of `distance_to_252_high` at `0.5747` and `ret_60 + distance_to_252_high` at `0.5743`. But the simpler `ret_60 + distance_to_252_high` line was the most stable fallback in the rolling check: fold 3 reached `test_bal_acc=0.5582` with `test_positive_rate=0.7752`, while the adopted line fell back to `test_bal_acc=0.5000` and `test_positive_rate=1.0000`. It also produced the strongest high-conviction forward overlay at `top_15pct avg_return=25.69%`, above the adopted line's best `top_20pct avg_return=22.90%`. That makes it the best robustness-first runner-up, but not enough to replace the current adopted line on full-sample evidence alone.
- [x] Compare operating rules directly between the adopted TSLA line and the stability-first fallback. Performance: `assets/tsla/operator_rule_summary.tsv` confirmed the split between the two roles. The adopted line still has the best base classifier quality, but the best operator-style overlay is now `ret_60 + distance_to_252_high + top_15pct`, with `trade_count=19`, `hit_rate=73.68%`, `avg_return=25.69%`, and `max_drawdown_compound=0.0`. By comparison, the adopted line's best overlay remained `top_20pct` at `avg_return=22.90%`. So the adopted line stays as the model reference, while the fallback-plus-`top_15pct` becomes the strongest conservative execution overlay.
- [x] Save a recent operator comparison for the adopted TSLA line and the conservative fallback overlay. Performance: `assets/tsla/operator_recent.tsv` now tracks both the adopted `top_20pct` overlay and the fallback `top_15pct` overlay. On the latest saved row `2026-03-18`, neither overlay was selected: the adopted probability was `0.4136` against cutoff `0.5769`, and the fallback probability was `0.3913` against cutoff `0.6578`.
- [ ] If the combo stays stable under walk-forward, promote it from adopted candidate to documented default operating line in the TSLA notes. Performance: blocked for now because the current walk-forward pass is still too regime-sensitive.

## Notes

- TSLA is no longer purely label-limited; `distance_to_252_high` unlocked a meaningful separation signal.
- The current adopted TSLA path is `60d +15%/-8% + ret_60 + sma_gap_60 + distance_to_252_high`.
- If we need a more conservative TSLA operating overlay later, `ret_60 + distance_to_252_high + top_15pct` is now the cleanest fallback candidate.
