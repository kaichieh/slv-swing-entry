# Multi-Asset Swing Entry

This repo uses one shared framework for multiple assets instead of one repo per ticker.

## Assets

Current asset folders:

- `assets/gld`
- `assets/slv`
- `assets/qqq`
- `assets/nvda`
- `assets/tsla`
- `assets/spy`
- `assets/iwm`
- `assets/tlt`
- `assets/xle`

Each asset keeps its own:

- `config.json`
- `results.tsv`
- `task.md`
- `ideas.md`
- `program.md`

## Main Output

Main homepage:

- `monitor_board.html`

This is the single dashboard entry point.

From there you can click into each asset chart:

- binary assets -> `.cache/<asset>-swing-entry/signal_chart.html`
- regression assets -> `assets/<asset>/regression_recent.html`

## Generate Reports

### Refresh everything except SLV

```powershell
python .\refresh_reports.py
```

This will:

- refresh each asset chart
- refresh each asset active-status summary
- refresh each asset monitor snapshot
- rebuild `monitor_board.html`

### Refresh only selected assets

```powershell
python .\refresh_reports.py iwm nvda xle
```

This will refresh only those assets, then rebuild the shared monitor board.

## What The Script Does

For binary assets such as:

- `gld`
- `iwm`
- `spy`
- `nvda`
- `tsla`

it runs:

- `predict_latest.py`
- `chart_signals.py`
- `refresh_active_status.py`
- `refresh_monitor_snapshot.py`

For regression assets such as:

- `qqq`
- `tlt`
- `xle`

it runs:

- `research_regression_recent.py`
- `research_regression_recent_chart.py`
- `refresh_active_status.py`
- `refresh_monitor_snapshot.py`

Then it rebuilds:

- `monitor_board.html`

## Notes

- Binary charts and regression charts both use a longer recent-history window now.
- Asset charts auto-scroll to the right on load so the newest bars are visible first.
- `monitor_board.html` is the main dashboard; use the asset chart pages for detailed context.
