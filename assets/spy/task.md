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

- [ ] Test `ret_60`.
- [ ] Test `sma_gap_60`.
- [ ] Test `atr_pct_20`.
- [ ] Test `distance_to_252_high`.
- [ ] Test `rolling_vol_60`.
- [ ] Test `above_200dma_flag`.

## Next Round

- [ ] If SPY remains too broad-beta, compare simpler top-percentile operating rules before adding more features.
- [ ] If a non-degenerate line appears, run 4-fold walk-forward and forward-trade validation.

## Notes

- SPY should become the repo's core broad-market reference if it produces a stable line.
- The first baseline behaved like a broad-beta always-long classifier, so the next round should focus on label sanity and regime filters rather than treating SPY as a ready entry line.
- The newest label sanity pass suggests `60d +10%/-5%` is the only SPY variant worth extending, because it is the first one that looks materially less degenerate than the broad baseline.
