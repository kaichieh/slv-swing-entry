# GLD Research Status

## Current Outcome

- [x] Baseline GLD mixed live path revalidated (`dual_context + context_no_atr`, `atr_pct_20_percentile >= 0.70`).
- [x] Direct daily-VIX feature and gate variants tested and rejected as core live replacements.
- [x] VIX/VIX3M term-structure features added and tested.
- [x] GLD runtime now uses the named baseline line `gld_current_live_mixed_live`.
- [x] `predict_latest.py`, `refresh_active_status.py`, `chart_signals.py`, and monitor outputs all resolve to that same baseline line.
- [x] Negative-result evidence for failed VIX core candidates is preserved in tracked repo artifacts.
- [x] Direct live-label re-evaluation of round1/2/3 follow-up candidate specs is preserved and remains below the mixed-core GLD frontier.

## Replacement Conclusion

- The current GLD live operator is the pure mixed-core baseline line `gld_current_live_mixed_live`.
- The previous overlay line `gld_mixed_vix_vxv_term_panic_live` remains tracked as a historical runtime/operator variant, not the current live default.
- No VIX-driven core GLD replacement candidate survived the final frontier search.

## Tracked Evidence

- `assets/gld/results.tsv`
- `assets/gld/program.md`
- `assets/gld/vix_runtime_replacement_decision.json`
- `assets/gld/vix_core_candidate_screen.json`
- `assets/gld/vix_replacement_frontier_compare.json`
- `assets/gld/live_label_followup_frontier.json`
