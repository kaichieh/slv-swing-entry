# SPY Backlog

## Round 1 Baseline

- [x] Run `AR_ASSET=spy python prepare.py` and confirm dataset shape. Performance: `rows=5763`, `train/validation/test=4034/864/865`, `positive_rate=0.3390`, `date_range=1994-01-26 -> 2026-03-19`, label config `60d +8%/-4% drop-neutral`.
- [x] Run `AR_ASSET=spy python train.py` and capture baseline metrics for `60d +8%/-4% drop-neutral`. Performance: `validation_f1=0.5628`, `validation_bal_acc=0.5042`, `test_f1=0.5248`, `test_bal_acc=0.5018`, `threshold=0.414`, `headline_score=0.5230`, `promotion_gate=fail`, `test_positive_rate=0.9977`.
- [x] Run `AR_ASSET=spy python predict_latest.py` for the baseline live snapshot. Performance: `latest_date=2026-03-19`, `signal=weak_bullish`, `predicted_probability=0.4567`, `decision_threshold=0.4140`, `top_20pct_reference=false`.
- [x] Run `AR_ASSET=spy python chart_signals.py` and confirm chart output. Performance: `bars_rendered=1260`, `latest_date=2026-03-19`, `output=.cache/spy-swing-entry/signal_chart.html`.
- [x] Write the baseline row into `assets/spy/results.tsv`. Performance: baseline row recorded.

## Round 2 Label Sanity

- [ ] Compare `drop-neutral` versus `keep-all binary`.
- [x] Compare `60d +8%/-4%`, `60d +10%/-5%`, and `60d +6%/-3%`. Performance: `60d +6%/-3%` posted the highest headline score at `0.5552`, but it remained almost fully positive with `test_positive_rate=0.9991` and `test_bal_acc=0.5008`. `60d +10%/-5%` was the cleanest non-degenerate alternative with `validation_bal_acc=0.6560`, `test_bal_acc=0.5218`, `test_positive_rate=0.6662`, but its overall `headline_score=0.5137` still trailed the default baseline. This means SPY now has a cleaner side candidate, but no clearly promotable replacement yet.
- [x] Compare `40d +8%/-4%` versus `60d +8%/-4%`. Performance: `40d +8%/-4%` reduced the all-positive behavior versus the default baseline, with `test_positive_rate=0.6731` and `test_bal_acc=0.5455`, but the overall line was too weak at `headline_score=0.4991`.
- [x] Review whether SPY is still behaving like a near-all-positive market-beta classifier. Performance: yes. The default `8/-4` and tighter `6/-3` labels both stayed too close to always-long behavior, while the wider `10/-5` label was cleaner but not strong enough to replace the baseline. SPY should still be treated as a broad-market reference rather than a ready entry model.

## Round 3 Feature Sweep

- [x] Test `ret_60`, `sma_gap_60`, `atr_pct_20`, `distance_to_252_high`, `rolling_vol_60`, and `above_200dma_flag` on the cleaner `60d +10%/-5%` SPY label. Performance: the best feature add-on was `rolling_vol_60`, with `validation_f1=0.5993`, `validation_bal_acc=0.6871`, `test_f1=0.4600`, `test_bal_acc=0.5471`, `headline_score=0.5367`, and `test_positive_rate=0.6263`. `atr_pct_20` and `distance_to_252_high` were close behind at `headline_score=0.5253` and `0.5232`, but none of them beat the broad default baseline on overall score. This means SPY now has a cleaner secondary line, but still not a better mainline candidate than its market-reference baseline.

## Round 4 Validation

- [x] Compare simpler top-percentile operating rules on the cleaner `60d +10%/-5%` SPY side path. Performance: threshold was still flat-to-negative on both candidates, with `avg_return=-0.18%` on the plain `10/-5` line and `-0.79%` on the `rolling_vol_60` extension. The only operator-style line worth keeping was `rolling_vol_60 + top_10pct`, which reached `avg_return=2.81%`, `hit_rate=50.00%`, and `max_drawdown_compound=-9.79%`, but only across `6` non-overlapping trades.
- [x] Add 4-fold walk-forward validation on the plain `10/-5` line and the `rolling_vol_60` extension. Performance: `rolling_vol_60` was modestly more stable than the plain side candidate, with `test_bal_acc=0.6223 / 0.5578 / 0.5605` across folds, versus `0.6344 / 0.5818 / 0.5373` for the plain `10/-5` line. That is enough to keep `rolling_vol_60` as the only SPY side candidate, but not enough to turn SPY into anything more than a market reference.

## Round 5 Recent Operator Output

- [x] Save a recent operator output for the only SPY side candidate worth keeping. Performance: `assets/spy/operator_recent.tsv` showed that `rolling_vol_60 + top_10pct` stayed inactive through the latest saved stretch. On `2026-03-17`, `predicted_probability=0.3895` versus cutoff `0.4522`, so the side candidate still did not produce a current selection. That reinforces the idea that SPY should remain a reference asset, not an active operating line.

## Round 6 Operating Compare

- [x] Compare the two remaining SPY operator-style side lines under walk-forward trading. Performance: `assets/spy/operator_walkforward_compare.tsv` showed almost no separation between the plain `10/-5 + top_10pct` line and the `rolling_vol_60 + top_10pct` extension. The plain line reached `trade_count=24`, `hit_rate=58.33%`, `avg_return=4.12%`, while the volatility extension reached `24`, `58.33%`, and `4.01%`. The plain line also had the slightly better worst-fold excess return. This means SPY now has no meaningful reason to prefer the extra feature, and should stay a market reference rather than a research priority.

## Next Round

- [ ] If SPY work continues at all, keep only the simpler `10/-5 + top_10pct` side line for reference and stop extending it.
- [ ] Otherwise keep SPY as the repo's market reference and stop adding nearby SPY features for now.

## Notes

- SPY should become the repo's core broad-market reference if it produces a stable line.
- The first baseline behaved like a broad-beta always-long classifier, so the next round should focus on label sanity and regime filters rather than treating SPY as a ready entry line.
- The newest label sanity pass suggests `60d +10%/-5%` is the only SPY variant worth extending, because it is the first one that looks materially less degenerate than the broad baseline.
- The first feature sweep on that `10/-5` side path suggests `rolling_vol_60` is the only add-on worth keeping for future SPY validation, and even then only as a side candidate rather than a mainline replacement.
