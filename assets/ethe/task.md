# ETHE Backlog

## First Round

- [ ] Run `AR_ASSET=ethe python prepare.py` and confirm dataset shape.
- [ ] Run `AR_ASSET=ethe python train.py` and capture baseline metrics.
- [ ] Run `AR_ASSET=ethe python predict_latest.py` for the baseline live snapshot.
- [ ] Run `AR_ASSET=ethe python chart_signals.py` and confirm chart output.
- [ ] Write the baseline row into `assets/ethe/results.tsv`.

## Notes

- Default label config: `60d +20%/-10% drop-neutral`.
- This asset was scaffolded from the cross-asset first-round batch universe.
