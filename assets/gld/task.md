# GLD Research Status

## Current Outcome

- [x] Baseline GLD mixed live path revalidated (`dual_context + context_no_atr`, `atr_pct_20_percentile >= 0.70`).
- [x] Direct daily-VIX feature and gate variants tested and rejected as core live replacements.
- [x] VIX/VIX3M term-structure features added and tested.
- [x] GLD runtime now uses the named line `gld_mixed_vix_vxv_term_panic_live`.
- [x] `predict_latest.py`, `refresh_active_status.py`, `chart_signals.py`, and monitor outputs all resolve to that same line.
- [x] Negative-result evidence for failed VIX core candidates is preserved in tracked repo artifacts.

## Replacement Conclusion

- The previous generic GLD mixed live operator has been replaced at runtime by `gld_mixed_vix_vxv_term_panic_live`.
- This replacement is an **operator-overlay replacement**, not a new VIX core-model family.
- No VIX-driven core GLD replacement candidate survived the final frontier search.

## Tracked Evidence

- `assets/gld/results.tsv`
- `assets/gld/program.md`
- `assets/gld/vix_runtime_replacement_decision.json`
- `assets/gld/vix_core_candidate_screen.json`
- `assets/gld/vix_replacement_frontier_compare.json`
