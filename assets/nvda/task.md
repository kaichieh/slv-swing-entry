# NVDA Backlog

## Round 1 Baseline

- [ ] 跑 `AR_ASSET=nvda python prepare.py`，確認資料日期區間、rows、split 與 positive rate。Performance:
- [ ] 跑 `AR_ASSET=nvda python train.py`，建立第一版 baseline metrics，記錄 `validation_f1`、`validation_bal_acc`、`test_f1`、`test_bal_acc`、`threshold`、`headline_score`。Performance:
- [ ] 跑 `AR_ASSET=nvda python predict_latest.py`，記錄最新 `signal`、`raw_model_signal`、`predicted_probability`、`top_20pct_reference`。Performance:
- [ ] 跑 `AR_ASSET=nvda python chart_signals.py`，確認圖表、買點過濾與 tooltip 敘述正常。Performance:
- [ ] 把 baseline 結果補進 `assets/nvda/results.tsv`。Performance:

## Round 2 Label Sanity

- [ ] 比較 `drop-neutral` 與 `keep-all binary`，確認高波動單股 NVDA 是否需要保留 neutral 區間。Performance:
- [ ] 比較 `60d +12%/-6%`、`60d +10%/-5%`、`60d +15%/-8%` 三組 barrier，確認 NVDA 的 target 寬度。Performance:
- [ ] 比較 `40d +12%/-6%` 與 `60d +12%/-6%`，確認 NVDA 是否比較適合短一點的 swing horizon。Performance:
- [ ] 檢查 validation/test future return 與 label balance，避免測到的 improvement 其實只是 AI 熱潮 regime 偏差。Performance:

## Round 3 Feature Sweep

- [ ] 單獨測 `ret_60`，確認 NVDA 是否極度偏向 momentum。Performance:
- [ ] 單獨測 `sma_gap_60`，確認中期均線乖離是否比報酬特徵更穩。Performance:
- [ ] 單獨測 `rolling_vol_60`，確認高 beta 股票是否適合波動率特徵。Performance:
- [ ] 單獨測 `atr_pct_20`，確認 normalized volatility 是否優於 raw 波動特徵。Performance:
- [ ] 單獨測 `distance_to_252_high`，檢查高位強勢延續對 NVDA 的解釋力。Performance:
- [ ] 單獨測 `close_location_20` 或 `up_day_ratio_20`，確認短線位置與節奏對買點判斷是否有幫助。Performance:

## Round 4 Combo And Rule

- [ ] 比較 `ret_60 + sma_gap_60` 與單一 feature，確認 NVDA 主線該走純 momentum 還是 momentum + mean reversion 混合。Performance:
- [ ] 比較 `ret_60 + sma_gap_60 + rolling_vol_60` 與 `ret_60 + sma_gap_60 + atr_pct_20`，挑一個更穩的第三特徵。Performance:
- [ ] 測 `neg_weight=1.10/1.15/1.20/1.30`，觀察高波動單股是否需要更強負樣本權重。Performance:
- [ ] 比較 `threshold rule` 與 `top 10% / 15% / 20%`，確認 NVDA live 是否更適合少量高 conviction 訊號。Performance:
- [ ] 補跑 4-fold walk-forward，檢查候選模型在不同市場階段是否還站得住。Performance:

## Round 5 Live And Review

- [ ] 用最佳 NVDA 候選模型重跑 live chart，人工檢查最近 30 天強訊號是不是大多落在可接受買點，而不是噴出後追價。Performance:
- [ ] 抽查最近 `strong_bullish` / `very_strong_bullish` 樣本，確認 chart 文案有把「過熱、超賣、回檔、量能」說清楚。Performance:
- [ ] 把 adopted candidate、被淘汰候選與下一輪假設寫回 `assets/nvda/results.tsv` 與 `assets/nvda/task.md`。Performance:

## Notes

- NVDA 容易受單一大趨勢驅動，先特別留意 barrier 是否太緊，避免把正常波動誤標成失敗。
- 如果 `distance_to_252_high` 很強，下一輪可以再加做 `above_200dma` 或相對 QQQ 的 cross-asset 特徵。
