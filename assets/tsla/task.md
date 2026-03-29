# TSLA Backlog

## Round 1 Baseline

- [ ] 跑 `AR_ASSET=tsla python prepare.py`，確認資料日期區間、rows、split 與 positive rate。Performance:
- [ ] 跑 `AR_ASSET=tsla python train.py`，建立第一版 baseline metrics，記錄 `validation_f1`、`validation_bal_acc`、`test_f1`、`test_bal_acc`、`threshold`、`headline_score`。Performance:
- [ ] 跑 `AR_ASSET=tsla python predict_latest.py`，記錄最新 `signal`、`raw_model_signal`、`predicted_probability`、`top_20pct_reference`。Performance:
- [ ] 跑 `AR_ASSET=tsla python chart_signals.py`，確認圖表、買點過濾與 tooltip 敘述正常。Performance:
- [ ] 把 baseline 結果補進 `assets/tsla/results.tsv`。Performance:

## Round 2 Label Sanity

- [ ] 比較 `drop-neutral` 與 `keep-all binary`，確認 TSLA 這種高震盪標的是否需要更大的 neutral 區。Performance:
- [ ] 比較 `60d +12%/-6%`、`60d +10%/-5%`、`60d +15%/-8%` 三組 barrier，確認 TSLA 的 label 是否太容易被噪音打掉。Performance:
- [ ] 比較 `40d +12%/-6%` 與 `60d +12%/-6%`，確認 TSLA 是否比較適合短節奏 swing。Performance:
- [ ] 檢查 validation/test 的 label balance 與 future return 分布，確認 regime shift 對結果的影響。Performance:

## Round 3 Feature Sweep

- [ ] 單獨測 `ret_60`，確認 TSLA 是否比 NVDA 更極端地偏向 momentum。Performance:
- [ ] 單獨測 `sma_gap_60`，確認中期均線乖離能否抓到回檔後再起。Performance:
- [ ] 單獨測 `rolling_vol_60`，確認高波動特徵是否直接提升 `test_bal_acc`。Performance:
- [ ] 單獨測 `atr_pct_20`，確認波動率正規化對 TSLA 是否更有效。Performance:
- [ ] 單獨測 `distance_to_252_high`，檢查 TSLA 強訊號是否過度集中在高位追價。Performance:
- [ ] 單獨測 `close_location_20` 或 `drawdown_60`，確認位置型特徵是否比趨勢型特徵更像買點模型。Performance:

## Round 4 Combo And Rule

- [ ] 比較 `ret_60 + sma_gap_60` 與單一 feature，確認 TSLA 主線是否需要雙特徵才穩。Performance:
- [ ] 比較 `ret_60 + sma_gap_60 + rolling_vol_60` 與 `ret_60 + sma_gap_60 + atr_pct_20`，找出較穩的第三特徵。Performance:
- [ ] 測 `neg_weight=1.10/1.15/1.20/1.30`，觀察是否需要更保守的 negative weighting。Performance:
- [ ] 比較 `threshold rule` 與 `top 10% / 15% / 20%`，確認 TSLA live 是否更適合少量高分訊號。Performance:
- [ ] 補跑 4-fold walk-forward，檢查候選模型是否只是在單一熱度區間有效。Performance:

## Round 5 Live And Review

- [ ] 用最佳 TSLA 候選模型重跑 live chart，人工檢查最近 30 天訊號是否符合「買點參考」而不是單純追漲。Performance:
- [ ] 抽查最近幾筆高分訊號，確認買點過濾有把過熱位置降級。Performance:
- [ ] 把 adopted candidate、風險觀察與下一輪 backlog 寫回 `assets/tsla/results.tsv` 與 `assets/tsla/task.md`。Performance:

## Notes

- TSLA 波動大、消息面干擾多，先優先看 barrier 設定與 top-percentile rule 是否比固定 threshold 更穩。
- 如果 live 訊號仍常出現在高位，下一輪應直接把買點過濾條件再收緊。
