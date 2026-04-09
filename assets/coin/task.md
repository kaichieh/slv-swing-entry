# COIN Backlog

## First Round

- [ ] Run `AR_ASSET=coin python prepare.py` and confirm dataset shape.
- [ ] Run `AR_ASSET=coin python train.py` and capture baseline metrics.
- [ ] Run `AR_ASSET=coin python predict_latest.py` for the baseline live snapshot.
- [ ] Run `AR_ASSET=coin python chart_signals.py` and confirm chart output.
- [ ] Write the baseline row into `assets/coin/results.tsv`.

## Notes

- Default label config: `60d +18%/-9% drop-neutral`.
- This asset was scaffolded from the cross-asset first-round batch universe.
