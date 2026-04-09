# QQQ Backlog

## First Round

- [ ] Run `AR_ASSET=qqq python prepare.py` and confirm dataset shape.
- [ ] Run `AR_ASSET=qqq python train.py` and capture baseline metrics.
- [ ] Run `AR_ASSET=qqq python predict_latest.py` for the baseline live snapshot.
- [ ] Run `AR_ASSET=qqq python chart_signals.py` and confirm chart output.
- [ ] Write the baseline row into `assets/qqq/results.tsv`.

## Notes

- Default label config: `60d +8%/-4% drop-neutral`.
- This asset was scaffolded from the cross-asset first-round batch universe.
