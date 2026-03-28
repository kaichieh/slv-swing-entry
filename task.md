# SLV Backlog

## Round 1

- [x] 跑一次 `python prepare.py`，確認 SLV 資料可以正常下載、切分與落地。Performance: `rows=4665`, `train/validation/test=3265/699/701`, `positive_rate=0.3810`, `date_range=2007-04-30 -> 2026-03-25`。
- [x] 跑一次 `python train.py`，建立 SLV 的 baseline metrics。Performance: `validation_f1=0.4591`, `validation_bal_acc=0.5364`, `test_f1=0.6439`, `test_bal_acc=0.4715`, `threshold=0.387`, `headline_score=0.5445`, `promotion_gate=fail`。
- [x] 跑一次 `python predict_latest.py`，確認 live scoring 可用。Performance: `latest_date=2026-03-27`, `signal=bullish`, `predicted_probability=0.4574`, `decision_threshold=0.3870`, `top_20pct_reference=true`。
- [x] 跑一次 `python chart_signals.py`，確認圖表輸出正常。Performance: `bars_rendered=1260`, `latest_date=2026-03-27`, `output=.cache/slv-swing-entry/signal_chart.html`。
- [x] 把 baseline 結果寫進 `results.tsv`。

## Round 2

- [x] 正式比較 `ret_60`、`sma_gap_60`、`ret_60 + sma_gap_60`。Performance: `ret_60` 最乾淨，`validation_f1=0.4642`, `validation_bal_acc=0.5428`, `test_f1=0.6470`, `test_bal_acc=0.4841`, `headline_score=0.5512`；`sma_gap_60` 較弱，`headline_score=0.5456`；combo `ret_60 + sma_gap_60` 幾乎沒有超過 `ret_60`，`headline_score=0.5509`。
- [x] 檢查 `neg_weight=1.15` 是否能改善 `ret_60 + sma_gap_60`。Performance: `test_f1` 小升到 `0.6497`、`test_bal_acc` 小升到 `0.4868`、`headline_score=0.5520`，但仍未過 gate，提升幅度有限。
- [x] 檢查 `ret_60 + sma_gap_60 + rolling_vol_60` 是否值得升級。Performance: 這條線 `test_f1=0.6628` 最高，但 `validation_f1=0.4577`, `validation_bal_acc=0.5276`, `test_bal_acc=0.4771`，headline 雖到 `0.5525`，仍主要是 test-side 提升，整體還不夠穩。
- [x] 看 `ret_60 + sma_gap_60` 的 walk-forward 與 forward rule。Performance: 4-fold walk-forward `test_bal_acc=0.5000/0.4919/0.4961`，沒有真正站上平衡；forward `threshold avg_return=3.99%`，優於 `top_15pct=2.51%`，但仍不足以證明可升級。

## Round 3

- [x] 以 `ret_60` 為主線，測試是否加入單一低風險補充特徵能把 `test_bal_acc` 拉回 `0.50+`，優先考慮 `distance_to_252_high`、`atr_pct_20`、`sma_gap_120`。Performance: `distance_to_252_high` 偏弱，`headline_score=0.5439`；`sma_gap_120` validation 最乾淨，`validation_bal_acc=0.5526`，但 `test_bal_acc=0.4807`；`atr_pct_20` headline 最好，`validation_f1=0.4615`, `validation_bal_acc=0.5372`, `test_f1=0.6588`, `test_bal_acc=0.4797`, `headline_score=0.5535`，仍未把 test balance 拉回 `0.50+`。
- [ ] 若單一特徵仍無法提升平衡表現，正式比較 barrier 設定 `60d +10%/-5%` 與 `60d +6%/-3%`，確認是否是 label 定義卡住了 SLV。Performance: 目前已有鄰近 sweep 可參考，`60d +12%/-6% + ret_60` 的 `headline_score=0.5797` 明顯高於現行主線，但 `test_bal_acc=0.5094` 仍未過 gate；`80d/120d +8/-4` 只有 `0.5385/0.5389`，因此精準的 `10/-5` 與 `6/-3` 仍值得單獨補跑。
- [x] 跑一次 `python research_exit_round1.py`，確認 SLV 的 exit/risk-off 線有沒有比 entry 線更穩。Performance: `exit_ret_60_plus_sma_gap_60` 是 exit round 最好版本，`validation_f1=0.5900`, `validation_bal_acc=0.5828`, `test_f1=0.3429`, `test_bal_acc=0.5101`, `headline_score=0.4664`；比 entry 線更穩定的證據不足，暫不切主線。

## Round 4

- [ ] 正式補跑 `60d +10%/-5%` 與 `60d +6%/-3%` 在 SLV 上的 baseline 與 `ret_60` 版本，確認 `60d +12%/-6%` 的改善是不是只是鄰近設定偶然值。
- [ ] 若 barrier 線仍過不了 gate，從 `atr_pct_20` 與 `ret_60 + sma_gap_60 + rolling_vol_60` 中各挑一條做 walk-forward 深驗，確認是否只是 test 分數漂亮但 forward 站不住。

## Notes

- 這個 repo 是從 `gld-swing-entry` 框架移植而來，但研究紀錄已重置。
- 後續所有 `Performance:` 都應該是 SLV 自己跑出來的結果。
- `predict_latest.py` 已改成 baseline-only live default，避免沿用 GLD 模板裡未經 SLV 驗證的 extra features。
