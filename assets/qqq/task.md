# QQQ Backlog

## Round 1 Baseline

- [x] Run `AR_ASSET=qqq python prepare.py` and confirm dataset shape. Performance: `rows=5782`, `train/validation/test=4047/867/868`, `positive_rate=0.4060`, `date_range=2000-03-07 -> 2026-03-25`, label config `60d +8%/-4% drop-neutral`.
- [x] Run `AR_ASSET=qqq python train.py` and capture baseline metrics. Performance: `validation_f1=0.6312`, `validation_bal_acc=0.5043`, `test_f1=0.6314`, `test_bal_acc=0.5011`, `threshold=0.497`, `headline_score=0.5796`, `promotion_gate=fail`.
- [x] Run `AR_ASSET=qqq python predict_latest.py` for the baseline live snapshot. Performance: `latest_date=2026-03-25`, `signal=bullish`, `predicted_probability=0.4998`, `decision_threshold=0.4970`, `top_20pct_reference=false`.
- [x] Run `AR_ASSET=qqq python chart_signals.py` and confirm chart output. Performance: `bars_rendered=1260`, `latest_date=2026-03-25`, `output=.cache/qqq-swing-entry/signal_chart.html`.
- [x] Write the baseline row into `assets/qqq/results.tsv`. Performance: baseline row recorded.

## Round 2 Label Sanity

- [x] Compare `drop-neutral` with `keep-all binary`. Performance: `keep-all binary` degraded to `validation_f1=0.5825`, `validation_bal_acc=0.5129`, `test_f1=0.5697`, `test_bal_acc=0.4895`, `headline_score=0.5425`, so the neutral filter still looks preferable.
- [x] Compare `60d +8%/-4%`, `60d +10%/-5%`, and `60d +6%/-3%`. Performance: `60d +10%/-5%` reached `validation_f1=0.6272`, `validation_bal_acc=0.5025`, `test_f1=0.6101`, `test_bal_acc=0.5012`, `headline_score=0.5701`; `60d +6%/-3%` reached `validation_f1=0.6224`, `validation_bal_acc=0.5057`, `test_f1=0.6059`, `test_bal_acc=0.5019`, `headline_score=0.5680`; both trailed the default baseline.
- [x] Compare `40d +8%/-4%` versus `60d +8%/-4%`. Performance: `40d +8%/-4%` gave `validation_f1=0.6191`, `validation_bal_acc=0.5247`, `test_f1=0.5804`, `test_bal_acc=0.4983`, `headline_score=0.5579`, so it did not beat the default 60-day horizon.
- [x] Review the failure mode across the label sweep. Performance: every tested QQQ label stayed near all-positive behavior, with `test_positive_rate` ranging from `0.9569` to `0.9988`, which points to a label separability problem rather than a simple feature gap.

## Round 3 Feature Sweep On `60d +8%/-4%`

- [x] Test `ret_60`. Performance: `validation_f1=0.6317`, `validation_bal_acc=0.5053`, `test_f1=0.6314`, `test_bal_acc=0.5011`, `headline_score=0.5798`; effectively unchanged from baseline.
- [x] Test `sma_gap_60`. Performance: `validation_f1=0.6312`, `validation_bal_acc=0.5043`, `test_f1=0.6314`, `test_bal_acc=0.5011`, `headline_score=0.5796`; no change.
- [x] Test `rolling_vol_60`. Performance: the training path ignored it because `rolling_vol_60` is not wired into the standard train-time experimental feature list, so the result matched baseline exactly; this still needs a dedicated code-path if we want to test it properly.
- [x] Test `atr_pct_20`. Performance: `validation_f1=0.6312`, `validation_bal_acc=0.5043`, `test_f1=0.6314`, `test_bal_acc=0.5011`, `headline_score=0.5796`; no change.
- [x] Test `distance_to_252_high`. Performance: `validation_f1=0.6312`, `validation_bal_acc=0.5043`, `test_f1=0.6314`, `test_bal_acc=0.5011`, `headline_score=0.5796`; no change.
- [x] Test `close_location_20`. Performance: `validation_f1=0.6312`, `validation_bal_acc=0.5043`, `test_f1=0.6314`, `test_bal_acc=0.5011`, `headline_score=0.5796`; no change.
- [x] Test `sma_gap_120`. Performance: the standard train path also ignored it, so the run stayed identical to baseline.

## Round 4 Weighting Check

- [x] Test `neg_weight=1.10/1.20/1.30` on the default baseline. Performance: `neg_weight=1.10` and `1.20` were identical to baseline; `neg_weight=1.30` only nudged `test_positive_rate` down to `0.9977` and slightly hurt the score with `test_f1=0.6303`, `test_bal_acc=0.4998`, `headline_score=0.5790`.
- [x] Summarize the current blocker. Performance: neither label sweeps, feature sweeps, nor modest negative weighting changed the near-all-positive behavior in a meaningful way.

## Next Round

- [ ] Change the QQQ target definition instead of adding more features on the current label. Best candidates are a wider downside barrier, a stricter upside barrier, or a ranking target.
- [ ] If we want to test `rolling_vol_60` or `sma_gap_120` in the standard train path, wire them into the train-time experimental feature flow instead of only the research batch path.
- [ ] Once a non-degenerate candidate appears, re-run threshold versus top-percentile rules and a 4-fold walk-forward check.

## Notes

- QQQ currently looks much more label-limited than feature-limited.
- The next useful step is to redesign the target, not to keep stacking small features onto the current `60d +8%/-4%` label.
