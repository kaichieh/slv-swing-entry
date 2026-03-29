# TLT Backlog

## Round 1 Baseline

- [x] Run `AR_ASSET=tlt python prepare.py` and confirm dataset shape. Performance: `rows=4628`, `train/validation/test=3239/694/695`, `positive_rate=0.3460`, `date_range=2003-07-30 -> 2026-03-10`, label config `60d +6%/-3% drop-neutral`.
- [x] Run `AR_ASSET=tlt python train.py` and capture baseline metrics for `60d +6%/-3% drop-neutral`. Performance: `validation_f1=0.3851`, `validation_bal_acc=0.5019`, `test_f1=0.3912`, `test_bal_acc=0.5000`, `threshold=0.433`, `headline_score=0.4174`, `promotion_gate=fail`, `test_positive_rate=1.0000`.
- [x] Run `AR_ASSET=tlt python predict_latest.py` for the baseline live snapshot. Performance: `latest_date=2026-03-10`, `signal=weak_bullish`, `raw_model_signal=bullish`, `predicted_probability=0.4969`, `decision_threshold=0.4330`, `top_20pct_reference=true`, but `buy_point_ok=false`.
- [x] Run `AR_ASSET=tlt python chart_signals.py` and confirm chart output. Performance: `bars_rendered=1260`, `latest_date=2026-03-10`, `output=.cache/tlt-swing-entry/signal_chart.html`.
- [x] Write the baseline row into `assets/tlt/results.tsv`. Performance: baseline row recorded.

## Round 2 Label Sanity

- [ ] Compare `drop-neutral` versus `keep-all binary`.
- [x] Compare `60d +6%/-3%`, `60d +8%/-4%`, and `60d +4%/-2%`. Performance: `60d +4%/-2%` had the highest headline score at `0.4693`, but it stayed fully collapsed with `test_positive_rate=1.0000`. `60d +8%/-4%` was the only less-degenerate line, reducing `test_positive_rate` to `0.3439` and lifting `test_bal_acc` to `0.5277`, but its overall quality stayed weak at `headline_score=0.3855`.
- [x] Compare `40d +6%/-3%` versus `60d +6%/-3%`. Performance: `40d +6%/-3%` was also weak, with `test_f1=0.2587`, `test_bal_acc=0.4649`, `headline_score=0.3673`.
- [x] Review whether TLT produces a genuinely different signal family from equities. Performance: yes, but not in a good way under the current binary workflow. The line is much more label-sensitive than the equity assets, and the least-degenerate candidate is still too weak to justify a normal feature sweep.

## Round 3 Feature Sweep

- [x] Run a first regression prototype instead of a normal feature sweep. Performance: `assets/tlt/regression_prototype_summary.tsv` confirmed that TLT behaves more like a formulation problem than a standard feature problem. The best current prototype was `atr_pct_20` with `validation_corr=0.0724`, `test_corr=-0.0955`, and `test_bottom10_avg_return=0.29%`, while the full test average stayed negative near `-0.93%`. `distance_to_252_high` and the baseline regression both stayed weak. This is not a ready signal, but it is still more promising than the binary classifier path.

## Round 4 Regression Validation

- [x] Formalize the first TLT ranking path with saved summary, recent, and walk-forward outputs using `atr_pct_20`. Performance: `assets/tlt/regression_summary.tsv` showed that the least-bad operating choice is `bottom 5%`, with `test_avg_return=0.73%` against an overall `test_avg_return=-0.93%`, while the `top` buckets stayed clearly negative. `assets/tlt/regression_recent.tsv` showed the latest saved row on `2026-03-26` was not selected. `assets/tlt/regression_walkforward.tsv` was mixed but still directionally interesting: fold 1 reached `test_bucket_avg_return=1.48%` versus `test_avg_return=0.46%`, fold 2 stayed weak at `-0.18%`, and fold 3 recovered to `0.48%` while the full fold average was `-1.65%`. This keeps TLT on a research-only regression track.

## Round 5 Regression Candidate Compare

- [x] Test whether one extra context feature can improve the TLT regression line. Performance: `assets/tlt/regression_candidate_compare.tsv` compared `atr_pct_20` against `atr_pct_20 + distance_to_252_high`. The extension changed the sign of the ranking but not for the better: at both `5%` and `10%`, the combined line preferred the `top` bucket, yet still produced negative test returns at `-0.94%` and `-0.38%`. The plain `atr_pct_20` line remained better, with `bottom 5% test_avg_return=0.73%` and `bottom 10% test_avg_return=0.29%`.

## Round 6 Regression Family Compare

- [x] Compare the current volatility-style TLT ranking line against a genuinely different price-action family. Performance: `assets/tlt/regression_family_walkforward.tsv` and `assets/tlt/regression_family_recent.tsv` compared `atr_pct_20` against `ret_60 + sma_gap_60` on the `bottom 5%` bucket. The result was decisive: `atr_pct_20` kept a positive `avg_bucket_return=0.59%` with `min_fold_excess_return=-0.31%`, while the price-action family fell to `avg_bucket_return=-0.81%` and `min_fold_excess_return=-1.50%`. The recent rows for the price-action family also stayed entirely inactive through `2026-03-26`. So TLT should stay on the volatility-style regression track, not pivot to a broad trend family.

## Round 7 Decision Summary

- [x] Save a decision summary for the current and alternate TLT regression families. Performance: `assets/tlt/regression_decision_summary.tsv` compared `atr_pct_20` with a different mean-reversion family, `drawdown_20`, on the `bottom 5%` bucket. Neither selected any of the latest `60` rows through `2026-03-26`, but `atr_pct_20` still had the cleaner operating cutoff at `-0.0104` versus `-0.0078` for `drawdown_20`. This reinforces that TLT still does not have a live-like watchlist line, but `atr_pct_20` remains the only credible base if work continues.

## Round 8 Family Tiebreak

- [x] Add one more genuinely different TLT family to settle the ranking track. Performance: `assets/tlt/regression_family_decision.tsv` added `close_location_20` to the decision compare. It also failed to produce any recent selections and had the weakest robustness with `min_fold_excess_return=-2.13%`, worse than both `atr_pct_20` and `drawdown_20`. That closes the tiebreak cleanly: `atr_pct_20` is still the only TLT family worth carrying forward.

## Round 9 Active Output Refresh

- [x] Refresh the active TLT regression recent output and chart on the surviving `atr_pct_20 + bottom 5%` line. Performance: `assets/tlt/regression_recent.tsv` and `assets/tlt/regression_recent.html` are now aligned to that active line. The latest saved row `2026-03-26` remained unselected, with `predicted_return=0.0088` versus cutoff `-0.0104`. This does not change the research conclusion, but it makes the active TLT line explicit for future review.

## Round 10 Active Status Summary

- [x] Save a one-file active status summary for the surviving TLT regression line. Performance: `assets/tlt/active_status_summary.tsv` now captures the current state of `atr_pct_20 + bottom 5%` in one place. The line remains inactive with `recent_selected_count=0`, latest `predicted_return=0.0088`, and no recent selected rows, which reinforces that TLT is still research-only unless a truly new formulation is introduced.

## Round 11 Active Status HTML

- [x] Render a lightweight HTML status page for the surviving TLT regression line. Performance: `assets/tlt/active_status.html` now gives TLT a visual research dashboard consistent with the other assets. It keeps the current message simple: `atr_pct_20 + bottom 5%` is still the only line worth carrying, and it is still inactive.

## Round 12 Monitor Snapshot

- [x] Save a preferred-line monitor snapshot for day-to-day use. Performance: `assets/tlt/monitor_snapshot.tsv` now makes the TLT stance explicit in one row. The preferred line remains `atr_pct_20_bottom5`, but the action is `research_only`, which formally separates TLT from the repo's watchlist-ready assets.

## Next Round

- [ ] If TLT work continues, compare `atr_pct_20` against a genuinely different ranking family rather than another nearby context extension.
- [ ] Do not return TLT to the binary workflow unless a genuinely different label family is introduced.

## Notes

- TLT is intended to cover rates and recession regimes, so even a modestly useful line would diversify the repo a lot.
- The first baseline strongly suggests TLT may need a different formulation or a narrower label before feature work is worth much.
- The current TLT evidence now points more strongly toward a formulation change or ranking-style workflow, not a standard binary feature round.
- The first regression prototype supports that direction: if TLT work continues, it should stay on a regression/ranking track, not return to a normal binary feature sweep.
