# KRE Backlog

## First Round

- [ ] Run `AR_ASSET=kre python prepare.py` and confirm dataset shape.
- [ ] Run `AR_ASSET=kre python train.py` and capture baseline metrics.
- [ ] Run `AR_ASSET=kre python predict_latest.py` for the baseline live snapshot.
- [ ] Run `AR_ASSET=kre python chart_signals.py` and confirm chart output.
- [ ] Write the baseline row into `assets/kre/results.tsv`.

## Notes

- Default label config: `60d +10%/-5% drop-neutral`.
- This asset was scaffolded from the cross-asset first-round batch universe.
