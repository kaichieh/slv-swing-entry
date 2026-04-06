# IWM Backlog

## Round 1 Baseline

- [x] Run `AR_ASSET=iwm python prepare.py` and confirm dataset shape. Performance: `rows=4769`, `train/validation/test=3338/715/716`, `positive_rate=0.3330`, `date_range=2001-05-25 -> 2026-03-10`, label config `60d +10%/-5% drop-neutral`.
- [x] Run `AR_ASSET=iwm python train.py` and capture baseline metrics for `60d +10%/-5% drop-neutral`. Performance: `validation_f1=0.5501`, `validation_bal_acc=0.6058`, `test_f1=0.5804`, `test_bal_acc=0.5560`, `threshold=0.450`, `headline_score=0.5730`, `promotion_gate=pass`, `test_positive_rate=0.7374`.
- [x] Run `AR_ASSET=iwm python predict_latest.py` for the baseline live snapshot. Performance: `latest_date=2026-03-10`, `signal=weak_bullish`, `predicted_probability=0.4731`, `decision_threshold=0.4500`, `top_20pct_reference=false`.
- [x] Run `AR_ASSET=iwm python chart_signals.py` and confirm chart output. Performance: `bars_rendered=1260`, `latest_date=2026-03-10`, `output=.cache/iwm-swing-entry/signal_chart.html`.
- [x] Write the baseline row into `assets/iwm/results.tsv`. Performance: baseline row recorded.

## Round 2 Label Sanity

- [x] Compare `drop-neutral` versus `keep-all binary`. Performance: `keep-all binary` reached `validation_f1=0.4545`, `validation_bal_acc=0.6287`, `test_f1=0.5103`, `test_bal_acc=0.5364`, `headline_score=0.5325`. It reduced the need for neutral dropping on paper, but it still trailed the default `drop-neutral` baseline by a wide margin on headline quality and did not change the practical IWM conclusion.
- [x] Compare `60d +10%/-5%`, `60d +12%/-6%`, and `60d +8%/-4%`. Performance: neither alternative beat the default baseline. `60d +8%/-4%` reached `test_bal_acc=0.5605` but only `headline_score=0.5482`, while `60d +12%/-6%` reached `test_bal_acc=0.5633` but `headline_score=0.5429`. The default `60d +10%/-5%` line remained strongest at `headline_score=0.5730`.
- [x] Compare `40d +10%/-5%` versus `60d +10%/-5%`. Performance: `40d +10%/-5%` weakened too much on test quality with `test_f1=0.4028`, `test_bal_acc=0.5316`, `headline_score=0.4917`.
- [x] Review whether IWM is cleaner than SPY or simply a noisier broad-beta line. Performance: IWM is clearly cleaner than SPY on the current workflow. It already passed the gate on the baseline and the nearby label sweep did not reveal a better replacement, which means the baseline itself is a credible reference line rather than a degenerate market-beta model.

## Round 3 Feature Sweep

- [x] Test `ret_60`, `sma_gap_60`, `rolling_vol_60`, `atr_pct_20`, `distance_to_252_high`, and `rs_vs_benchmark_60` versus `SPY`. Performance: the strongest add-on was `rs_vs_benchmark_60`, reaching `validation_f1=0.5270`, `validation_bal_acc=0.5753`, `test_f1=0.5924`, `test_bal_acc=0.5643`, `headline_score=0.5692`. `distance_to_252_high` and `ret_60 + sma_gap_60` were close behind at `0.5655` and `0.5647`, and `rolling_vol_60` was the cleanest validation-side add-on at `validation_bal_acc=0.6256`. But the key conclusion is that the baseline itself still remained strongest at `headline_score=0.5730`, so the feature sweep did not dislodge it.

## Round 4 Validation

- [x] Compare threshold versus top-percentile operating rules on the default baseline and the `rs_vs_benchmark_60` side candidate. Performance: threshold remained the only broadly usable operator for both lines, with `avg_return=3.70%` on the baseline and `3.61%` on the relative-strength candidate. The best percentile overlay was `top_20pct`, which reached `avg_return=4.63%`, but it only produced `10` non-overlapping trades and did not clearly improve the operating case.
- [x] Add 4-fold walk-forward validation on the baseline and the `rs_vs_benchmark_60` side candidate. Performance: the first two folds still collapsed toward always-long behavior for both lines, but fold 3 was informative. The relative-strength side candidate reached `test_f1=0.6160`, `test_bal_acc=0.5813`, and `test_positive_rate=0.7872`, ahead of the baseline at `0.4591 / 0.5251 / 0.4383`. That keeps the baseline as the active IWM default, while `rs_vs_benchmark_60` becomes the only sidecar still worth keeping.

## Round 5 Recent Operator Output

- [x] Save live-like recent operator outputs for the active IWM threshold line and the `rs_vs_benchmark_60` sidecar. Performance: `assets/iwm/operator_recent.tsv` showed that the relative-strength sidecar was actually the more active line into the latest dates. By `2026-03-10`, `rs_vs_benchmark_60` was still selected with `predicted_probability=0.4601` versus `threshold=0.4360`, while the baseline was quieter. This does not change the adoption decision, but it makes the sidecar useful as a tactical overlay when IWM is outperforming SPY.

## Round 6 Operating Compare

- [x] Compare the baseline threshold line against a stricter relative-strength overlay under walk-forward trading. Performance: `assets/iwm/operator_walkforward_compare.tsv` showed that the default baseline threshold still wins on robustness. It reached `trade_count=41`, `hit_rate=53.66%`, `avg_return=2.19%`, and kept fold excess returns in a narrow `-0.23%` to `+0.60%` band. The `rs_vs_benchmark_60 + top_20pct` overlay was more selective, but weaker overall with `trade_count=30`, `hit_rate=46.67%`, `avg_return=1.81%`, and a much worse worst-fold excess at `-2.25%`. So the sidecar remains tactical only; it should not replace the baseline operating line.

## Round 7 Decision Summary

- [x] Save a direct operating decision summary for the baseline and sidecar IWM lines. Performance: `assets/iwm/operator_decision_summary.tsv` showed that both lines were still active into the latest row `2026-03-10`, but the baseline remains the cleaner default. Over the last `60` saved rows, the baseline threshold selected `45` times and the sidecar threshold selected `44` times, with both still selected on the latest date. This means the practical difference is not signal frequency but interpretation: the sidecar should be treated as context for IWM-vs-SPY strength, not as a replacement operating line.

## Round 8 Overlap Review

- [x] Measure how often the baseline and IWM sidecar actually disagree. Performance: `assets/iwm/operator_overlap_summary.tsv` and `assets/iwm/operator_overlap_recent.tsv` showed the two lines are almost identical in practice. In the latest `60` rows they agreed on `59` out of `60` dates, with `44` rows selected by both, `15` selected by neither, and only `1` row selected by the baseline alone. There were `0` rows where the sidecar fired without the baseline. That means the sidecar is useful as explanatory context, but it is not generating a distinct operating stream.

## Round 9 Usage Summary

- [x] Save a compact usage summary for the surviving IWM operator lines. Performance: `assets/iwm/operator_usage_summary.tsv` confirmed that the baseline threshold and sidecar threshold are both currently active, with `45` and `44` selections in the latest `60` rows and both still selected on `2026-03-10`. This makes the practical guidance very simple: use the baseline as the default line, and read the sidecar as confirmation rather than as a second signal stream.

## Round 10 Active Status Summary

- [x] Save a one-file active status summary for the current IWM operating lines. Performance: `assets/iwm/active_status_summary.tsv` now packages the current usage decision into one table. The baseline threshold remains the preferred line with `recent_selected_count=45` and latest selected on `2026-03-10`, while the `rs_vs_benchmark_60` sidecar is also active at `44` selections but is explicitly marked as confirmation-only. This closes the practical next step for IWM: there is no reason to treat the sidecar as a separate watchlist stream.

## Round 11 Active Status HTML

- [x] Render a lightweight HTML status page for the current IWM operating lines. Performance: `assets/iwm/active_status.html` now mirrors the active summary in a human-readable view. The page makes the baseline-versus-sidecar split obvious: the baseline is still the preferred line, while the relative-strength sidecar is only a confirmation layer.

## Round 12 Monitor Snapshot

- [x] Save a preferred-line monitor snapshot for day-to-day use. Performance: `assets/iwm/monitor_snapshot.tsv` now compresses the current IWM stance into a single row. The preferred line remains `baseline_threshold`, the latest row on `2026-03-10` is still selected, and the asset action is therefore `selected_now`. This is the clearest sign in the non-SLV set that is still live-like right now.

## Round 13 Indicator Expansion

- [x] Test a broader indicator stack built around relative strength, trend quality, compression, and recovery features. Performance: the best stack so far used `ret_20_vs_benchmark`, `price_ratio_benchmark_z_20`, `trend_quality_20`, `percent_up_days_20`, `bollinger_bandwidth_20`, `distance_from_60d_low`, and `atr_pct_20_percentile`. It reached `validation_f1=0.5475`, `validation_bal_acc=0.6149`, `test_f1=0.5726`, `test_bal_acc=0.5865`, and `headline_score=0.5804`, which is the first feature expansion to beat the validated baseline headline score `0.5730`. The result is not yet validated, but it is the clearest sign so far that IWM can improve through a structured feature stack rather than a single sidecar add-on.

## Round 14 Candidate Validation

- [x] Validate the new IWM indicator stack with rule comparison and 4-fold walk-forward checks before replacing the baseline. Performance: the stack kept a usable threshold rule with `trade_count=41`, `hit_rate=63.41%`, and `avg_return=1.82%`, while the percentile rules were less convincing. But the walk-forward test still broke too hard in the early folds, with `test_bal_acc=0.4491 / 0.5009 / 0.5393` and `test_positive_rate=0.9217 / 0.9987 / 0.4432`. So the stack is a genuine static-split breakthrough, but not yet a validated replacement for the existing IWM baseline.

## Round 15 Rule Stabilization Check

- [x] Scan tighter fixed thresholds and percentile rules on the new IWM context stack before giving up on it. Performance: no operating rule rescued the stability problem. `fixed_0.49` was the cleanest selective rule with `selected_count=7`, `hit_rate=71.43%`, `avg_return=3.80%`, and `forward_avg_return=2.96%`, while `fixed_0.50` was too sparse at only `10` forward trades. Percentile rules such as `top_10pct` and `top_12_5pct` looked decent on the static test split, but they still failed to beat the threshold line cleanly on forward trading. This means the current IWM context stack still lacks a convincing operating-layer breakthrough even though the raw model score improved.

## Round 16 Anti-Overprediction Controls

- [x] Add explicit threshold controls for overprediction and test them on the IWM context stack. Performance: the repo now supports a `max_positive_rate` cap and a target positive-rate penalty during threshold selection, with regression tests covering both behaviors. On IWM, though, the controls did not produce a real breakthrough. The cleanest threshold-policy variant was only `target_0.60_penalty_0.5`, which kept static split quality respectable at `validation_f1=0.5467`, `validation_bal_acc=0.6179`, `test_f1=0.5489`, and `test_bal_acc=0.5726`, but walk-forward still broke in fold 1 and fold 2 at `test_bal_acc=0.3631 / 0.5000`. Adding `neg_weight` on top did not fix the issue either: even `neg_weight=1.15` plus caps still left fold 2 near all-long behavior.

## Round 17 Structural Gating Check

- [x] Test simple regime and selectivity gates on top of the IWM context-stack score instead of changing the base model again. Performance: no gate combo became a true replacement line, but the exercise did produce one useful clue. `fixed_0.49 + above_200dma + ret_20_vs_benchmark > 0` was the least unstable walk-forward variant, with fold balanced accuracy at `0.5025 / 0.5522 / 0.4978` and only `8` total non-overlapping trades. That is too sparse and still too weak in the third fold to count as a breakthrough, but it does suggest the next IWM path is a second-stage selective operator gated by market regime and relative strength rather than more threshold tuning on the raw model.

## Round 18 Second-Stage Operator Refinement

- [x] Refine the structural gating idea into a simpler second-stage operator and compare it against the more restrictive regime gate. Performance: the cleaner variant turned out to be `fixed_0.49 + ret_20_vs_benchmark > 0` without the extra `above_200dma` filter. It kept all three walk-forward folds close to neutral-or-better on balanced accuracy at `0.5025 / 0.5931 / 0.4994`, improved average fold return to roughly `5.80%`, and raised total non-overlapping trades to `12`. That is still too sparse to replace the validated IWM baseline, and the static split remained weak at only `4` test trades with `bal_acc=0.4948`, but it is a cleaner selective side candidate than the previous `above_200dma + rs` version.

## Round 19 Live-Like Sidecar Check

- [x] Compare the new `fixed_0.49 + ret_20_vs_benchmark > 0` side operator directly against the validated baseline over recent live-like rows. Performance: the result was decisive. `assets/iwm/operator_side_compare_summary.tsv` and `assets/iwm/operator_recent_side_compare.tsv` showed that over the latest `60` saved rows through `2026-03-25`, the baseline still selected `41` times while the new side operator selected `0` times. Across the full saved test window, the side operator only fired on `14` dates, ending on `2025-04-04`. That means the new line is not a practical live sidecar right now; it is better understood as a sparse historical selective-study lane.

## Next Round

- [ ] If IWM work continues, stop trying to operationalize the sparse side operator as a current live lane and instead treat it as a historical regime-study reference.
- [ ] If an operating-layer follow-up is needed, keep `fixed_0.49` plus relative strength only as a template for future two-stage research rather than as an immediate deployment candidate.

## Notes

- IWM is the repo's intended small-cap cycle line, so relative performance versus SPY matters.
- IWM immediately looks like the strongest of the new macro basket, so the next round should focus on validation and simplification rather than rescue work.
- Because the baseline already passed, the next IWM round should move to feature and rule validation rather than more label tuning.
- The earlier single-feature sweep suggested `rs_vs_benchmark_60` was the only IWM add-on clearly worth keeping, but the new multi-feature stack has now overtaken the baseline on headline score and deserves its own validation round.
