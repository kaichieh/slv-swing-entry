# IEF Backlog

## First Round

- [ ] Run `AR_ASSET=ief python prepare.py` and confirm dataset shape.
- [ ] Run `AR_ASSET=ief python train.py` and capture baseline metrics.
- [ ] Run `AR_ASSET=ief python predict_latest.py` for the baseline live snapshot.
- [ ] Run `AR_ASSET=ief python chart_signals.py` and confirm chart output.
- [ ] Write the baseline row into `assets/ief/results.tsv`.

## Notes

- Default label config: `60d +5%/-2% drop-neutral`.
- This asset was scaffolded from the cross-asset first-round batch universe.
