# TAN Backlog

## First Round

- [ ] Run `AR_ASSET=tan python prepare.py` and confirm dataset shape.
- [ ] Run `AR_ASSET=tan python train.py` and capture baseline metrics.
- [ ] Run `AR_ASSET=tan python predict_latest.py` for the baseline live snapshot.
- [ ] Run `AR_ASSET=tan python chart_signals.py` and confirm chart output.
- [ ] Write the baseline row into `assets/tan/results.tsv`.

## Notes

- Default label config: `60d +12%/-6% drop-neutral`.
- This asset was scaffolded from the cross-asset first-round batch universe.
