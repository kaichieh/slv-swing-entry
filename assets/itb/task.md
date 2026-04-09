# ITB Backlog

## First Round

- [ ] Run `AR_ASSET=itb python prepare.py` and confirm dataset shape.
- [ ] Run `AR_ASSET=itb python train.py` and capture baseline metrics.
- [ ] Run `AR_ASSET=itb python predict_latest.py` for the baseline live snapshot.
- [ ] Run `AR_ASSET=itb python chart_signals.py` and confirm chart output.
- [ ] Write the baseline row into `assets/itb/results.tsv`.

## Notes

- Default label config: `60d +10%/-5% drop-neutral`.
- This asset was scaffolded from the cross-asset first-round batch universe.
