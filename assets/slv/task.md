# SLV Backlog

## Round 1 Baseline

- [x] Run `AR_ASSET=slv python prepare.py` and confirm dataset shape. Performance: `rows=4665`, `train/validation/test=3265/699/701`, `positive_rate=0.3810`, `date_range=2007-04-30 -> 2026-03-25`, label config `60d +8%/-4% drop-neutral`.
- [x] Run `AR_ASSET=slv python train.py` and capture baseline metrics. Performance: `validation_f1=0.4591`, `validation_bal_acc=0.5364`, `test_f1=0.6439`, `test_bal_acc=0.4715`, `threshold=0.387`, `headline_score=0.5445`, `promotion_gate=fail`.
- [x] Run `AR_ASSET=slv python predict_latest.py` for the baseline live snapshot. Performance: `latest_date=2026-03-27`, `signal=bullish`, `predicted_probability=0.4574`, `decision_threshold=0.3870`, `top_20pct_reference=true`.
- [x] Run `AR_ASSET=slv python chart_signals.py` and confirm chart output. Performance: `bars_rendered=1260`, `latest_date=2026-03-27`, `output=.cache/slv-swing-entry/signal_chart.html`.
- [x] Write the baseline row into `assets/slv/results.tsv`. Performance: baseline row recorded.

## Round 2 Feature Sweep On `60d +8%/-4%`

- [x] Test `ret_60`. Performance: `validation_f1=0.4642`, `validation_bal_acc=0.5428`, `test_f1=0.6470`, `test_bal_acc=0.4841`, `headline_score=0.5512`; this was the cleanest single-feature follow-up.
- [x] Test `sma_gap_60`. Performance: `validation_f1=0.4596`, `validation_bal_acc=0.5374`, `test_f1=0.6438`, `test_bal_acc=0.4749`, `headline_score=0.5456`; weaker than `ret_60`.
- [x] Test `ret_60 + sma_gap_60`. Performance: `validation_f1=0.4636`, `validation_bal_acc=0.5418`, `test_f1=0.6470`, `test_bal_acc=0.4841`, `headline_score=0.5509`; matched `ret_60` on test but did not improve the main balance problem.
- [x] Test `neg_weight=1.15` on `ret_60 + sma_gap_60`. Performance: `validation_f1=0.4613`, `validation_bal_acc=0.5378`, `test_f1=0.6497`, `test_bal_acc=0.4868`, `headline_score=0.5520`; slightly better but still below promotion quality.
- [x] Test `ret_60 + sma_gap_60 + rolling_vol_60`. Performance: `validation_f1=0.4577`, `validation_bal_acc=0.5276`, `test_f1=0.6628`, `test_bal_acc=0.4771`, `headline_score=0.5525`; best test `f1`, but too unstable and too imbalanced.
- [x] Run walk-forward and forward-rule review on `ret_60 + sma_gap_60`. Performance: 4-fold walk-forward test balance stayed weak at roughly `0.5000 / 0.4919 / 0.4961`, and forward rules were not attractive enough to rescue the line.

## Round 3 Extended Sweep

- [x] Test `distance_to_252_high`. Performance: `headline_score=0.5439`; no improvement versus the better Round 2 candidates.
- [x] Test `atr_pct_20`. Performance: `validation_f1=0.4615`, `validation_bal_acc=0.5372`, `test_f1=0.6588`, `test_bal_acc=0.4797`, `headline_score=0.5534`; strongest low-risk single add-on by headline score, but still below the needed balance.
- [x] Test `sma_gap_120`. Performance: `validation_bal_acc=0.5526`, `test_bal_acc=0.4807`, `headline_score=0.5489`; validation looked cleaner than test.
- [x] Run a nearby label sweep. Performance: `60d +12%/-6% + ret_60` became the strongest nearby label candidate with `validation_f1=0.4835`, `validation_bal_acc=0.5234`, `test_f1=0.6946`, `test_bal_acc=0.5094`, `headline_score=0.5797`, but it still failed the promotion gate.
- [x] Run `AR_ASSET=slv python research_exit_round1.py`. Performance: the best exit variant `exit_ret_60_plus_sma_gap_60` reached `validation_f1=0.5900`, `validation_bal_acc=0.5828`, `test_f1=0.3429`, `test_bal_acc=0.5101`, `headline_score=0.4665`; it remained much weaker than the entry line on test quality.

## Next Round

- [x] Run clean baselines for `60d +10%/-5%` and `60d +6%/-3%`, then compare them directly against the current `60d +12%/-6%` nearby-label candidate. Performance: `60d +10%/-5%` baseline reached `validation_f1=0.4757`, `validation_bal_acc=0.5040`, `test_f1=0.7037`, `test_bal_acc=0.4985`, `headline_score=0.5455`, which was too collapsed to matter. Adding `ret_60` made it cleaner at `validation_f1=0.4911`, `validation_bal_acc=0.5373`, `test_f1=0.6917`, `test_bal_acc=0.5316`, `headline_score=0.5629`, but it still trailed the current `60d +12%/-6% + ret_60` candidate on headline quality. `60d +6%/-3%` was weaker in both baseline and `ret_60` form, topping out at `headline_score=0.5355` baseline and `0.5291` with `ret_60`.
- [x] Because the tighter and mid-width barrier checks both failed to replace the current nearby-label winner, re-run walk-forward and forward-rule validation on the strongest remaining candidates such as `60d +12%/-6% + ret_60`, `atr_pct_20`, and `ret_60 + sma_gap_60 + rolling_vol_60`. Performance: the dedicated `12/-6` validation confirmed that `ret_60` remains the best nearby-label line. It led on headline score at `0.5797` with `validation_f1=0.4835`, `validation_bal_acc=0.5234`, `test_f1=0.6946`, `test_bal_acc=0.5094`, while `atr_pct_20` was slightly lower at `headline_score=0.5789` and far more degenerate with `test_positive_rate=0.9969`. The 3-feature combo `ret_60 + sma_gap_60 + rolling_vol_60` dropped to `headline_score=0.5684` and `test_bal_acc=0.4861`. Rule comparison also favored the simpler `ret_60` line: `top_20pct` gave the strongest single-split trade profile with `hit_rate=77.78%`, `avg_return=15.33%`, and only `-6.01%` compound drawdown. In 4-fold forward trades, `ret_60 top_15pct` was the cleanest compromise with `trade_count=28`, `hit_rate=53.57%`, `avg_return=6.75%`, ahead of the `atr_pct_20` percentile rules. Walk-forward remained weak across all three candidates, with test balanced accuracy staying below `0.50` to `0.49` in most folds, so none of them are ready for promotion.
- [x] Decide whether SLV is still best treated as a research-only line or whether a narrower operating rule can make it useful despite the weak balanced-accuracy profile. Performance: keep SLV as research-only for now. The best nearby-label candidate remains `60d +12%/-6% + ret_60`, and `top 15% / top 20%` overlays are useful as optional context, but the walk-forward balance never cleaned up enough to justify promoting SLV into the same day-to-day watchlist tier as IWM, GLD, or the binary NVDA lane.

## Notes

- The main SLV blocker is not lack of candidate ideas; it is weak out-of-sample balanced accuracy.
- The unfinished nearby-label sweep is now effectively closed: `60d +12%/-6% + ret_60` remains the best nearby label path, while `60d +10%/-5% + ret_60` is the best of the tighter checks but still not strong enough to replace it.
- Dedicated `12/-6` validation also closed the remaining feature question for that label: keep `ret_60` as the reference candidate, treat `atr_pct_20` and `ret_60 + sma_gap_60 + rolling_vol_60` as weaker side paths, and only keep `top_15pct` or `top_20pct` rules as optional operating overlays if SLV stays research-only.
- `predict_latest.py` was intentionally kept on a baseline-oriented live path for SLV so the chart and signal review would stay stable while research was still unsettled.
