# GLD Program

This asset is part of the cross-asset batch universe under the `Macro ETFs` bucket.

## Current Research Direction

- baseline reference: `60d +8%/-4% drop-neutral`
- official live default: `future-return-top-bottom-10pct` with `hard_gate_two_expert_mixed`
- the current optimized live path mixes `dual_context` and `context_no_atr` using `atr_pct_20_percentile >= 0.70`
- VIX is now available in the GLD winner path as an opt-in research source through selected `vix_*` extras, but the tested GLD regime variant remains below the optimized non-VIX baseline and is not the live default
- the current runtime line is `gld_current_live_mixed_live`, which keeps the same mixed core and uses the pure `threshold_plus_buy_point_overlay` decision rule without the VIX/VIX3M term-panic block
- the prior overlay line `gld_mixed_vix_vxv_term_panic_live` remains tracked in `assets/gld/vix_runtime_replacement_decision.json` as a historical runtime/operator variant
- additional attempts to push VIX/VIX3M term features into the core mixed model underperformed the existing non-VIX frontier, so no VIX-driven core replacement became the long-run GLD default
- final frontier comparison against the stronger row121 / row122 GLD candidates still leaves the preserved mixed baseline frontier above the tested GLD+VIX runtime alternatives
- Monitor Board now reads the production GLD state from this baseline live path through `predict_latest.py -> refresh_active_status.py -> refresh_monitor_snapshot.py -> refresh_monitor_board.py`
- older rolling-vol and context-stack operator files remain historical comparison material, not the current live default

## Working Style

1. Keep the active research backlog in `task.md`.
2. Save every completed run in `results.tsv`.
3. Keep future follow-up ideas in `ideas.md` until they become concrete backlog items.
