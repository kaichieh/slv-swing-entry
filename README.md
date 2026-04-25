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

Use the explicit interpreter path for this repo:

```powershell
C:\Python313\python.exe
```

This avoids ambiguity with other local Python installs and virtual environments that do not have `numpy` / `pandas` installed.

Price downloads now use `yfinance` first, then fall back to the repo's direct Yahoo chart endpoint, then Stooq/cache. For close-based reports generated before the current U.S. session is complete, set `AR_MAX_PRICE_DATE` to the latest completed market date so partial intraday rows are excluded.

Example:

```powershell
$env:PYTHONPATH = "D:\coding\slv\slv-swing-entry\.packages;C:\Users\Jay\AppData\Roaming\Python\Python313\site-packages;" + $env:PYTHONPATH
$env:AR_MAX_PRICE_DATE = "2026-04-22"
C:\Python313\python.exe .\refresh_reports.py
```

### Refresh everything except SLV

```powershell
C:\Python313\python.exe .\refresh_reports.py
```

This will:

- refresh each asset chart
- refresh each asset active-status summary
- refresh each asset monitor snapshot
- rebuild `monitor_board.html`

### Refresh only selected assets

```powershell
C:\Python313\python.exe .\refresh_reports.py iwm nvda xle
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

## Options IV Skeleton

There is now a starter script for per-asset options implied volatility:

- `options_iv.py`

It expects an options chain file at:

- `.cache/<asset>-swing-entry/<asset>_options_chain.csv`

and writes:

- `.cache/<asset>-swing-entry/options_iv_summary.json`
- `assets/<asset>/options_iv_history.csv`

This is intentionally a first-step pipeline for `30D ATM IV`, not a full volatility surface. The history file can now also feed optional `prepare.py` features. See [docs/options-iv-pipeline.md](D:/coding/slv/slv-swing-entry/docs/options-iv-pipeline.md) for the accepted schema and flow.

## Notes

- Binary charts and regression charts both use a longer recent-history window now.
- Asset charts auto-scroll to the right on load so the newest bars are visible first.
- `monitor_board.html` is the main dashboard; use the asset chart pages for detailed context.
