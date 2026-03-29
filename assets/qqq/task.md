# QQQ Backlog

## Round 1 Baseline

- [ ] 跑 `AR_ASSET=qqq python prepare.py`，確認資料日期區間、rows、train/validation/test split 與 positive rate。Performance:
- [ ] 跑 `AR_ASSET=qqq python train.py`，建立第一版 baseline metrics，記錄 `validation_f1`、`validation_bal_acc`、`test_f1`、`test_bal_acc`、`threshold`、`headline_score`。Performance:
- [ ] 跑 `AR_ASSET=qqq python predict_latest.py`，記錄最新 `signal`、`raw_model_signal`、`predicted_probability`、`top_20pct_reference`。Performance:
- [ ] 跑 `AR_ASSET=qqq python chart_signals.py`，確認圖表與 tooltip 正常輸出。Performance:
- [ ] 把 baseline 結果補進 `assets/qqq/results.tsv`。Performance:

## Round 2 Label Sanity

- [ ] 比較 `drop-neutral` 與 `keep-all binary` baseline，確認 QQQ 是否真的適合保留 neutral filter。Performance:
- [ ] 比較 `60d +8%/-4%`、`60d +10%/-5%`、`60d +6%/-3%` 三組 barrier，判斷 QQQ 是更適合寬鬆 breakout 還是保守 swing。Performance:
- [ ] 比較 `40d +8%/-4%` 與 `60d +8%/-4%`，確認 horizon 對指數型標的是否太長或太短。Performance:
- [ ] 檢查 validation/test label balance 與 future return 分布，避免 baseline 好壞只是 regime 偏移。Performance:

## Round 3 Feature Sweep

- [ ] 單獨測 `ret_60`，確認 QQQ 是否也吃中期趨勢延續。Performance:
- [ ] 單獨測 `sma_gap_60`，確認均線乖離對 QQQ 是否比單股更乾淨。Performance:
- [ ] 單獨測 `rolling_vol_60`，確認波動壓縮或擴張對 QQQ 是否有訊號。Performance:
- [ ] 單獨測 `atr_pct_20`，確認波動率正規化是否優於 raw volatility。Performance:
- [ ] 單獨測 `distance_to_252_high`，檢查 QQQ 是否更像高位強勢延續而非跌深反彈。Performance:
- [ ] 單獨測 `close_location_20` 或 `sma_gap_120`，確認中期位置感是否能改善 `test_bal_acc`。Performance:

## Round 4 Combo And Rule

- [ ] 比較 `ret_60 + sma_gap_60` 與單一 feature，確認 QQQ 是否值得直接走 GLD 類型雙特徵主線。Performance:
- [ ] 比較 `ret_60 + sma_gap_60 + rolling_vol_60` 與 `ret_60 + sma_gap_60 + atr_pct_20`，選出較穩的第三特徵。Performance:
- [ ] 測 `neg_weight=1.10/1.15/1.20`，確認是否能把 `test_bal_acc` 往上拉而不傷 `test_f1`。Performance:
- [ ] 比較 `threshold rule` 與 `top 15% / 17.5% / 20%` ranking-style rule，確認 QQQ live 規則該走門檻制還是分位數制。Performance:
- [ ] 補跑 4-fold walk-forward，確認候選模型不是只在單一 validation 區間看起來漂亮。Performance:

## Round 5 Live And Review

- [ ] 用最好的 QQQ 候選模型重跑 `predict_latest.py` 與 `chart_signals.py`，檢查最近 30 天訊號是否符合「買點參考」而不是高位追價。Performance:
- [ ] 人工抽查最近 5 到 10 筆 `bullish` 以上訊號，確認描述文字、買點過濾、top20 標記是否一致。Performance:
- [ ] 把這輪結論整理進 `assets/qqq/results.tsv` 與 `assets/qqq/task.md`，標示 adopted candidate 或 reject。Performance:

## Notes

- QQQ 比較像指數主線，優先留意 regime、均線位置、距離年內高點這類順勢特徵。
- 如果 QQQ 在 `distance_to_252_high` 或 `above_200dma` 上特別有效，後面可以再開一輪 regime-aware 研究。
