# CAT Backlog

## First Round

- [ ] Run `AR_ASSET=cat python prepare.py` and confirm dataset shape.
- [ ] Run `AR_ASSET=cat python train.py` and capture baseline metrics.
- [ ] Run `AR_ASSET=cat python predict_latest.py` for the baseline live snapshot.
- [ ] Run `AR_ASSET=cat python chart_signals.py` and confirm chart output.
- [ ] Write the baseline row into `assets/cat/results.tsv`.

## Notes

- Default label config: `60d +10%/-5% drop-neutral`.
- This asset was scaffolded from the cross-asset first-round batch universe.
