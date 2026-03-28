# SLV Swing Entry

This repo predicts medium-term SLV entry quality instead of short-term direction.

## How To Work In This Repo

This repo should be operated primarily by following [program.md](/C:/Users/Jay/OneDrive/文件/codex/slv-swing-entry/program.md).

In practice:

- read `program.md` first
- execute the current round of tasks from `task.md`
- record all formal experiment results in `results.tsv`
- use `ideas.md` to break down the next round of tasks

## Goal

The default target is:

- `1`: within the next `60` trading days, SLV hits `+8%` before `-4%`
- `0`: within the next `60` trading days, SLV hits `-4%` before `+8%`
- `neutral`: neither barrier is hit first, or both are hit on the same day and ordering is ambiguous

Neutral samples are dropped from training by default.

## Files

- [prepare.py](/C:/Users/Jay/OneDrive/文件/codex/slv-swing-entry/prepare.py): downloads SLV daily data, builds features, and labels barrier outcomes
- [train.py](/C:/Users/Jay/OneDrive/文件/codex/slv-swing-entry/train.py): trains a NumPy logistic baseline on the processed dataset
- [predict_latest.py](/C:/Users/Jay/OneDrive/文件/codex/slv-swing-entry/predict_latest.py): scores the latest raw SLV bar without waiting for future labels
- [chart_signals.py](/C:/Users/Jay/OneDrive/文件/codex/slv-swing-entry/chart_signals.py): exports an HTML chart of recent closes colored by live signal
- [research_batch.py](/C:/Users/Jay/OneDrive/文件/codex/slv-swing-entry/research_batch.py): runs the current formal research batch and writes compact TSV/JSON summaries
- [research_exit_round1.py](/C:/Users/Jay/OneDrive/文件/codex/slv-swing-entry/research_exit_round1.py): runs the first pure-SLV exit/risk-off research round
- [score_results.py](/C:/Users/Jay/OneDrive/文件/codex/slv-swing-entry/score_results.py): refreshes `headline_score` and `promotion_gate` in `results.tsv`
- [results.tsv](/C:/Users/Jay/OneDrive/文件/codex/slv-swing-entry/results.tsv): experiment log
- [task.md](/C:/Users/Jay/OneDrive/文件/codex/slv-swing-entry/task.md): next research tasks

## Default Target Settings

- horizon: `60` trading days
- upper barrier: `+8%`
- lower barrier: `-4%`
- labeling style: `binary drop-neutral`

## Usage

```powershell
$env:PYTHONPATH='C:\Users\Jay\OneDrive\文件\codex\slv-swing-entry\.packages'
python prepare.py
python train.py
python predict_latest.py
python chart_signals.py
python research_batch.py
python research_exit_round1.py
```

## Notes

- Barrier ordering uses daily `high` and `low`.
- If both barriers are touched on the same day, the sample is dropped as ambiguous.
- The repo starts as a clean SLV port of the GLD research framework, so `results.tsv` and `task.md` have been reset for SLV-specific work.
- This is a baseline research repo, not a production trading system.
