# SHY Backlog

## First Round

- [ ] Run `AR_ASSET=shy python prepare.py` and confirm dataset shape.
- [ ] Run `AR_ASSET=shy python train.py` and capture baseline metrics.
- [ ] Run `AR_ASSET=shy python predict_latest.py` for the baseline live snapshot.
- [ ] Run `AR_ASSET=shy python chart_signals.py` and confirm chart output.
- [ ] Write the baseline row into `assets/shy/results.tsv`.

## Notes

- Default label config: `60d +3%/-2% drop-neutral`.
- This asset was scaffolded from the cross-asset first-round batch universe.
