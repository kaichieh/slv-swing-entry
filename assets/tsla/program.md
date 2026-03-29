# TSLA Program

This asset tracks the strongest current binary swing-entry candidate in the repo. The main job now is to decide whether the adopted TSLA line can become a durable operating default.

## Current Research Direction

- baseline reference: `60d +12%/-6% drop-neutral`
- adopted candidate: `60d +15%/-8% + ret_60 + sma_gap_60 + distance_to_252_high`
- focus on rule quality and walk-forward stability rather than basic feature discovery

## Working Style

1. Keep the live adoption decision in `task.md`.
2. Save validated result rows into `results.tsv`.
3. Use `ideas.md` only for follow-up lines that are clearly distinct from the adopted candidate path.
