# GLD Program

This asset is part of the cross-asset batch universe under the `Macro ETFs` bucket.

## Current Research Direction

- baseline reference: `60d +8%/-4% drop-neutral`
- official live default: `future-return-top-bottom-10pct` with `hard_gate_two_expert_mixed`
- the current optimized live path mixes `dual_context` and `context_no_atr` using `atr_pct_20_percentile >= 0.70`
- VIX is now available in the GLD winner path as an opt-in research source through selected `vix_*` extras, but the tested GLD regime variant remains below the optimized non-VIX baseline and is not the live default
- the previous generic GLD mixed live operator has now been replaced at runtime by the named line `gld_mixed_vix_vxv_term_panic_live`, which keeps the same mixed core but replaces the old entry overlay with a VIX/VIX3M term-panic block whenever the 3-day rolling max of `vix_vxv_ratio_pct_63` exceeds `0.90`
- the runtime replacement decision is tracked in `assets/gld/vix_runtime_replacement_decision.json`, which records the explicit replacement bar and the measured operator-level improvement over the prior generic line
- additional attempts to push VIX/VIX3M term features into the core mixed model underperformed the existing non-VIX frontier, so the adopted GLD-with-VIX path is explicitly an operator overlay rather than a model-family replacement
- final frontier comparison against the stronger row121 / row122 GLD candidates still leaves `gld_mixed_vix_vxv_term_panic_live` as the only surviving GLD+VIX runtime line worth keeping
- Monitor Board now reads the production GLD state from this live path through `predict_latest.py -> refresh_active_status.py -> refresh_monitor_snapshot.py -> refresh_monitor_board.py`
- older rolling-vol and context-stack operator files remain historical comparison material, not the current live default

## Working Style

1. Keep the active research backlog in `task.md`.
2. Save every completed run in `results.tsv`.
3. Keep future follow-up ideas in `ideas.md` until they become concrete backlog items.
