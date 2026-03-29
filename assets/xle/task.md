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

## Round 4 Regression Validation

- [x] Formalize the first XLE ranking path with saved summary, recent, and walk-forward outputs on `ret_60 + sma_gap_60`. Performance: `assets/xle/regression_summary.tsv` confirmed that both `top` and `bottom` buckets can beat the full test average, but `bottom 10%` remained the cleanest operating choice at `test_avg_return=5.72%` versus the overall `3.30%`, with `65.69%` hit rate. `assets/xle/regression_recent.tsv` showed the latest saved row on `2026-03-26` was not selected. `assets/xle/regression_walkforward.tsv` stayed mixed but materially better than TLT: fold 1 was still weak at `-1.14%`, while folds 2 and 3 reached `8.15%` and `6.16%` test bucket returns. That keeps XLE on a credible ranking-style path without yet supporting adoption.

## Round 5 Regression Candidate Compare

- [x] Compare the current XLE ranking candidate against nearby alternatives. Performance: `assets/xle/regression_candidate_compare.tsv` kept `ret_60 + sma_gap_60` in front overall. `distance_to_252_high` had a flashy `top 5% test_avg_return=5.09%`, but its `bottom 10%` line only reached `5.40%` with weaker hit rate than the incumbent. `atr_pct_20` was similar but slightly weaker. The current best XLE interpretation remains `ret_60 + sma_gap_60` through the `bottom 10%` bucket at `5.72%` average return and `65.69%` hit rate.

## Round 6 Walk-Forward Compare

- [x] Compare the two most plausible XLE ranking candidates directly under walk-forward. Performance: `assets/xle/regression_walkforward_compare.tsv` showed that `distance_to_252_high` is now the more stable operating choice even though it trailed slightly on the static full-sample table. It reached `avg_bucket_return=5.84%`, `avg_hit_rate=65.45%`, and crucially kept `min_fold_excess_return=+0.49%`, while `ret_60 + sma_gap_60` fell to `min_fold_excess_return=-1.24%`. That means XLE now has a split: the old combo still looks good on the static split, but `distance_to_252_high` is the cleaner walk-forward candidate.

## Round 7 Decision Summary

- [x] Save a recent operating decision summary for the leading XLE ranking candidates. Performance: `assets/xle/regression_decision_summary.tsv` confirmed that the walk-forward winner is also the more live-like line. `distance_to_252_high + bottom 10%` selected `6` of the latest `60` rows and was last active on `2026-02-19`, while `ret_60 + sma_gap_60 + bottom 10%` selected `0` of the latest `60`. So XLE should now treat `distance_to_252_high + bottom 10%` as the active operating candidate, even if the older combo still looks fine on one static split.

## Round 8 Operating Preference

- [x] Save a direct operating preference summary for the two XLE candidates. Performance: `assets/xle/regression_operating_preference.tsv` tightened the same conclusion with walk-forward context included. `distance_to_252_high + bottom 10%` kept `recent_selected_count=6`, `last_selected_date=2026-02-19`, and a positive `min_fold_excess_return=+0.49%`, while `ret_60 + sma_gap_60 + bottom 10%` stayed at `0` recent selections and `-1.24%` worst-fold excess. This means the repo can now treat the distance-based line as the clear XLE operating preference, not just a tentative alternative.

## Round 9 Active Output Refresh

- [x] Refresh the active XLE regression recent output and chart on `distance_to_252_high + bottom 10%`. Performance: `assets/xle/regression_recent.tsv` and `assets/xle/regression_recent.html` are now aligned to the active distance-based line. The latest saved row `2026-03-26` was not selected, but the recent window still contained `6` selections and last fired on `2026-02-19`, which is enough to justify treating it as the current XLE operating watchlist.

## Next Round

- [ ] If XLE work continues, promote `distance_to_252_high + bottom 10%` into recent/rule-style monitoring and treat it as the leading operating candidate.
- [ ] Keep XLE on a ranking-style workflow rather than retrying nearby binary barriers.

## Notes

- XLE is intended to cover inflation and commodity-driven equity regimes that are underrepresented in the current set.
- The first baseline acted like a commodity-beta always-long model, so the next round should focus on label redesign or stronger regime filters before broader feature sweeps.
- The label sanity pass confirmed that no nearby barrier fixes the problem, so the next useful XLE step is regime or formulation change, not more of the same binary tuning.
- The first regression prototype now points to `ret_60 + sma_gap_60` as the cleanest XLE side path if the asset stays on a ranking-style workflow, but it still needs one more direct ranking compare before it can become an operating line.
