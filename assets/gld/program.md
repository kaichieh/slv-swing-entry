# GLD Program

This asset is part of the cross-asset batch universe under the `Macro ETFs` bucket.

## Current Research Direction

- baseline reference: `60d +8%/-4% drop-neutral`
- official live default: `future-return-top-bottom-10pct` with `hard_gate_two_expert_mixed`
- the live path mixes `dual_context` and `context_no_atr` using `atr_pct_20_percentile >= 0.75`
- Monitor Board now reads the production GLD state from this live path through `predict_latest.py -> refresh_active_status.py -> refresh_monitor_snapshot.py -> refresh_monitor_board.py`
- older rolling-vol and context-stack operator files remain historical comparison material, not the current live default

## Working Style

1. Keep the active research backlog in `task.md`.
2. Save every completed run in `results.tsv`.
3. Keep future follow-up ideas in `ideas.md` until they become concrete backlog items.
