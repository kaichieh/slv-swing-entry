# NVDA Backlog

## Round 1 Baseline

- [x] Run `AR_ASSET=nvda python prepare.py` and confirm dataset shape. Performance: `rows=6391`, `train/validation/test=4473/958/960`, `positive_rate=0.4360`, `date_range=2000-01-20 -> 2026-03-25`, label config `60d +12%/-6% drop-neutral`.
- [x] Run `AR_ASSET=nvda python train.py` and capture baseline metrics. Performance: `validation_f1=0.6607`, `validation_bal_acc=0.5353`, `test_f1=0.6347`, `test_bal_acc=0.5121`, `threshold=0.402`, `headline_score=0.5932`, `promotion_gate=fail`.
- [x] Run `AR_ASSET=nvda python predict_latest.py` for the baseline live snapshot. Performance: `latest_date=2026-03-27`, `signal=weak_bullish`, `predicted_probability=0.4310`, `decision_threshold=0.4020`, `top_20pct_reference=false`.
- [x] Run `AR_ASSET=nvda python chart_signals.py` and confirm chart output. Performance: `bars_rendered=1260`, `latest_date=2026-03-27`, `output=.cache/nvda-swing-entry/signal_chart.html`.
- [x] Write the baseline result into `assets/nvda/results.tsv`. Performance: baseline row recorded.

## Round 2 Label Sanity

- [x] Compare `drop-neutral` with `keep-all binary`. Performance: `keep-all binary` landed at `validation_f1=0.6578`, `validation_bal_acc=0.5172`, `test_f1=0.6280`, `test_bal_acc=0.5156`, `headline_score=0.5892`, so it did not beat the default baseline.
- [x] Compare `60d +12%/-6%`, `60d +10%/-5%`, and `60d +15%/-8%`. Performance: `60d +10%/-5%` collapsed into near-all-positive predictions with `test_positive_rate=1.0000` and `test_bal_acc=0.5000`; `60d +15%/-8%` was the best label sweep result with `validation_f1=0.7030`, `validation_bal_acc=0.5542`, `test_f1=0.6496`, `test_bal_acc=0.5217`, `headline_score=0.6124`.
- [x] Compare `40d +12%/-6%` versus `60d +12%/-6%`. Performance: `40d +12%/-6%` reached `validation_f1=0.6515`, `validation_bal_acc=0.5349`, `test_f1=0.6293`, `test_bal_acc=0.5048`, which was weaker than the default 60-day horizon.
- [x] Review label balance and regime drift across the sweep. Performance: the main failure mode was not low `f1`; it was overly high predicted positive rate. The cleanest label so far is still `60d +15%/-8%`, but even that stays below the promotion gate on `test_bal_acc`.

## Round 3 Feature Sweep On `60d +15%/-8%`

- [x] Test `ret_60`. Performance: `validation_f1=0.7034`, `validation_bal_acc=0.5527`, `test_f1=0.6480`, `test_bal_acc=0.5195`, `headline_score=0.6114`; essentially flat versus the `15/-8` baseline.
- [x] Test `sma_gap_60`. Performance: `validation_f1=0.7027`, `validation_bal_acc=0.5489`, `test_f1=0.6486`, `test_bal_acc=0.5185`, `headline_score=0.6107`; no real lift.
- [x] Test `rolling_vol_60`. Performance: after wiring `rolling_vol_60` into the standard prepare/train path, it reached `validation_f1=0.7010`, `validation_bal_acc=0.5522`, `test_f1=0.6484`, `test_bal_acc=0.5246`, `headline_score=0.6122`; this was clean and non-degenerate, but still weaker than `atr_pct_20`.
- [x] Test `atr_pct_20`. Performance: `validation_f1=0.7056`, `validation_bal_acc=0.5724`, `test_f1=0.6455`, `test_bal_acc=0.5264`, `headline_score=0.6145`; best single add-on so far by balance and headline score.
- [x] Test `distance_to_252_high`. Performance: `validation_f1=0.7013`, `validation_bal_acc=0.5494`, `test_f1=0.6485`, `test_bal_acc=0.5206`, `headline_score=0.6111`; weaker than `atr_pct_20`.
- [x] Test `close_location_20` and `up_day_ratio_20`. Performance: `close_location_20` reached `headline_score=0.6114`; `up_day_ratio_20` reached `headline_score=0.6085`; both trailed `atr_pct_20`.

## Round 4 Combo And Rule

- [x] Compare `ret_60 + sma_gap_60` against single-feature candidates. Performance: `validation_f1=0.7029`, `validation_bal_acc=0.5529`, `test_f1=0.6475`, `test_bal_acc=0.5184`, `headline_score=0.6110`; still weaker than `atr_pct_20`.
- [x] Compare `ret_60 + sma_gap_60 + atr_pct_20` against simpler candidates. Performance: `validation_f1=0.7081`, `validation_bal_acc=0.5810`, `test_f1=0.6478`, `test_bal_acc=0.5378`, `headline_score=0.6202`; this is the strongest NVDA candidate from this round.
- [x] Test `neg_weight=1.10/1.15/1.20/1.30` on `atr_pct_20`. Performance: the scan stayed tightly clustered; best was `neg_weight=1.30` with `validation_f1=0.7061`, `validation_bal_acc=0.5722`, `test_f1=0.6471`, `test_bal_acc=0.5276`, `headline_score=0.6156`, still behind the 3-feature combo.
- [x] Run a first threshold versus top-percentile rule comparison. Performance: `research_batch.py` showed stronger forward returns for top-percentile rules such as `top_17.5pct avg_return=15.57%` and `top_20pct avg_return=16.05%`, but the combo model inside that batch collapsed toward near-all-positive predictions, so this rule work is directional only and not yet ready to adopt.
- [x] Run a first walk-forward check. Performance: the same `research_batch.py` pass produced combo walk-forward folds around `test_bal_acc=0.4997/0.5000/0.5000`, which confirms the current rule pipeline is still unstable for NVDA and needs a cleaner follow-up pass.

## Round 5 Live And Review

- [x] Run live prediction for the best current candidate `60d +15%/-8% + ret_60+sma_gap_60+atr_pct_20`. Performance: `latest_date=2026-03-17`, `signal=weak_bullish`, `predicted_probability=0.4926`, `decision_threshold=0.4660`, `top_20pct_reference=false`, `buy_point_ok=true`.
- [x] Regenerate the candidate chart after fixing the live feature path. Performance: `predict_latest.py` and `chart_signals.py` now use `add_features()` instead of only `add_price_features()`, so live candidates that depend on `atr_pct_20` and other context features no longer break.
- [x] Decide whether to adopt `60d +15%/-8% + ret_60+sma_gap_60+atr_pct_20` as the active NVDA default. Performance: a dedicated candidate compare was saved to `assets/nvda/candidate_validation_summary.tsv`, `assets/nvda/candidate_forward_summary.tsv`, and `assets/nvda/candidate_walkforward_summary.tsv`. The 3-feature combo remained the best full-sample line at `headline_score=0.6202`, ahead of `atr_pct_20` at `0.6145` and `rolling_vol_60` at `0.6121`, but the dedicated walk-forward check still failed to support adoption. All three candidates collapsed in folds 1 and 3 to `test_bal_acc=0.5000` or worse with `test_positive_rate` near `1.0`, and even the winning combo only reached `test_bal_acc=0.5056` in fold 2. Forward rules also stayed weaker than the plain threshold rule. The correct decision is to keep the combo as the best NVDA candidate, but not adopt it as the active default.
- [x] If NVDA stays research-only, compare tighter percentile rules to see whether a watchlist overlay is still worth keeping. Performance: `assets/nvda/operator_rule_summary.tsv` extended the rule compare to `top 10%` and `top 12.5%`. Threshold still had the best broad trade profile with `trade_count=54`, `hit_rate=75.93%`, `avg_return=14.53%`, but the best high-conviction compromise was `top_12_5pct`, which kept `hit_rate=75.00%`, improved compound drawdown to `-7.17%`, and only trimmed average return to `14.04%`. That is not enough to change the adoption decision, but it is the cleanest watchlist-style overlay if NVDA remains a candidate-only line.

## Next Round

- [x] Run a clean dedicated `rolling_vol_60` pass for NVDA. Performance: the dedicated train path confirmed `rolling_vol_60` is viable but not best-in-class, and `ret_60 + sma_gap_60 + rolling_vol_60` only reached `validation_f1=0.7009`, `validation_bal_acc=0.5509`, `test_f1=0.6463`, `test_bal_acc=0.5204`, `headline_score=0.6099`.
- [x] Re-run threshold versus `top 15% / 17.5% / 20%` on the winning 3-feature combo with a non-degenerate scoring path. Performance: the clean rerun on `ret_60 + sma_gap_60 + atr_pct_20` showed threshold still leading in forward results with `trade_count=54`, `hit_rate=0.7593`, `avg_return=14.53%`; `top_15pct` reached `trade_count=41`, `avg_return=13.03%`, `top_17.5pct` reached `trade_count=43`, `avg_return=13.10%`, and `top_20pct` reached `trade_count=43`, `avg_return=13.40%`. The percentile rules did improve precision into the `0.58-0.60` range, but they did not improve the overall case enough to promote the model.
- [x] If NVDA still behaves like a trend continuation model, add `above_200dma_flag` or a relative-strength feature versus `QQQ`. Performance: `above_200dma_flag` alone only reached `validation_f1=0.6612`, `validation_bal_acc=0.5344`, `test_f1=0.6333`, `test_bal_acc=0.5092`, `headline_score=0.5898`, and adding it to the winning combo landed at `validation_f1=0.6582`, `validation_bal_acc=0.5350`, `test_f1=0.6387`, `test_bal_acc=0.5235`, `headline_score=0.5978`, which was clearly worse. A new `QQQ` relative-strength feature `rs_vs_benchmark_60` was then added via `benchmark_symbol=QQQ`; it was clean but still weaker than the current winner both alone (`headline_score=0.6098`) and on top of the winner (`validation_f1=0.7076`, `validation_bal_acc=0.5799`, `test_f1=0.6452`, `test_bal_acc=0.5325`, `headline_score=0.6173`).

## Notes

- NVDA still has a credible candidate, but the adoption question is now effectively closed for this round: the combo is worth keeping, not promoting.
- If NVDA research continues later, the next step should be a formulation change or a much stricter operating rule, not another nearby feature sweep.
- If a live watchlist overlay is needed before a formulation change, use the current combo with `top_12_5pct` rather than the broader threshold rule.
