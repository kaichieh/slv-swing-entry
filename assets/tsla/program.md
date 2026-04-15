# TSLA Program

This asset tracks the strongest current binary swing-entry candidate in the repo. The main job now is to validate whether the new TSLA XGBoost line can stay strong enough across rolling windows to justify long-term default status.

## Current Research Direction

- baseline reference: `60d +12%/-6% drop-neutral`
- adopted candidate: `future-return-top-bottom-30pct + distance_to_252_high + xgboost`
- live settings: `n_estimators=150`, `max_depth=2`, `learning_rate=0.05`
- focus on walk-forward robustness and operator behavior now that the headline target has been cleared

## Working Style

1. Keep the live adoption decision in `task.md`.
2. Save validated result rows into `results.tsv`.
3. Use `ideas.md` only for follow-up lines that are clearly distinct from the adopted candidate path.
