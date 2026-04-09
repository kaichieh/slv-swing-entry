# Multi-Asset Repo

Per-asset backlogs live under `assets/<asset>/task.md`.

Examples:

- `assets/slv/task.md`
- `assets/qqq/task.md`
- `assets/nvda/task.md`
- `assets/tsla/task.md`

## Monitoring Layer

- [x] Add per-asset active status summaries and dashboards for all non-SLV assets. Performance: each active asset now has `active_status_summary.tsv` and `active_status.html`, so the preferred line and current lane role can be reviewed quickly.
- [x] Add per-asset monitor snapshots for all non-SLV assets. Performance: each active asset now has `monitor_snapshot.tsv`, which reduces the preferred line to a single current action row such as `selected_now`, `watchlist_wait`, `reference_only`, or `research_only`.
- [x] Add a repo-level monitor board for all non-SLV assets. Performance: `monitor_board.tsv` and `monitor_board.html` now summarize the current cross-asset stance in one place. In the current snapshot, `IWM` is `selected_now`, `XLE` and `NVDA` are `watchlist_wait`, `QQQ` and `TSLA` are `inactive_wait`, `SPY` is `reference_only`, and `TLT` is `research_only`.
- [x] Upgrade the repo-level monitor board into the main dashboard page. Performance: `monitor_board.html` now uses a `gold`-style layout with spotlight cards on top and a colored overview chart below, so it can act as the single primary HTML entry point instead of forcing day-to-day review through multiple pages.
- [x] Add a repo-level monitor priority view for all non-SLV assets. Performance: `monitor_priority.tsv` and `monitor_priority.html` now sort the same board into daily review order with a suggested next step per asset. The current priority stack is `IWM` first, then `NVDA` and `XLE`, then `QQQ` and `TSLA`, with `SPY` and `TLT` kept only for context or research.
- [x] Add a repo-level focus shortlist for all non-SLV assets. Performance: `monitor_focus.tsv` and `monitor_focus.html` now filter the priority stack down to the daily review shortlist only. In the current snapshot, the focus set is `IWM`, `NVDA`, and `XLE`.

## Cross-Asset Priority

- [x] Record the current first-round priority shortlist from the 20-asset batch. Performance: the current official top-three follow-up assets are `XLP`, `VT`, and `IJH`.
- [x] Save the selection rationale for the current shortlist. Performance: `XLP` is the cleanest classifier candidate so far with `test_bal_acc=0.6731` on `ret_60 + sma_gap_60 + above_200dma_flag`; `VT` is the most conservative high-balance line with `test_bal_acc=0.6337` and `test_positive_rate=0.1182`; `IJH` remains the strongest operator-style candidate with `combo_neg115_top_15pct avg_return=5.00%`, `hit_rate=81.48%`, and `trade_count=27`.
- [x] Record the current second-round priority shortlist from the thematic and macro batch. Performance: the current official top-five follow-up assets from the second 20-asset batch are `FXB`, `FXE`, `GLD`, `KRE`, and `SMH`.
- [x] Save the selection rationale for the second-round shortlist. Performance: `FXB` is the cleanest second-round classifier line with `test_bal_acc=0.6803` and `test_positive_rate=0.3606`; `FXE` is the next-best balanced macro line at `test_bal_acc=0.5777`; `GLD` remains attractive as a high-f1 macro benchmark with `test_f1=0.8193` and `test_bal_acc=0.5763`; `KRE` is the best surviving thematic risk line above `0.51` balance; `SMH` still looks worth a heavier follow-up despite a weaker `test_bal_acc=0.4954` because the baseline `test_f1=0.6349` and `11.70%` average return suggest there may be a cleaner filtered rule underneath.
- [x] Save the second-round heavy-batch ranking after safe parallel runs. Performance: `GLD` now leads the second-round heavy batch on the headline model score at `0.6810` with `ret_60_plus_sma_gap_60_interaction`, `test_bal_acc=0.6159`, and a usable forward rule `combo_neg115_top_20pct avg_return=3.99%` over `31` trades.
- [x] Record the standout heavy-batch classifier from the second round. Performance: `FXB` remains the cleanest low-frequency classifier with `sma_gap_120`, `test_bal_acc=0.8260`, and `test_positive_rate=0.1306`, though its current best forward rule is only `3` trades so it still needs more robustness checks.
- [x] Record the second-round heavy-batch caveats. Performance: `FXE` kept decent classifier balance at `test_bal_acc=0.6586` but its best forward rule is currently negative, `SMH` found a stronger filtered rule with `combo_fixed_0_49 avg_return=7.23%` across `29` trades despite weak classifier balance, and `KRE` stayed usable but secondary with `combo_top_20pct avg_return=2.45%` over `29` trades.
- [x] Publish the current global heavy-batch leaderboard across both rounds. Performance: the current top five by headline model score are `GLD`, `FXB`, `XLP`, `FXE`, and `IJH`, while the strongest rule-first alternates are `SMH`, `IJH`, `FXB`, `VT`, and `GLD`.
- [x] Save the current global follow-up interpretation. Performance: `GLD` is the most balanced all-around macro candidate, `FXB` is the cleanest sparse classifier but still under-sampled in forward rules, `XLP` is still the cleanest practical first-round classifier, `IJH` remains one of the best operator-style assets with `5.00%` average forward return over `27` trades, and `SMH` is now the most interesting upside rule-follow-up because its filtered entry line reached `7.23%` average forward return over `29` trades even though the raw classifier stayed weak.
