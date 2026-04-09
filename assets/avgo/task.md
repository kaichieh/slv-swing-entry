# AVGO Backlog

## First Round

- [ ] Run `AR_ASSET=avgo python prepare.py` and confirm dataset shape.
- [ ] Run `AR_ASSET=avgo python train.py` and capture baseline metrics.
- [ ] Run `AR_ASSET=avgo python predict_latest.py` for the baseline live snapshot.
- [ ] Run `AR_ASSET=avgo python chart_signals.py` and confirm chart output.
- [ ] Write the baseline row into `assets/avgo/results.tsv`.

## Notes

- Default label config: `60d +12%/-6% drop-neutral`.
- This asset was scaffolded from the cross-asset first-round batch universe.
