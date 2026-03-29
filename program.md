# Multi-Asset Program

This repo now uses one shared research framework across multiple assets.

## Layout

- shared scripts stay at repo root
- per-asset research files live in `assets/<asset>/`
- per-asset cached datasets live in `.cache/<asset>-swing-entry/`

## Usage

Examples:

- `AR_ASSET=slv python prepare.py`
- `AR_ASSET=qqq python train.py`
- `AR_ASSET=nvda python predict_latest.py`
- `AR_ASSET=tsla python chart_signals.py`
