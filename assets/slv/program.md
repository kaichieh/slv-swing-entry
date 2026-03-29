# SLV Program

本資產的目標不是預測 SLV 幾天後的精確價格，而是判斷某一天是否值得當成中期波段進場點。

## 預設設定

- horizon: `60` 個交易日
- 上方 barrier: `+8%`
- 下方 barrier: `-4%`
- label mode: `drop-neutral`

## 工作規則

1. 先執行 `task.md` 的正式 backlog。
2. 所有正式結果都寫進 `results.tsv`。
3. 只有在值得正式驗證時，才把 `ideas.md` 的點子搬進 `task.md`。
