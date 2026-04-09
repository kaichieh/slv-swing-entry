# ETH-USD Backlog

## First Round

- [ ] Run `AR_ASSET=eth-usd python prepare.py` and confirm dataset shape.
- [ ] Run `AR_ASSET=eth-usd python train.py` and capture baseline metrics.
- [ ] Run `AR_ASSET=eth-usd python predict_latest.py` for the baseline live snapshot.
- [ ] Run `AR_ASSET=eth-usd python chart_signals.py` and confirm chart output.
- [ ] Write the baseline row into `assets/eth-usd/results.tsv`.

## Notes

- Default label config: `60d +22%/-11% drop-neutral`.
- This asset was scaffolded from the cross-asset first-round batch universe.
