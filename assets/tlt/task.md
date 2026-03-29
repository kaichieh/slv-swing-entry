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

- [ ] Test `ret_60`.
- [ ] Test `sma_gap_60`.
- [ ] Test `rolling_vol_60`.
- [ ] Test `atr_pct_20`.
- [ ] Test `distance_to_252_high`.
- [ ] Test `rs_vs_benchmark_60` versus `SPY`.

## Next Round

- [ ] If TLT is too different for the binary workflow, test whether regression/ranking is a better fit.
- [ ] If a binary candidate works, run threshold versus percentile operating rules and walk-forward validation.

## Notes

- TLT is intended to cover rates and recession regimes, so even a modestly useful line would diversify the repo a lot.
- The first baseline strongly suggests TLT may need a different formulation or a narrower label before feature work is worth much.
- The current TLT evidence now points more strongly toward a formulation change or ranking-style workflow, not a standard binary feature round.
