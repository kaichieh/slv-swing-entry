# NFLX Backlog

## First Round

- [ ] Run `AR_ASSET=nflx python prepare.py` and confirm dataset shape.
- [ ] Run `AR_ASSET=nflx python train.py` and capture baseline metrics.
- [ ] Run `AR_ASSET=nflx python predict_latest.py` for the baseline live snapshot.
- [ ] Run `AR_ASSET=nflx python chart_signals.py` and confirm chart output.
- [ ] Write the baseline row into `assets/nflx/results.tsv`.

## Notes

- Default label config: `60d +12%/-6% drop-neutral`.
- This asset was scaffolded from the cross-asset first-round batch universe.
