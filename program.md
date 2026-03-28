# SLV Swing Entry Program

本 repo 的目標不是預測 SLV 幾天後的精確價格，而是判斷某一天是否值得當成中期波段進場點。

## 預設任務定義

- horizon: `60` 個交易日
- 上方 barrier: `+8%`
- 下方 barrier: `-4%`
- label mode: `drop-neutral`

也就是：

- `1`: 未來 `60` 個交易日內，先碰到 `+8%`
- `0`: 未來 `60` 個交易日內，先碰到 `-4%`
- `neutral`: 兩邊都沒先明確成立，或同日同時觸發而無法排序

## 工作原則

1. 先跑目前 `task.md` 上排最前面的正式研究項目。
2. 每個正式實驗都要把結果寫進 `results.tsv`。
3. 每輪做完後，把觀察整理回 `task.md`，必要時把新想法放進 `ideas.md`。
4. 不把 GLD 的舊結論直接搬來當成 SLV 的已驗證事實。

## 執行流程

1. 先讀 `task.md`
2. 跑 `prepare.py`
3. 依研究需要跑 `train.py`、`predict_latest.py`、`research_batch.py` 或 `research_exit_round1.py`
4. 把正式結果補到 `results.tsv`
5. 更新 `task.md`
6. 若有新方向，再補進 `ideas.md`

## results.tsv 規格

欄位固定為：

- `commit_id`
- `validation_f1`
- `validation_accuracy`
- `validation_bal_acc`
- `test_f1`
- `test_accuracy`
- `test_bal_acc`
- `headline_score`
- `promotion_gate`
- `status`
- `description`

`status` 使用方式：

- `live`: 目前 `predict_latest.py` 與圖表使用的主線
- `candidate`: 值得繼續驗證的候選
- `discard`: 已確認不值得追的方向

## task.md 規格

- 只放目前還有效的 SLV backlog
- 每項正式任務完成後補上 `Performance: ...`
- 若某條線已明確失敗，從主線移除並把原因寫清楚

## ideas.md 規格

- 放還沒正式排進 backlog 的點子
- 可以記錄 feature、label、rule、walk-forward、risk 管理方向
- 只有在值得正式驗證時才搬進 `task.md`
