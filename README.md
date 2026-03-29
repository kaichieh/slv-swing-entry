# Multi-Asset Swing Entry

This repo uses one shared framework for multiple assets instead of one repo per ticker.

## Assets

- `slv`
- `qqq`
- `nvda`
- `tsla`

Each asset has its own folder:

- `assets/<asset>/config.json`
- `assets/<asset>/results.tsv`
- `assets/<asset>/task.md`
- `assets/<asset>/ideas.md`
- `assets/<asset>/program.md`

Research outputs generated for a specific asset should also live inside `assets/<asset>/`.

## Shared Scripts

- `prepare.py`
- `train.py`
- `predict_latest.py`
- `chart_signals.py`
- `research_batch.py`
- `research_exit_round1.py`
- `score_results.py`

## How To Run

```powershell
$env:AR_ASSET='slv'
python prepare.py
python train.py
python predict_latest.py
python chart_signals.py
python research_batch.py
python research_exit_round1.py
python score_results.py
```

Swap `slv` for `qqq`, `nvda`, or `tsla` as needed.
