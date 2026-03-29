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
- [x] Add a repo-level monitor priority view for all non-SLV assets. Performance: `monitor_priority.tsv` and `monitor_priority.html` now sort the same board into daily review order with a suggested next step per asset. The current priority stack is `IWM` first, then `NVDA` and `XLE`, then `QQQ` and `TSLA`, with `SPY` and `TLT` kept only for context or research.
