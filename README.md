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

Asset-specific research outputs should also live inside `assets/<asset>/`.

## Shared Scripts

Core research scripts:

- `prepare.py`
- `train.py`
- `predict_latest.py`
- `chart_signals.py`
- `research_batch.py`
- `research_exit_round1.py`
- `score_results.py`

Regression / ranking scripts:

- `research_regression.py`
- `research_regression_recent.py`
- `research_regression_recent_chart.py`
- `research_regression_walkforward.py`
- `research_regression_compare.py`

Monitoring scripts:

- `refresh_active_status.py`
- `refresh_monitor_snapshot.py`
- `refresh_monitor_board.py`

## How To Run Research

Set the target asset first:

```powershell
$env:AR_ASSET='slv'
$env:PYTHONPATH='C:\Users\Jay\OneDrive\文件\codex\slv-swing-entry\.packages'
```

Then run the standard binary workflow:

```powershell
python prepare.py
python train.py
python predict_latest.py
python chart_signals.py
```

For the broader research workflow:

```powershell
python research_batch.py
python research_exit_round1.py
python score_results.py
```

Swap `slv` for any other asset key as needed.

## How To Regenerate Charts

### Binary assets

Use the standard live prediction + signal chart flow:

```powershell
$env:AR_ASSET='iwm'
$env:PYTHONPATH='C:\Users\Jay\OneDrive\文件\codex\slv-swing-entry\.packages'
python predict_latest.py
python chart_signals.py
```

This currently applies to assets such as:

- `gld`
- `slv`
- `iwm`
- `spy`
- `nvda`
- `tsla`

Generated chart path pattern:

- `.cache/<asset>-swing-entry/signal_chart.html`

### Regression assets

Use the regression recent export + chart flow:

```powershell
$env:AR_ASSET='qqq'
$env:PYTHONPATH='C:\Users\Jay\OneDrive\文件\codex\slv-swing-entry\.packages'
python research_regression_recent.py
python research_regression_recent_chart.py
```

This currently applies to assets such as:

- `qqq`
- `tlt`
- `xle`

Generated chart path pattern:

- `assets/<asset>/regression_recent.html`

## How To Regenerate The Monitor Board

The homepage is:

- `monitor_board.html`

It summarizes non-SLV assets in two sections:

- `Today`: current operating state
- `Role`: structural role in the basket

Recommended refresh order:

```powershell
$env:PYTHONPATH='C:\Users\Jay\OneDrive\文件\codex\slv-swing-entry\.packages'
python refresh_active_status.py
python refresh_monitor_snapshot.py
python refresh_monitor_board.py
```

Because `refresh_active_status.py` and `refresh_monitor_snapshot.py` are asset-specific, run them with `AR_ASSET` set:

```powershell
$env:AR_ASSET='iwm'
python refresh_active_status.py
python refresh_monitor_snapshot.py
```

Then regenerate the shared homepage:

```powershell
python refresh_monitor_board.py
```

## Practical Daily Refresh

If you want to update one asset and then refresh the homepage:

### Binary example

```powershell
$env:AR_ASSET='nvda'
$env:PYTHONPATH='C:\Users\Jay\OneDrive\文件\codex\slv-swing-entry\.packages'
python predict_latest.py
python chart_signals.py
python refresh_active_status.py
python refresh_monitor_snapshot.py
python refresh_monitor_board.py
```

### Regression example

```powershell
$env:AR_ASSET='xle'
$env:PYTHONPATH='C:\Users\Jay\OneDrive\文件\codex\slv-swing-entry\.packages'
python research_regression_recent.py
python research_regression_recent_chart.py
python refresh_active_status.py
python refresh_monitor_snapshot.py
python refresh_monitor_board.py
```

## Notes

- Binary charts and regression charts now both default to a longer recent-history window instead of a 60-bar-only view.
- Asset charts auto-scroll to the right on load so the newest bars are visible first.
- `monitor_board.html` is the main dashboard entry point; use asset charts for full detail.
