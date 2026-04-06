# 第 1 輪研究任務

說明：

- 這份 `task.md` 只放本輪真正要執行的任務，不一次塞入過多想法。
- 每個任務做完都要打勾，並在後方補 `Performance` 或簡短結論。
- 若只是想到但還沒排入本輪，請不要先寫進這裡。
- 若同一主題需要更細的參數展開，先完成上層探索，再補開下層任務。

## 一、標記設計

目標：先確認 `60d / +8% / -4% / drop-neutral` 是否合理，避免後面所有實驗建立在不好的標記上。

- [x] 統計目前 `positive / negative / neutral` 比例。Performance: `positive=2023`, `negative=2346`, `neutral=935`, `total=5304`.
- [x] 檢查 `drop-neutral` 後剩餘樣本數是否足夠。Performance: `drop_neutral_rows=4369`，約保留 `82.4%` 樣本。
- [x] 比較 `drop-neutral` 與 `keep-all binary` 的 class balance。Performance: `drop-neutral` 正類率 `0.4630`；`keep-all binary` 正類率 `0.3814`。
- [x] 比較 `60d +8%/-4%` 與 `60d +10%/-5%` 的標籤分布。Performance: `+10/-5` 的 `neutral_rate=0.3064`，明顯高於目前設定的 `0.1763`。
- [x] 比較 `60d +8%/-4%` 與 `60d +6%/-3%` 的標籤分布。Performance: `+6/-3` 的 `neutral_rate=0.0626`，但正類率降到 `0.4429`。
- [x] 比較 `40d +8%/-4%` 與 `60d +8%/-4%` 的標籤分布。Performance: `40d` 的 `neutral_rate=0.3173`，高於 `60d` 的 `0.1763`。

## 二、基準模型

目標：建立一個穩定、可重跑的 baseline，後面所有改動都和它比較。

- [x] 跑一次目前 baseline，記錄完整指標。Performance: `validation_f1=0.5765`, `validation_bal_acc=0.5102`, `validation_accuracy=0.4150`, `test_f1=0.8129`, `test_bal_acc=0.5526`, `threshold=0.491`.
- [x] 重跑 baseline 第二次，確認結果一致。Performance: 第二次結果完全相同，確認可重跑。
- [x] 固定 threshold `0.50` 比較 baseline。Performance: `validation_f1=0.1433`, `validation_bal_acc=0.4979`，明顯劣於自動 threshold。
- [x] 比較 `threshold_steps=401` 與 `threshold_steps=801`。Performance: 兩者都選到 `threshold=0.491`，`validation_f1=0.5765`，沒有差異。
- [x] 比較 best epoch by `validation_f1` 與 best epoch by `validation_bal_acc`。Performance: 兩者都選到 `epoch=11`，結果一致。

## 三、特徵擴充

目標：先做最有希望的中期特徵，不一次展開太多細碎組合。

- [x] 加入 `ret_60`。Performance: `validation_f1=0.0000`, `validation_bal_acc=0.5000`, `test_f1=0.0000`。
- [x] 加入 `drawdown_60`。Performance: `validation_f1=0.0000`, `validation_bal_acc=0.5000`, `test_f1=0.0000`。
- [x] 加入 `volatility_20`。Performance: `validation_f1=0.5733`, `validation_bal_acc=0.5013`, `test_f1=0.8143`。
- [x] 加入 `volume_vs_60`。Performance: `validation_f1=0.0000`, `validation_bal_acc=0.5000`, `test_f1=0.0000`。
- [x] 加入 `sma_gap_60`。Performance: `validation_f1=0.0000`, `validation_bal_acc=0.5000`, `test_f1=0.0000`。
- [x] 加入 `range_z_20`。Performance: `validation_f1=0.5758`, `validation_bal_acc=0.5064`, `test_f1=0.8173`。
- [x] 加入 `gap_up_flag`。Performance: `validation_f1=0.5752`, `validation_bal_acc=0.5077`, `test_f1=0.8162`。
- [x] 加入 `gap_down_flag`。Performance: `validation_f1=0.5771`, `validation_bal_acc=0.5115`, `test_f1=0.8164`。
- [x] 加入 `inside_bar`。Performance: `validation_f1=0.5771`, `validation_bal_acc=0.5115`, `test_f1=0.8137`。
- [x] 加入 `outside_bar`。Performance: `validation_f1=0.5765`, `validation_bal_acc=0.5102`, `test_f1=0.8159`。

## 四、特徵替換

目標：找出哪些新特徵值得取代舊特徵，而不是只是無限制往上疊。

- [x] 用 `drawdown_60` 替換 `drawdown_20`。Performance: `validation_f1=0.0000`, `validation_bal_acc=0.5000`, `test_f1=0.0000`。
- [x] 用 `volatility_20` 替換 `volatility_10`。Performance: `validation_f1=0.5739`, `validation_bal_acc=0.5026`, `test_f1=0.8166`。
- [x] 用 `sma_gap_60` 替換 `sma_gap_20`。Performance: `validation_f1=0.0000`, `validation_bal_acc=0.5000`, `test_f1=0.0000`。
- [x] 用 `volume_vs_60` 替換 `volume_vs_20`。Performance: `validation_f1=0.0000`, `validation_bal_acc=0.5000`, `test_f1=0.0000`。
- [x] 用 `range_z_20` 替換 `range_pct`。Performance: `validation_f1=0.5758`, `validation_bal_acc=0.5064`, `test_f1=0.8158`。

## 五、互動項

目標：只測少數高價值 interaction，不做無限制暴力組合。

- [x] 測 `gap_up_flag:drawdown_20`。Performance: `validation_f1=0.5752`, `validation_bal_acc=0.5077`, `test_f1=0.8162`。
- [x] 測 `gap_up_flag:volume_vs_20`。Performance: `validation_f1=0.5752`, `validation_bal_acc=0.5077`, `test_f1=0.8151`。
- [x] 測 `drawdown_20:volume_vs_20`。Performance: `validation_f1=0.5853`, `validation_bal_acc=0.5346`, `test_f1=0.8092`。
- [x] 測 `ret_20:drawdown_20`。Performance: `validation_f1=0.5777`, `validation_bal_acc=0.5102`, `test_f1=0.8152`。
- [x] 測 `ret_20:breakout_20`。Performance: `validation_f1=0.5790`, `validation_bal_acc=0.5128`, `test_f1=0.8019`。
- [x] 測 `rsi_14:drawdown_20`。Performance: `validation_f1=0.5791`, `validation_bal_acc=0.5154`, `test_f1=0.7947`。

## 六、參數探索

目標：只做一小圈有根據的參數微調，不做無上限掃描。

- [x] 試 `neg_weight = 1.1`。Performance: `validation_f1=0.5771`, `validation_bal_acc=0.5115`, `test_f1=0.8159`。
- [x] 試 `neg_weight = 1.2`。Performance: `validation_f1=0.5765`, `validation_bal_acc=0.5102`, `test_f1=0.8159`。
- [x] 試 `neg_weight = 1.3`。Performance: `validation_f1=0.5771`, `validation_bal_acc=0.5115`, `test_f1=0.8148`。
- [x] 試 `l2_reg = 5e-4`。Performance: `validation_f1=0.5765`, `validation_bal_acc=0.5102`, `test_f1=0.8129`。
- [x] 試 `l2_reg = 2e-3`。Performance: `validation_f1=0.5765`, `validation_bal_acc=0.5102`, `test_f1=0.8129`。
- [x] 試 `learning_rate = 0.01`。Performance: `validation_f1=0.5771`, `validation_bal_acc=0.5115`, `test_f1=0.8137`。
- [x] 試 `learning_rate = 0.03`。Performance: `validation_f1=0.5765`, `validation_bal_acc=0.5102`, `test_f1=0.8144`。

## 七、驗證穩定性

目標：避免只是在單一 validation 區段看起來漂亮。

- [x] 做一次 3-fold walk-forward validation。Performance: fold `validation_f1=[0.6084, 0.5765, 0.8233]`。
- [x] 做一次 4-fold walk-forward validation。Performance: fold `validation_f1=[0.5043, 0.5214, 0.6326, 0.6743]`。
- [x] 比較不同 fold 的 threshold 穩定性。Performance: 3-fold threshold `[0.471, 0.491, 0.491]`；4-fold threshold `[0.300, 0.496, 0.492, 0.427]`。
- [x] 比較不同 fold 的 `validation_f1` 波動。Performance: 3-fold 範圍約 `0.5765 -> 0.8233`；4-fold 範圍約 `0.5043 -> 0.6743`，穩定性普通。
- [x] 重建資料後再跑 baseline。Performance: refresh 後 baseline 仍為 `validation_f1=0.5765`, `validation_bal_acc=0.5102`, `test_f1=0.8129`。
- [x] 用 3 個 seed 重跑目前最佳設定。Performance: seed `1/2/3` 全部一致，`validation_f1=0.5765`, `test_f1=0.8129`。

## 八、交易解讀

目標：讓模型指標能對應到真正的買入決策，而不是只看分類分數。

- [x] 統計預測為正類時的平均 `future_return_60`。Performance: baseline threshold `0.491` 下，`test_avg_return=8.99%`。
- [x] 統計預測為正類時的勝率。Performance: baseline threshold `0.491` 下，預測正類的 `win_rate=0.8462`。
- [x] 比較不同 threshold 下的正類比例。Performance: `0.45 -> 1.0000`, `0.49 -> 0.9557`, `0.50 -> 0.0474`, `0.55 -> 0.0000`。
- [x] 比較不同 threshold 下的平均報酬。Performance: `0.45 -> 8.27%`, `0.49 -> 8.85%`, `0.50 -> 9.97%`, `0.55 -> 0%`。
- [x] 寫出一版簡單交易解讀摘要。Performance: 目前 baseline 對正類預測過多，導致 `validation_f1` 偏弱；雖然預測正類的平均 60 日報酬高，但暫時不能當成穩定交易訊號。

## 下一輪候選方向

這裡暫時不列具體任務，只保留方向提示：

- barrier 設計第二輪細化
- 中期回撤類特徵深化
- ranking / 回歸版本
- 簡易回測框架

---

# 第 2 輪研究任務

## 一、標記設計第二輪

- [x] 正式比較 `drop-neutral` 與 `keep-all binary` 的 baseline 表現。Performance: `keep-all binary` 為 `validation_f1=0.5341`, `validation_bal_acc=0.5052`, `test_f1=0.7001`, `test_bal_acc=0.4993`，全面弱於目前 `drop-neutral` baseline。
- [x] 正式比較 `60d +8%/-4%` 與 `60d +6%/-3%` 的 baseline 表現。Performance: `60d +6%/-3%` 為 `validation_f1=0.6080`, `validation_bal_acc=0.5319`, `test_f1=0.7231`, `test_bal_acc=0.4802`，validation 提升但 test 明顯退化。
- [x] 正式比較 `60d +8%/-4%` 與 `60d +10%/-5%` 的 baseline 表現。Performance: `60d +10%/-5%` 為 `validation_f1=0.5167`, `validation_bal_acc=0.5378`, `test_f1=0.7277`, `test_bal_acc=0.5602`，validation_f1 明顯低於目前預設。

## 二、目前最佳模型深化

- [x] 在目前最佳設定上測 `neg_weight = 1.1`。Performance: `validation_f1=0.5851`, `validation_bal_acc=0.5320`, `test_f1=0.8115`, `test_bal_acc=0.5623`，test 略好但 validation_f1 仍低於目前最佳。
- [x] 在目前最佳設定上測 `neg_weight = 1.2`。Performance: `validation_f1=0.5853`, `validation_bal_acc=0.5346`, `test_f1=0.8081`, `test_bal_acc=0.5637`，validation 持平但 test_f1 較弱。
- [x] 在目前最佳設定上測 `learning_rate = 0.01`。Performance: `validation_f1=0.5845`, `validation_bal_acc=0.5307`, `test_f1=0.8074`, `test_bal_acc=0.5613`，未優於目前最佳。
- [x] 在目前最佳設定上比較 `threshold_steps=401` 與 `801`。Performance: `threshold=0.422`、`validation_f1=0.5853`、`test_f1=0.8092` 完全一致，沒有額外收益。

## 三、最佳方向延伸

- [x] 在目前最佳設定上加入 `gap_down_flag`。Performance: `validation_f1=0.5836`, `validation_bal_acc=0.5327`, `test_f1=0.8058`, `test_bal_acc=0.5614`，未優於目前最佳。
- [x] 在目前最佳設定上加入 `inside_bar`。Performance: `validation_f1=0.5849`, `validation_bal_acc=0.5327`, `test_f1=0.8081`, `test_bal_acc=0.5589`，未優於目前最佳。
- [x] 在目前最佳設定上加入 `range_z_20`。Performance: `validation_f1=0.5840`, `validation_bal_acc=0.5262`, `test_f1=0.8092`, `test_bal_acc=0.5552`，test_f1 持平但 validation 與平衡度較弱。
- [x] 在目前最佳設定上加入 `gap_down_flag:drawdown_20`。Performance: `validation_f1=0.5836`, `validation_bal_acc=0.5327`, `test_f1=0.8070`, `test_bal_acc=0.5626`，沒有形成有效突破。
- [x] 在目前最佳設定上加入 `range_z_20:drawdown_20`。Performance: `validation_f1=0.5859`, `validation_bal_acc=0.5359`, `test_f1=0.8054`, `test_bal_acc=0.5579`，validation 小幅創高但 test 退化，不升級為正式最佳。

## 四、交易規則校準

- [x] 比較 `threshold=0.42`、`0.45`、`0.49` 的交易解讀。Performance: `0.42` 最接近目前最佳，`test_f1=0.8085`, `avg_return=8.83%`；`0.45` 雖把單筆平均報酬拉到 `9.28%`，但 `test_f1` 降到 `0.6279`；`0.49` 僅交易 `1.38%` 樣本，`test_f1=0.0310`，過度保守。
- [x] 只交易最高信心 `top 20%` 樣本並統計表現。Performance: 約對應門檻 `0.4661`，`selected_count=131`, `avg_return=9.09%`, `win_rate=0.6870`，但 `test_f1=0.3141`, `test_bal_acc=0.5051`，不適合直接取代現行規則。
- [x] 只交易最高信心 `top 10%` 樣本並統計表現。Performance: 約對應門檻 `0.4735`，`selected_count=66`, `avg_return=7.85%`, `win_rate=0.6970`，`test_f1=0.1811`，過度稀疏且報酬也未更好。

## 五、問題排查

- [x] 釐清為何 `ret_60`、`drawdown_60`、`sma_gap_60`、`volume_vs_60` 加入後會退化到幾乎全負類。Performance: 根因不是特徵本身，而是這四個 `60` 日特徵在 train split 各殘留 `8` 個 NaN；先前標準化時 NaN 直接污染整欄，導致 logits 與 threshold 搜尋失真，表面上變成幾乎全負類。已在 `train.py` 加入 NaN guard，未來會直接報錯而不是產生假結果。
- [x] 檢查 validation 與 test 落差過大的原因，特別是正類比例與 threshold 行為。Performance: 目前最佳設定在 validation 的實際正類率僅 `0.4012`，test 則升到 `0.6758`；固定 threshold `0.422` 下，模型在兩段都預測約九成正類，但 validation precision 只有 `0.4191`，test precision 升到 `0.7047`。主因較像時段分布轉移與 test 區間更偏多頭，而不是模型在 test 真正更穩定。

---

# 第 3 輪研究任務

## 一、長週期特徵修正重跑

- [x] 補上實驗特徵的 NaN 處理策略，正式重跑 `ret_60`。Performance: NaN-clean 資料集為 `4347` 列，`ret_60` 重新變成有效特徵，`validation_f1=0.5868`, `validation_bal_acc=0.5345`, `test_f1=0.8128`, `test_bal_acc=0.5718`，整體優於 NaN-clean baseline。
- [x] 補上實驗特徵的 NaN 處理策略，正式重跑 `drawdown_60`。Performance: `validation_f1=0.5824`, `validation_bal_acc=0.5333`, `test_f1=0.8078`, `test_bal_acc=0.5636`，未優於 NaN-clean baseline。
- [x] 補上實驗特徵的 NaN 處理策略，正式重跑 `sma_gap_60` 與 `volume_vs_60`。Performance: `sma_gap_60` 為 `validation_f1=0.5917`, `validation_bal_acc=0.5428`, `test_f1=0.8083`, `test_bal_acc=0.5768`，validation 與平衡度最強；`volume_vs_60` 為 `validation_f1=0.5811`, `validation_bal_acc=0.5224`, `test_f1=0.8084`, `test_bal_acc=0.5516`，仍偏弱。

## 二、目前最佳設定再驗證

- [x] 對 `neg_weight = 1.1` 做 seed 與 walk-forward 驗證，確認 test 改善是否可重現。Performance: seed `1/2/3` 完全一致，但 forward folds 的 `test_f1=[0.6065, 0.7468, 0.0000]`、`test_bal_acc=[0.4986, 0.5262, 0.0000]` 波動極大，test 小幅改善不具穩定性。
- [x] 對 `range_z_20:drawdown_20` 做 seed 與 walk-forward 驗證，確認 validation 小幅提升是否可信。Performance: seed `1/2/3` 完全一致，但 forward folds 的 `test_f1=[0.6047, 0.7526, 0.0000]`、`test_bal_acc=[0.5002, 0.5381, 0.0000]` 同樣不穩定，validation 小升幅不足以升級。

## 三、交易框架下一步

- [x] 為目前最佳設定建立簡單回測摘要，至少統計命中率、平均報酬與最大回撤。Performance: 以 NaN-clean baseline 的 `threshold=0.433` 做簡化逐筆回測摘要，`selected_count=588`, `hit_rate=0.7075`, `avg_return=9.02%`, `max_drawdown=-84.70%`；顯示目前規則雖命中率高，但訊號過密時資金曲線品質很差。
- [x] 比較「現行 threshold 規則」與「top 20% ranking 規則」在簡單回測下的差異。Performance: `top 20%` 規則選出 `131` 筆、`hit_rate=0.6870`, `avg_return=9.19%`, `max_drawdown=-35.33%`；雖命中率略低，但回撤明顯比現行 threshold 規則低。

---

# 第 4 輪研究任務

## 一、長週期特徵正式升級驗證

- [x] 以 `ret_60` 為新候選最佳，做 seed 與 walk-forward 驗證。Performance: seed `1/2/3` 完全一致，當前切分下 `validation_f1=0.5868`, `test_f1=0.8128`, `test_bal_acc=0.5718`；forward folds 前兩折 `test_f1=0.5748 -> 0.8140`，顯示可用但仍受時段影響。
- [x] 以 `sma_gap_60` 為新候選最佳，做 seed 與 walk-forward 驗證。Performance: seed `1/2/3` 完全一致，當前切分下 `validation_f1=0.5917`, `validation_bal_acc=0.5428`, `test_bal_acc=0.5768` 最強；forward folds 前兩折 `test_f1=0.5242 -> 0.8107`，穩定性仍受 regime 影響。
- [x] 測試 `ret_60 + drawdown_20:volume_vs_20` 是否可疊加。Performance: 指標與 `ret_60` 完全一致，因為目前模型預設就已含 `drawdown_20:volume_vs_20` interaction，沒有新增效果。
- [x] 測試 `sma_gap_60 + drawdown_20:volume_vs_20` 是否可疊加。Performance: 指標與 `sma_gap_60` 完全一致，原因同上，屬於重複設定而非新突破。

## 二、交易規則深化

- [x] 建立非重疊持倉的簡單回測，重新估算目前最佳規則的最大回撤。Performance: 改成非重疊持倉後，NaN-clean baseline `threshold rule` 只產生 `11` 筆交易，`hit_rate=0.7273`, `avg_return=8.01%`, `max_drawdown=-5.41%`；先前的 `-84.70%` 主要是重疊持倉假設造成的失真。
- [x] 比較 `ret_60` 模型在 `threshold rule` 與 `top 20% ranking rule` 下的回測摘要。Performance: `threshold rule` 為 `11` 筆、`hit_rate=0.7273`, `avg_return=8.01%`, `max_drawdown=-5.41%`；`top 20%` 為 `9` 筆、`hit_rate=0.7778`, `avg_return=9.91%`, `max_drawdown=-6.80%`，報酬與命中率較高，但回撤略大且樣本更少。

## 三、時段轉移排查

- [x] 比較 validation 與 test 區間的實際 barrier 命中分布，確認是否存在 regime shift。Performance: validation 正類率僅 `0.4003`、平均 60 日報酬 `1.41%`，test 正類率升到 `0.6753`、平均 60 日報酬 `8.27%`，明顯存在多頭 regime shift。
- [x] 測試改用較晚起始年份訓練，是否能縮小 validation/test 落差。Performance: `2012` 與 `2016` 起訓雖讓 `f1` 看起來升高，但 `validation_bal_acc`/`test_bal_acc` 都掉到 `0.5000`，本質上只是更偏向全正類，沒有真的縮小落差。

---

# 第 5 輪研究任務

## 一、候選最佳正面對決

- [x] 正式比較 `ret_60` 與 `sma_gap_60`，加入同一張對照表與交易摘要。Performance: `ret_60` 保有最高 `test_f1=0.8128`，`sma_gap_60` 則有更強的 `validation_f1=0.5917` 與 `test_bal_acc=0.5768`；兩者都值得保留，但單看一方已不夠。
- [x] 測試 `ret_60 + sma_gap_60` 是否能同時保留 test_f1 與 validation_bal_acc。Performance: 組合版成為本輪最佳新候選，`validation_f1=0.5928`, `validation_bal_acc=0.5460`, `test_f1=0.8088`, `test_bal_acc=0.5948`, `test_accuracy=0.7075`，在整體平衡度上明顯優於單獨版本。
- [x] 測試 `ret_60 + sma_gap_60 + drawdown_20:volume_vs_20` 的整體表現，確認雙長週期特徵是否互補。Performance: 指標與 `ret_60 + sma_gap_60` 完全一致，因為 `drawdown_20:volume_vs_20` 本來就是預設 interaction，沒有額外增益。
- [x] 測試 `ret_60` 取代 `ret_20` 後的版本，確認長週期報酬是否比短週期報酬更有用。Performance: `validation_f1=0.5809`, `validation_bal_acc=0.5365`, `test_f1=0.8000`, `test_bal_acc=0.5785`；長週期報酬不能直接取代短週期報酬，兩者並存反而更好。

## 二、交易規則細化

- [x] 對 `ret_60` 模型測 `top 10%`、`top 15%`、`top 20%` 的非重疊持倉回測。Performance: `top 10%` 為 `8` 筆、`avg_return=7.99%`, `max_drawdown_compound=-6.80%`；`top 15%` 同為 `8` 筆、`avg_return=8.59%`；`top 20%` 為 `9` 筆、`hit_rate=0.7778`, `avg_return=9.91%`, `max_drawdown_compound=-6.80%`，是三者中最有交易味道的版本。
- [x] 對 `sma_gap_60` 模型測 `threshold rule` 與 `top 20% rule` 的非重疊持倉回測。Performance: `threshold` 為 `11` 筆、`hit_rate=0.9091`, `avg_return=8.06%`, `max_drawdown_compound=-5.41%`；`top 20%` 為 `9` 筆、`hit_rate=0.7778`, `avg_return=9.43%`, `max_drawdown_compound=-6.80%`，屬於高命中率換取較低單筆報酬的典型差異。
- [x] 對 `sma_gap_60` 模型測 `top 10%`、`top 15%`、`top 20%` 的非重疊持倉回測。Performance: `top 10%` 偏弱，僅 `7` 筆、`avg_return=6.36%`；`top 15%` 最亮眼，`9` 筆、`hit_rate=0.7778`, `avg_return=10.59%`, `max_drawdown_compound=-6.80%`；`top 20%` 次之，`avg_return=9.43%`。
- [x] 比較 `ret_60` 與 `sma_gap_60` 在相同非重疊持倉假設下的交易次數、命中率、平均報酬與最大回撤。Performance: 兩者 `threshold` 規則都做出 `11` 筆、`hit_rate=0.9091`、`max_drawdown_compound=-5.41%` 的高命中低報酬型態；進入 ranking 後，`ret_60 top 20%` 的 `avg_return=9.91%`，`sma_gap_60 top 15%` 則到 `10.59%`，後者在精選交易上略占優勢。
- [x] 測試將 `weak_bullish` 視為不進場，只交易 `bullish` 以上訊號時的非重疊回測摘要。Performance: `ret_60 bullish+` 為 `10` 筆、`hit_rate=0.8000`, `avg_return=8.25%`, `max_drawdown_compound=-6.80%`；比 `threshold` 少一筆交易，但命中率與回撤都沒有更好，暫不值得升級。

## 三、Regime 感知驗證

- [x] 將 validation/test 按年份切段，統計每段的 barrier 正類率與平均 60 日報酬。Performance: validation 中 `2020/2021/2022` 的正類率約 `0.35~0.42`、平均 60 日報酬最多僅 `3.09%`；test 的 `2024/2025` 正類率則升到 `0.8374/0.8438`，平均 60 日報酬達 `9.56%/15.02%`，而 `2026` 又轉回 `0.4340` 與 `-8.23%`。
- [x] 測試加入簡單 regime 特徵後，是否能降低 validation/test 分布落差。Performance: 沒有。`year` 讓 `test_f1` 掉到 `0.6541`；`rolling_return_120` 幾乎變成全正類，`test_bal_acc=0.5000`；`rolling_vol_60` 是最接近可用的版本，但 `validation_f1=0.5762`, `test_bal_acc=0.5695` 仍不如 `ret_60` 與雙特徵組合。
- [x] 建立 `year`, `rolling_return_120`, `rolling_vol_60` 三種簡單 regime 特徵候選，逐一測試是否改善 `validation_bal_acc`。Performance: `year=0.5249`、`rolling_return_120=0.5013`、`rolling_vol_60=0.5090`；三者都沒有超過 `ret_60` 的 `0.5345`，更遠落後於 `ret_60 + sma_gap_60` 的 `0.5460`。
- [x] 比較 2008、2011、2020、2024 之後不同市場階段中，`ret_60` 與 `sma_gap_60` 的預測正類率變化。Performance: 兩模型在 `2011-2019` 都偏高，`ret_60=0.9677`, `sma_gap_60=0.9689`；到了 `2024+` 才降到 `0.8729` 與 `0.8458`，`sma_gap_60` 對近期 regime 的收斂感較強，但整體仍偏多。

## 四、標記與視窗延伸

- [x] 在目前較強特徵下，正式比較 `60d +8%/-4%` 與 `80d +8%/-4%`。Performance: `80d +8%/-4%` 的 `validation_f1=0.5944` 看似較高，但 `validation_bal_acc=0.5049`, `test_bal_acc=0.5276`, `test_positive_rate=0.9537`，本質上接近幾乎全正類。
- [x] 在目前較強特徵下，正式比較 `60d +8%/-4%` 與 `120d +8%/-4%`。Performance: `120d +8%/-4%` 把 `validation_f1` 拉到 `0.6275`、`test_f1` 拉到 `0.8219`，但 `validation_bal_acc=0.5012`, `test_bal_acc=0.5135`, `test_positive_rate=0.9843`，明顯是更嚴重的正類偏置，不可視為正式升級。
- [x] 在目前較強特徵下，正式比較 `60d +8%/-4%` 與 `60d +12%/-6%`。Performance: `60d +12%/-6%` 把 `validation_bal_acc` 拉到 `0.6322`，但 `validation_f1=0.5346`, `test_f1=0.7250`，核心主指標大幅退步，不如現行設定。

## 五、回測框架深化

- [x] 在非重疊持倉回測中加入單利與複利兩種資金曲線摘要。Performance: 已輸出到 `backtest_comparison.tsv`，例如 `ret_60 threshold` 的 `max_drawdown_simple=-4.92%`、`max_drawdown_compound=-5.41%`，而 ranking 規則多落在 `-6.80%` 左右。
- [x] 在非重疊持倉回測中加入最長連敗、最長連勝與交易筆數統計。Performance: `threshold` 規則普遍為 `11` 筆且最長連勝 `9`；`ret_60 top 20%` 與 `sma_gap_60 top 15%` 都有 `9` 筆、最長連勝 `6`、最長連敗 `1`，方便直接比較交易節奏。
- [x] 產出 `ret_60` 與 `sma_gap_60` 的回測對照表，寫回 repo 內可重跑的輸出檔。Performance: 已新增可重跑腳本 `research_batch.py`，並輸出 `backtest_comparison.tsv` 與 `regime_summary.tsv`。

---

# 第 6 輪研究任務

## 一、雙長週期組合正式升級驗證

- [x] 以 `ret_60 + sma_gap_60` 為新候選最佳，做 seed 與 walk-forward 驗證。Performance: seed `1/2/3` 完全一致，當前切分下維持 `validation_f1=0.5928`, `validation_bal_acc=0.5460`, `test_f1=0.8088`, `test_bal_acc=0.5948`；forward folds 為 `test_f1=[0.5971, 0.7466]`, `test_bal_acc=[0.5114, 0.5285]`，仍受 regime 影響，但比單獨 `ret_60` 略穩。
- [x] 比較 `ret_60 + sma_gap_60` 與 `ret_60` 在 forward folds 中的 `test_f1`、`test_bal_acc` 與預測正類率。Performance: combo 在兩折的 `test_f1` 為 `0.5971/0.7466`，略低於或接近 `ret_60` 的 `0.6035/0.7429`，但 `test_bal_acc` 提升到 `0.5114/0.5285`，且 `predicted_positive_rate` 降到 `0.8953/0.9402`，比 `ret_60` 的 `0.9574/0.9448` 更收斂。
- [x] 測試 `ret_60 + sma_gap_60 + neg_weight=1.1`，確認雙長週期組合是否仍能受益於較高負類權重。Performance: `validation_f1=0.5931`, `validation_bal_acc=0.5454` 接近原版，但 `test_f1=0.8040`, `test_bal_acc=0.5903` 略退，沒有額外收益。
- [x] 測試 `ret_60 + sma_gap_60` 再加入 `rolling_vol_60`，確認唯一相對不差的 regime 候選是否能在雙特徵模型上帶來增益。Performance: `validation_f1=0.5813`, `validation_bal_acc=0.5192`, `test_f1=0.8087`, `test_bal_acc=0.5852`；整體弱於純 combo，不值得保留。

## 二、雙長週期組合交易規則深化

- [x] 對 `ret_60 + sma_gap_60` 模型測 `threshold`、`top 10%`、`top 15%`、`top 20%` 的非重疊持倉回測。Performance: `threshold` 為 `11` 筆、`hit_rate=0.9091`, `avg_return=8.15%`, `max_drawdown_compound=-5.41%`；`top 10%` 為 `7` 筆、`avg_return=7.86%`；`top 15%` 為 `9` 筆、`avg_return=10.39%`, `max_drawdown_compound=-6.80%`；`top 20%` 也有 `9` 筆、`avg_return=10.29%`，其中 `top 15%` 最平衡。
- [x] 對 `ret_60 + sma_gap_60` 模型測 `bullish+` 與 `strong_bullish+` 兩種 signal 分級規則。Performance: `bullish+` 與 `top 20%` 幾乎等價，`9` 筆、`avg_return=10.29%`；`strong_bullish+` 僅 `7` 筆、`avg_return=7.35%`, `max_drawdown_compound=-6.80%`，過度嚴格反而變弱。
- [x] 比較 `ret_60 + sma_gap_60` 與 `ret_60`、`sma_gap_60` 三者在相同非重疊假設下的交易次數、平均報酬與最大回撤。Performance: 三者 `threshold` 規則都產生 `11` 筆與 `-5.41%` 複利最大回撤，但 combo 的 `avg_return=8.15%` 略高；精選規則下，combo `top 15%/20%` 的 `10.39%/10.29%` 優於 `ret_60 top 20%` 的 `9.91%`，略低於 `sma_gap_60 top 15%` 的 `10.59%`，屬於更平衡的中間解。

## 三、正類偏高問題收斂

- [x] 對 `ret_60 + sma_gap_60` 比較 `threshold_steps=401` 與更窄的高分區間 threshold 掃描，觀察是否能降低預測正類率而不傷 `validation_f1`。Performance: `401/801/1201` 三組的 `validation_f1` 完全相同，門檻只在 `0.4610~0.4625` 間微調；`801` 反而讓 `test_f1` 小降到 `0.8076`，不能有效收斂正類率。
- [x] 對 `ret_60 + sma_gap_60` 測試固定 threshold `0.47`、`0.49`、`0.51` 的分類與非重疊回測摘要。Performance: `0.47` 有 `11` 筆、`avg_return=7.40%`；`0.49` 降到 `8` 筆但 `avg_return=9.53%`；`0.51` 只剩 `2` 筆、`avg_return=2.51%`，過度保守。若要收斂交易密度，`0.49` 是較可討論的固定門檻。
- [x] 統計 `ret_60 + sma_gap_60` 在 validation/test 的 `predicted_positive_rate`、precision、recall，確認是否比單特徵版本更接近可交易密度。Performance: validation 為 `predicted_positive_rate=0.9294`, `precision=0.4241`, `recall=0.9847`；test 為 `0.8545`, `0.7240`, `0.9161`。相較 `ret_60`，combo 的正類率更低、precision 更高，確實較接近可交易密度。

## 四、新長週期候選延伸

- [x] 建立並測試 `ret_120`。Performance: `validation_f1=0.5724`, `validation_bal_acc=0.5013`, `test_f1=0.8062`, `test_bal_acc=0.5000`；幾乎走向全正類，沒有研究價值。
- [x] 建立並測試 `sma_gap_120`。Performance: `validation_f1=0.5831`, `validation_bal_acc=0.5288`, `test_f1=0.8077`, `test_bal_acc=0.5588`；比 `ret_120` 好，但仍明顯弱於 `sma_gap_60` 與雙長週期 combo。
- [x] 測試 `ret_60:sma_gap_60` interaction，確認雙長週期特徵之間是否存在額外非線性訊號。Performance: `validation_f1=0.6074`, `validation_bal_acc=0.5767` 很亮眼，但 `test_f1=0.7304`、`test_positive_rate=0.6539` 明顯崩掉，屬於 validation overfit 而非正式突破。

---

# 第 7 輪研究任務

## 一、雙長週期組合正式升級決戰

- [x] 以 `ret_60 + sma_gap_60` 做更完整 walk-forward，至少補到 4-fold 並整理成正式對照表。Performance: 4-fold 中實際可用 `3` 折，`test_f1=[0.4520, 0.6094, 0.8182]`, `test_bal_acc=[0.5027, 0.5327, 0.5329]`；仍有 regime 波動，但沒有單點崩壞到全零，確認 combo 不是偶然單折結果。
- [x] 比較 `ret_60 + sma_gap_60` 與 `sma_gap_60 top 15%` 的 forward 交易摘要，確認分類最佳與交易最佳是否其實是不同策略。Performance: forward 非重疊摘要中，`combo threshold` 共 `38` 筆、`hit_rate=0.6053`, `avg_return=2.94%`；`sma_gap_60 top 15%` 為 `29` 筆、`hit_rate=0.5517`, `avg_return=2.40%`。目前分類最佳與交易最佳沒有分岔，combo 仍略占優勢。
- [x] 對 `ret_60 + sma_gap_60` 測 `neg_weight=1.05` 與 `1.15`，確認是否存在比 `1.1` 更溫和的平衡點。Performance: `1.05` 為 `validation_f1=0.5931`, `test_f1=0.8028`, `test_bal_acc=0.5892`，不如原版；`1.15` 則為 `validation_f1=0.5934`, `validation_bal_acc=0.5448`, `test_f1=0.8135`, `test_bal_acc=0.5946`，成為目前新的主線候選。

## 二、交易密度控制

- [x] 對 `ret_60 + sma_gap_60` 比較自動 threshold、固定 `0.49`、`top 15%`、`top 20%` 的非重疊回測與 precision/recall。Performance: 自動 threshold 仍是最穩的高命中版本，`11` 筆、`hit_rate=0.9091`, `avg_return=8.15%`；固定 `0.49` 降到 `8` 筆但 `avg_return=9.53%`；`top 15%` 與 `top 20%` 都是 `9` 筆，平均報酬分別 `10.39%` / `10.29%`。若追求交易密度收斂與報酬兼顧，`0.49` 或 `top 15%` 最值得後續驗證。
- [x] 為 `ret_60 + sma_gap_60` 加入「每次訊號後至少冷卻 N 天」的簡單規則，比較 `N=5`、`10`。Performance: 這條線目前沒用。`cooldown_5d` 反而產生 `100` 筆、`max_drawdown_compound=-36.66%`；`cooldown_10d` 仍有 `57` 筆、`max_drawdown_compound=-28.04%`，遠差於非重疊規則。
- [x] 產出 `ret_60 + sma_gap_60` 的 signal 分級統計，包含 `weak/bullish/strong/very_strong` 各級樣本數、命中率與平均報酬。Performance: `weak_bullish=428` 筆、`hit_rate=0.8621`, `avg_return=9.46%`；`bullish=96` 筆、`0.8750`, `8.75%`；`strong_bullish=24` 筆、`0.9583`, `9.27%`；`very_strong_bullish=10` 筆、`0.8000`, `8.10%`。目前 `strong_bullish` 最像少量高品質訊號，但 `very_strong` 樣本太少且未更強。

## 三、延伸長週期候選

- [x] 建立並測試 `drawdown_120`。Performance: `validation_f1=0.5841`, `validation_bal_acc=0.5294`, `test_f1=0.8030`, `test_bal_acc=0.5351`；沒有超越目前主線。
- [x] 建立並測試 `volume_vs_120`。Performance: `validation_f1=0.5843`, `validation_bal_acc=0.5262`, `test_f1=0.8068`, `test_bal_acc=0.5372`；同樣偏弱。
- [x] 測試 `sma_gap_60 + sma_gap_120`，確認均線長週期疊加是否比報酬型長週期更自然。Performance: `validation_f1=0.5913`, `validation_bal_acc=0.5409`, `test_f1=0.8105`, `test_bal_acc=0.5695`；是較乾淨的次佳方案，但仍落後 `ret_60 + sma_gap_60` 與其 `neg_weight=1.15` 版本。

---

# 第 8 輪研究任務

## 一、主線升級確認

- [x] 以 `ret_60 + sma_gap_60 + neg_weight=1.15` 做 seed 與 4-fold walk-forward 驗證。Performance: seed `1/2/3` 完全一致，當前切分為 `validation_f1=0.5934`, `validation_bal_acc=0.5448`, `test_f1=0.8135`, `test_bal_acc=0.5946`；4-fold 可用 `3` 折的 `test_f1=[0.4549, 0.6104, 0.8153]`, `test_bal_acc=[0.5065, 0.5188, 0.5395]`，與原 combo 接近但整體略優。
- [x] 比較 `ret_60 + sma_gap_60 + neg_weight=1.15` 與原 combo 在自動 threshold、固定 `0.49`、`top 15%` 下的非重疊回測。Performance: forward `threshold` 摘要為 `38` 筆、`hit_rate=0.6053`, `avg_return=2.98%`，比原 combo 的 `2.94%` 稍高；當前 test 切分下，`fixed 0.49` 與 `top 15%` 仍維持原 combo 類似的少量高報酬型態，主差異主要來自分類面而非交易規則崩壞。
- [x] 比較 `ret_60 + sma_gap_60 + neg_weight=1.15` 的 `headline_score` 與 `promotion_gate` 是否能穩定勝過原 combo。Performance: `neg_weight=1.15` 為 `headline_score=0.6770`, `promotion_gate=pass`；原 combo 為 `0.6751`, `pass`。目前新版本小幅領先，但優勢不大，仍值得下一輪再做更嚴格對照。

## 二、交易規則收斂

- [x] 對原 combo 與 `neg_weight=1.15` 版本比較 `strong_bullish+` 與 `top 15%` 是否其實選到相似樣本。Performance: 原 combo `strong_bullish+` 僅 `7` 筆、`avg_return=7.35%`，明顯弱於 `top 15%` 的 `9` 筆、`avg_return=10.39%`；`neg_weight=1.15` 版本的 `strong_bullish` bucket 也只有 `22` 筆、平均報酬 `7.81%`，說明 `strong_bullish+` 並不等於最佳交易切法。
- [x] 針對原 combo 與 `neg_weight=1.15` 版本，統計固定 `0.49` 下的 trade count、hit rate、avg return、precision、recall。Performance: 原 combo 在 `0.49` 下為 `8` 筆、`hit_rate=0.7500`, `avg_return=9.53%`；`neg_weight=1.15` 版本的正類率提高到 `0.8683`，代表固定門檻下更容易放行，因此之後若採 `0.49`，需要與 precision/recall 一起看，不宜只看報酬摘要。
- [x] 將 `signal_bucket_summary.tsv` 擴成可比較兩個模型版本的對照表。Performance: 已改成同時輸出原 combo 與 `neg_weight=1.15` 的各級 signal 統計；新版本的 `bullish` bucket 為 `97` 筆、`hit_rate=0.8969`, `avg_return=9.38%`，比原 combo 的 `96` 筆、`8.75%` 更好，但 `strong_bullish` 反而較弱。

## 三、次佳備案驗證

- [x] 以 `sma_gap_60 + sma_gap_120` 做 seed 與 walk-forward 驗證，確認它是否能成為更穩但較保守的備案。Performance: 當前切分為 `validation_f1=0.5913`, `validation_bal_acc=0.5409`, `test_f1=0.8105`, `test_bal_acc=0.5695`，確實乾淨但仍落後主線；若要作為備案可接受，但不是升級方向。
- [x] 測試 `sma_gap_60 + sma_gap_120 + neg_weight=1.15`。Performance: `validation_f1=0.5900`, `validation_bal_acc=0.5384`, `test_f1=0.8097`, `test_bal_acc=0.5623`，比未加權版本還略退，沒有必要續追。

---

# 第 9 輪研究任務

## 一、主線最後確認

- [x] 對 `ret_60 + sma_gap_60 + neg_weight=1.15` 比較固定 `0.47`、`0.49`、`top 15%`、`top 20%` 的完整 precision/recall 與非重疊回測。Performance: `fixed 0.47` 為 `precision=0.6595`, `recall=0.2766`, `avg_return=9.43%`；`fixed 0.49` 雖有 `precision=0.8000`，但 `recall=0.0181`, `selected_count=3`, `avg_return=3.64%` 明顯過度收縮；`top 15%` 為 `precision=0.6224`, `recall=0.1383`, `avg_return=8.59%`；`top 20%` 為 `precision=0.6260`, `recall=0.1859`, `avg_return=9.54%`，是 `neg_weight=1.15` 版本中最實用的 ranking 規則。
- [x] 對 `ret_60 + sma_gap_60 + neg_weight=1.15` 做與原 combo 完全對稱的 `signal_bucket_summary` 與 `backtest_comparison` 對照表。Performance: 已新增 `rule_comparison.tsv` 做對稱輸出；原 combo 在 `top 15%/20%` 的 `avg_return=10.39%/10.29%` 仍高於 `neg_weight=1.15` 的 `8.59%/9.54%`，而 `neg_weight=1.15` 只有 `threshold` 在模型面維持領先，交易面並未全面超車。
- [x] 針對 `ret_60 + sma_gap_60 + neg_weight=1.15` 補一次更長 horizon 的 forward 交易摘要，確認優勢不是只出現在目前 test 切分。Performance: 已將 `forward_trade_summary.tsv` 擴成多規則 walk-forward 對照；`combo_neg115_threshold` 為 `38` 筆、`hit_rate=0.6053`, `avg_return=2.98%`，`combo_neg115_top_20pct` 為 `30` 筆、`0.5667`, `3.07%`，但原 combo `top 15%` 仍以 `30` 筆、`0.6333`, `3.32%` 最佳，說明主線模型雖強，最佳交易規則仍偏向原 combo ranking。

## 二、最終交易規則候選收斂

- [x] 在原 combo 與 `neg_weight=1.15` 版本之間，正式比較 `auto threshold`、`fixed 0.49`、`top 15%` 三種規則，挑出最值得保留的單一交易規則。Performance: 若看 walk-forward 交易摘要，原 combo `top 15%` 以 `trade_count=30`, `hit_rate=0.6333`, `avg_return=3.32%` 最佳；`neg_weight=1.15 threshold` 次佳為 `38` 筆、`2.98%`；兩邊的 `fixed 0.49` 都顯著偏弱，尤其 `neg_weight=1.15 fixed 0.49` 只剩 `avg_return=0.01%`。
- [x] 若 `top 15%` 仍然最好，補做 `top 12.5%` 與 `top 17.5%`，確認是否需要更細化 ranking 門檻。Performance: 已延伸到第 10 輪正式比較；原 combo 在 walk-forward 仍以 `top 15%` 的 `avg_return=3.32%` 最佳，`top 12.5%` 與 `top 17.5%` 都沒有超過它。
- [x] 若 `fixed 0.49` 仍然最好，補做 `0.48` 與 `0.50`，確認是否存在更穩定的固定門檻。Performance: 本輪已先證實 `fixed 0.49` 並非最佳，原 combo 只有 `avg_return=1.01%`、`neg_weight=1.15` 更接近 `0%`，因此不再展開 `0.48/0.50` 細化。

---

# 第 10 輪研究任務

## 一、ranking 規則最後收斂

- [x] 以原 combo 為主，正式比較 `top 12.5%`、`top 15%`、`top 17.5%` 的 test 與 walk-forward 交易摘要。Performance: test 非重疊回測中 `top 12.5%` 與 `fixed 0.49` 幾乎同型，`avg_return=9.53%`；`top 15%` 仍最佳，`avg_return=10.39%`；`top 17.5%` 與 `top 20%` 接近，約 `10.29%`。walk-forward 上則是 `top 12.5%=2.85%`, `top 15%=3.32%`, `top 17.5%=2.99%`，確認原 combo `top 15%` 仍是最穩的 ranking 規則。
- [x] 對 `neg_weight=1.15` 版本補做 `top 17.5%`，確認它是否比 `top 20%` 更平衡。Performance: `top 17.5%` 在 test 非重疊回測下 `precision=0.6261`, `recall=0.1633`, `avg_return=10.59%`，高於 `top 20%` 的 `9.54%`；但 walk-forward 上 `top 17.5%=3.04%` 仍略低於 `top 20%=3.07%`，差距很小但尚未形成明顯優勢。

## 二、主線模型與交易規則切分

- [x] 將「模型正式最佳」與「交易規則正式最佳」分開記錄到 `results.tsv` / `task.md` 摘要中，避免 `headline_score` 最佳與交易摘要最佳混在一起。Performance: `results.tsv` 已補記「模型正式最佳」仍為 `ret_60 + sma_gap_60 + neg_weight=1.15`，但「交易規則正式最佳」目前偏向原 combo `top 15%`；`task.md` 也已分開描述兩條結論。
- [x] 針對原 combo `top 15%` 與 `neg_weight=1.15 threshold/top 20%` 做並排結論，明確決定下一輪要沿模型主線還是交易主線前進。Performance: 若看模型面，下一輪主線仍應是 `neg_weight=1.15`；若看可交易規則，原 combo `top 15%` 目前最強，`avg_return=3.32%` 高於 `neg_weight=1.15 threshold` 的 `2.98%` 與 `neg_weight=1.15 top 20%` 的 `3.07%`，因此下一輪應優先沿交易主線收斂 ranking 規則，而不是再強追固定門檻。

---

# 第 11 輪研究任務

## 一、交易主線最後收斂

- [x] 以原 combo `top 15%` 為主，補做 `top 14%`、`top 16%`，確認最佳 ranking 門檻是否已在局部最優附近。Performance: `top 14%` walk-forward `avg_return=3.50%`、`top 15%=3.44%`、`top 16%=3.29%`；test 非重疊回測則 `top 15%`/`16%` 同為 `8.93%`，但 `top 14%` 只剩 `7.65%`。整體看最佳點就在 `14%~15%` 附近，沒有必要再往更寬的 ranking 門檻延伸。
- [x] 對原 combo `top 15%` 與 `neg_weight=1.15 top 20%` 做同一套 walk-forward 與 test 對照摘要，決定是否正式把交易主線固定成原 combo ranking。Performance: 原 combo `top 15%` 的 walk-forward 為 `trade_count=27`, `hit_rate=0.6667`, `avg_return=3.44%`；`neg_weight=1.15 top 20%` 則是 `31` 筆、`0.6129`, `3.99%`，但 test 非重疊回測上原 combo `top 15%` 仍較穩，`avg_return=8.93%` 對 `9.75%` 且正類率更受控。結論是交易主線仍偏向原 combo ranking，但 `neg_weight=1.15 top 20%` 值得保留成較積極備案。

## 二、模型主線保守追蹤

- [x] 在 `ret_60 + sma_gap_60 + neg_weight=1.15` 上只做極小範圍的 `neg_weight=1.12`、`1.18` 檢查，確認 `1.15` 是否真的是局部最佳。Performance: `neg_weight=1.12` 為 `validation_f1=0.5950`, `validation_bal_acc=0.5533`, `test_f1=0.8124`, `test_bal_acc=0.5935`；`1.18` 為 `0.5957`, `0.5546`, `0.8124`, `0.5935`。兩者都沒有明顯超過目前 `neg_weight=1.15` / 新 cohort combo，說明局部最優已經非常平。

---

# 第 12 輪研究任務

## 一、新 input 擴充首輪

- [x] 加入 `distance_to_252_high`，先單獨與目前 baseline / combo 比較，確認長週期位置資訊是否有額外訊號。Performance: 單獨版本為 `validation_f1=0.5721`, `validation_bal_acc=0.5105`, `test_f1=0.8031`, `test_bal_acc=0.5200`，單獨不強；但加到 combo 後變成 `validation_f1=0.5847`, `validation_bal_acc=0.5387`, `test_f1=0.8204`, `test_bal_acc=0.5979`，是本輪最強的新 input 加成候選。
- [x] 加入 `close_location_20`，檢查收盤在近 20 日區間中的相對位置是否能補足現有 return / drawdown 特徵。Performance: 單獨版本為 `validation_f1=0.5853`, `validation_bal_acc=0.5374`, `test_f1=0.8091`, `test_bal_acc=0.5463`；加到 combo 後 validation 衝到 `0.6010 / 0.5696`，但 `test_f1=0.7886` 明顯退化，屬於新的 validation 型強者。
- [x] 加入 `up_day_ratio_20`，檢查近 20 日上漲天數比例是否能提供比 `ret_20` 更穩的結構資訊。Performance: 單獨版本為 `validation_f1=0.5788`, `validation_bal_acc=0.5262`, `test_f1=0.8110`, `test_bal_acc=0.5449`；加到 combo 後為 `validation_f1=0.5878`, `validation_bal_acc=0.5433`, `test_f1=0.8116`, `test_bal_acc=0.5962`，屬於乾淨的次佳組合。
- [x] 加入 `above_200dma_flag`，檢查是否能改善現有 regime shift 問題。Performance: 單獨版本直接退化成全正類，`validation_bal_acc=0.5000`, `test_bal_acc=0.5000`；加到 combo 後也只有 `test_bal_acc=0.5192`，沒有解 regime 問題。
- [x] 加入 `atr_pct_20`，檢查波動狀態資訊是否能改善泛化。Performance: 單獨版本為 `validation_f1=0.5805`, `validation_bal_acc=0.5282`, `test_f1=0.8115`, `test_bal_acc=0.5487`；加到 combo 後為 `validation_f1=0.5915`, `validation_bal_acc=0.5525`, `test_f1=0.8096`, `test_bal_acc=0.6028`，balanced accuracy 本輪最佳，是第二個值得追的候選。
- [x] 加入 `gld_vs_spy_20`，檢查跨資產相對強弱是否能提供現有純 GLD 特徵沒有的資訊。Performance: 單獨版本 `test_f1=0.8139` 看起來亮眼，但 `validation_bal_acc=0.5039`, `test_bal_acc=0.5292` 很弱；加到 combo 後更是掉到 `test_f1=0.7593`，暫不續追。

## 二、新 input 收斂

- [x] 從上述 6 個新 input 中保留前 2 名，再各自與 `ret_60 + sma_gap_60` 組合比較。Performance: 目前保留的前 2 名是 `distance_to_252_high` 與 `atr_pct_20`；前者拉高 `test_f1/test_bal_acc` 到 `0.8204/0.5979`，後者把 `test_bal_acc` 拉到 `0.6028`，兩者都比 `close_location_20`、`gld_vs_spy_20` 更健康。
- [x] 若新 input 中有特別偏交易規則的一項，補做 `top 15%` 規則比較，確認它改善的是模型分數還是交易摘要。Performance: 本輪先以模型分數篩選，新 input 還沒有正式進入交易規則比較；但 `distance_to_252_high` 與 `atr_pct_20` 都屬於「模型面有效」而不是單純靠 ranking 規則撐起來，下一輪才值得做 `top 15%` 實測。

---

# 第 13 輪研究任務

## 一、新 input 候選深化

- [x] 對 `ret_60 + sma_gap_60 + distance_to_252_high` 做 seed 與 walk-forward 驗證，確認它是否能正式超過目前主線。Performance: seed 結果為 `validation_f1=0.5237`, `validation_bal_acc=0.5239`, `test_f1=0.8231`, `test_bal_acc=0.5941`；walk-forward 三折中前兩折仍有 `all-positive` 傾向，`test_bal_acc=0.4995/0.5000`，只有第三折站得住，說明它是高上限候選，但還不能算正式超車。
- [x] 對 `ret_60 + sma_gap_60 + atr_pct_20` 做 seed 與 walk-forward 驗證，確認高 balanced accuracy 是否穩定。Performance: seed 結果為 `validation_f1=0.5362`, `validation_bal_acc=0.5460`, `test_f1=0.8094`, `test_bal_acc=0.5962`；walk-forward 仍有 `0.4993/0.5000/0.5796` 的 regime 不穩，但第三折表現比距高點版本略平衡，是較保守的候選。
- [x] 對 `ret_60 + sma_gap_60 + up_day_ratio_20` 做快速複驗，確認它是否是值得保留的第三候選。Performance: seed 結果為 `validation_f1=0.5326`, `validation_bal_acc=0.5439`, `test_f1=0.8036`, `test_bal_acc=0.5928`；walk-forward 三折依序為 `test_f1=0.6171/0.5699/0.7943`、`test_bal_acc=0.5019/0.5000/0.5868`，可保留作第三候選，但優先級低於 `distance_to_252_high` 與 `atr_pct_20`。

## 二、交易規則與新 input 交叉驗證

- [x] 若 `distance_to_252_high` 或 `atr_pct_20` 在模型面站得住，補做 `top 15%` 與 `top 20%` 規則比較，確認它們提升的是模型品質還是交易摘要。Performance: `distance_to_252_high` 版本在 test 非重疊回測上 `top 20%` 最亮眼，`avg_return=11.26%`，但 walk-forward 則是 `top 15%=4.51%` 優於 `top 20%=3.89%`；`atr_pct_20` 版本則由 `top 20%` 同時拿下 test `11.13%` 與 walk-forward `4.73%`。兩者都不只是靠 headline_score 撐起來，而是確實值得做交易規則深挖。

---

# 第 14 輪研究任務

## 一、第二批 datasource 擴充

- [x] 加入 `DXY` datasource，先做 `gld_vs_dxy_20` 或等價美元相對強弱特徵，檢查美元方向是否能提供黃金外部 context。Performance: 這裡以 `UUP` 作為美元 proxy；單獨版本為 `validation_f1=0.5324`, `validation_bal_acc=0.5425`, `test_f1=0.8114`, `test_bal_acc=0.5772`，加到 combo 後為 `0.5391 / 0.5512 / 0.8054 / 0.5868`，沒有打進前段班。
- [x] 加入 `TLT` datasource，先做 `gld_vs_tlt_20` 或等價債券相對強弱特徵，檢查利率 / 債券方向是否能補足 GLD 單體訊號。Performance: 單獨版本是第二批 datasource 中最好的 standalone，`validation_f1=0.5312`, `validation_bal_acc=0.5413`, `test_f1=0.8230`, `test_bal_acc=0.5884`；加到 combo 後為 `0.5366 / 0.5488 / 0.8058 / 0.5910`，沒有超過主線。
- [x] 加入 `GDX` datasource，先做 `gld_vs_gdx_20` 或等價金礦股相對強弱特徵，檢查金礦股是否能領先反映金價趨勢。Performance: 單獨版本為 `validation_f1=0.5355`, `validation_bal_acc=0.5491`, `test_f1=0.8058`, `test_bal_acc=0.5795`；加到 combo 後變成 `validation_f1=0.5367`, `validation_bal_acc=0.5458`, `test_f1=0.8134`, `test_bal_acc=0.6000`，是第二批 datasource 中最強的 combo 候選。
- [x] 加入 `SLV` datasource，先做 `slv_gld_ratio_20` 或等價白銀 / 黃金相對強弱特徵，檢查貴金屬內部輪動是否有額外資訊。Performance: 單獨版本 `validation_f1=0.5380`, `validation_bal_acc=0.5515` 不差，但 `test_f1=0.7863`, `test_bal_acc=0.5363` 偏弱；加到 combo 後也掉到 `test_f1=0.7877`，暫不追。

## 二、datasource 收斂

- [x] 從 `DXY / TLT / GDX / SLV` 四個新 datasource 中保留前 1 到 2 名，再與 `ret_60 + sma_gap_60 + distance_to_252_high` 或 `atr_pct_20` 主線組合比較。Performance: 保留的 datasource 是 `TLT` 與 `GDX`。其中 `ret_60 + sma_gap_60 + distance_to_252_high + gld_vs_gdx_20` 最亮眼，`validation_f1=0.5258`, `validation_bal_acc=0.5278`, `test_f1=0.8249`, `test_bal_acc=0.5996`，headline_score 約 `0.6678`，略高於當前 cohort baseline；`distance + TLT` 也有 `test_f1=0.8261`，但 balanced accuracy 較低。`atr + TLT/GDX` 都沒有超過單獨的 `distance + GDX`。

---

# 第 15 輪研究任務

## 一、最強 cross-asset 候選深化

- [x] 對 `ret_60 + sma_gap_60 + distance_to_252_high + gld_vs_gdx_20` 做 seed 與 walk-forward 驗證，確認它是否是真正的新主線候選。Performance: seed `1/2/3` 完全一致，`validation_f1=0.5258`, `validation_bal_acc=0.5278`, `test_f1=0.8249`, `test_bal_acc=0.5996`；但 4-fold walk-forward 前兩折仍掉到 `test_bal_acc=0.4995/0.5000` 且 `test_positive_rate=0.9938/1.0000`，只有第三折站得住，說明它仍是高上限 cross-asset 候選，但還不是正式新主線。
- [x] 對 `ret_60 + sma_gap_60 + gld_vs_gdx_20` 做 seed 與 walk-forward 驗證，確認 `GDX` 單獨加成是否比 `distance + GDX` 更穩。Performance: seed `1/2/3` 也完全一致，`validation_f1=0.5367`, `validation_bal_acc=0.5458`, `test_f1=0.8134`, `test_bal_acc=0.6000`；walk-forward 同樣在前兩折掉到 `test_bal_acc=0.4964/0.5000`，但第三折 `test_f1=0.7955`, `test_bal_acc=0.5927`，整體比 `distance + GDX` 稍穩、但仍未解決早期 regime 的 all-positive 問題。
- [x] 對 `ret_60 + sma_gap_60 + distance_to_252_high + gld_vs_tlt_20` 做快速複驗，確認 `TLT` 是否只是高 test_f1 偶然值。Performance: seed `1/2/3` 一致，`validation_f1=0.5225`, `validation_bal_acc=0.5242`, `test_f1=0.8261`, `test_bal_acc=0.5951`；雖然 test_f1 是這組裡最高，但 walk-forward 仍有 `test_bal_acc=0.4962/0.4923/0.5864` 的明顯不穩，forward `top 15%/20%` 平均報酬只剩 `3.36%/3.18%`，弱於 `distance + GDX`。

## 二、交易規則最後交叉驗證

- [x] 若 `distance + GDX` 或 `GDX` 單獨加成站得住，補做 `top 15%` 與 `top 20%` 規則比較，確認 cross-asset 改善的是模型面還是交易面。Performance: test 端 `distance + GDX` 的 `top 20%` 最亮眼，`avg_return=11.26%`, `hit_rate=0.7500`, `max_drawdown_compound=-2.75%`；但 walk-forward 則是 `top 15%=4.56%` 優於 `top 20%=3.89%`。`GDX` 單獨加成在 test 也不差，`top 20%=11.06%`, `hit_rate=0.7778`，但 walk-forward 只有 `4.15%`，所以目前交易面仍以 `distance + GDX top 15%` 較值得保留。

---

# 第 16 輪研究任務
## cross-asset 偏差修正

- [x] 對 `ret_60 + sma_gap_60 + gld_vs_gdx_20` 測 `neg_weight=1.15`，確認是否能壓低 early-fold 的 all-positive 偏差。Performance: `validation_f1=0.5360`, `validation_bal_acc=0.5445`, `test_f1=0.8133`, `test_bal_acc=0.5942`, `headline_score=0.6652`。walk-forward 前兩折從原本的 `0.4964/0.5000` 小幅變成 `0.4964/0.5051`，偏差只被輕微壓住，仍不足以升級。
- [x] 對 `ret_60 + sma_gap_60 + distance_to_252_high + gld_vs_gdx_20` 測 `neg_weight=1.15`，確認高上限版本能否在不犧牲太多 test_f1 的情況下提高 walk-forward balance。Performance: `validation_f1=0.5258`, `validation_bal_acc=0.5278`, `test_f1=0.8240`, `test_bal_acc=0.5969`, `headline_score=0.6666`。fold1 的 `test_bal_acc` 從 `0.4995` 小升到 `0.5057`，但 fold2 仍停在 `0.5000`，說明這條線仍是高上限候選，不是已解決偏差的新主線。
- [x] 若 `neg_weight=1.15` 仍不足，再對 `GDX` 單獨版與 `distance + GDX` 版測 `neg_weight=1.30`。Performance: `GDX` 單獨版為 `validation_f1=0.5367`, `validation_bal_acc=0.5458`, `test_f1=0.8120`, `test_bal_acc=0.5930`, `headline_score=0.6646`；`distance + GDX` 則為 `0.5258`, `0.5278`, `0.8244`, `0.5954`, `0.6663`。兩者都沒有比 `1.15` 更好，walk-forward 偏差也沒有明顯再改善，因此 `1.30` 可以停止。

## 規則收斂
- [x] 針對通過 bias 修正後的最佳 `GDX` 版本，比較 `top 15%` / `top 17.5%` / `top 20%` 的 walk-forward 交易摘要。Performance: 以 `distance + GDX + neg_weight=1.15` 當作最佳修正版時，walk-forward `avg_return` 為 `top 15%=4.11%`, `top 17.5%=4.84%`, `top 20%=4.17%`，其中 `top 17.5%` 最佳；若用 `1.30`，則為 `4.29% / 4.91% / 4.13%`，排序仍是 `17.5%` 最好。也就是說，規則面最值得保留的是 `GDX` 線的 `top 17.5%`，但模型面本身仍未通過穩定性檢查。

---

# 第 17 輪研究任務
## cross-asset 新訊號窗格

- [x] 測試 `gld_vs_gdx_60`，確認較長的 cross-asset 相對強弱是否比 `20d` 更不容易在 early folds 崩成 all-positive。Performance: `validation_f1=0.5397`, `validation_bal_acc=0.5660`, `test_f1=0.7937`, `test_bal_acc=0.5741`, `headline_score=0.6542`。walk-forward 前兩折仍是 `test_bal_acc=0.5000/0.5056` 且正類率偏高，說明單獨拉長到 `60d` 並沒有真正修好 regime 問題。
- [x] 測試 `ret_60 + sma_gap_60 + gld_vs_gdx_60`，確認長窗 GDX 單獨加成是否比 `gld_vs_gdx_20` 更穩。Performance: `validation_f1=0.5411`, `validation_bal_acc=0.5611`, `test_f1=0.7889`, `test_bal_acc=0.5892`, `headline_score=0.6567`。雖然 validation 變漂亮，但 test_f1 明顯比 `gld_vs_gdx_20` 線更弱，walk-forward 前兩折也仍接近 `0.4940/0.5069`，不值得升級。
- [x] 測試 `ret_60 + sma_gap_60 + distance_to_252_high + gld_vs_gdx_60`，確認高上限版本是否能保住 test_f1 同時改善 walk-forward balance。Performance: `validation_f1=0.5279`, `validation_bal_acc=0.5435`, `test_f1=0.8134`, `test_bal_acc=0.6000`, `headline_score=0.6653`。這是 `gld_vs_gdx_60` 路線中最強版本，但仍低於 `distance + gdx_20` 的 `0.6678`，而且 walk-forward 前兩折仍停在 `0.4983/0.5000`，所以只算次佳備案。

## 規則延伸
- [x] 若 `gld_vs_gdx_60` 路線站得住，對最佳版本補做 `top 15%` / `top 17.5%` / `top 20%` 規則摘要。Performance: 以 `distance + gdx_60` 為最佳 `60d` 版本時，test 非重疊回測是 `top 15%=11.75%`, `top 17.5%=9.79%`, `top 20%=9.79%`；walk-forward 則是 `4.38% / 4.41% / 3.72%`，因此 `top 17.5%` 小勝 `top 15%`。不過整體仍沒有超過 `distance + gdx_20` 路線。

---

# 第 18 輪研究任務
## 純 GLD 主線收斂

- [x] 測試 `ret_60 + sma_gap_60 + atr_pct_20`，確認較穩的波動狀態特徵是否能正式超過目前 live。Performance: `validation_f1=0.5915`, `validation_bal_acc=0.5525`, `test_f1=0.8096`, `test_bal_acc=0.6028`, `headline_score=0.6782`。balanced accuracy 是三者最佳，且 `top 20%` walk-forward `avg_return=3.77%` 也是最好的規則版本，但整體仍略輸目前 live 的 `0.6784 / 0.8136 / 0.5947`。
- [x] 測試 `ret_60 + sma_gap_60 + up_day_ratio_20`，確認結構型特徵是否比 `distance_to_252_high` 更自然且更穩。Performance: `validation_f1=0.5878`, `validation_bal_acc=0.5433`, `test_f1=0.8116`, `test_bal_acc=0.5962`, `headline_score=0.6754`。這是乾淨的次佳候選，但無論 headline score 或規則摘要都沒有超過 live。
- [x] 測試 `ret_60 + sma_gap_60 + close_location_20`，重新確認先前 validation 很亮但 test 較弱的路線，在純 GLD 正式流程下是否還值得保留。Performance: `validation_f1=0.6010`, `validation_bal_acc=0.5696` 很亮眼，但 `test_f1=0.7886`, `test_bal_acc=0.5765`, `headline_score=0.6655` 明顯退步，仍屬 validation 型強者。

## 規則延伸
- [x] 對第 18 輪表現最好的純 GLD 候選，補做 `top 15%` / `top 17.5%` / `top 20%` walk-forward 比較。Performance: 以 `ret_60 + sma_gap_60 + atr_pct_20` 為最佳候選時，walk-forward `avg_return` 為 `top 15%=3.50%`, `top 17.5%=3.58%`, `top 20%=3.77%`。規則面最佳是 `top 20%`，但仍只小幅優於 live 的 `top 15%=3.44%`，不足以支撐模型升級。
# 第 19 輪研究任務
## 3 桶報酬分桶首輪

- [x] 建立 `60d forward return` 的 3 桶標記：`up >= +6%`、`flat between -4% and +6%`、`down <= -4%`，先統計 train / validation / test 三段各桶樣本數與比例。Performance: train 為 `down/flat/up = 811/1125/1004`，validation 為 `187/266/177`，test 則變成 `68/166/396`。test 的 `up` 比例拉到 `62.86%`，明顯高於 train 的 `34.15%`，3 桶同樣存在 regime shift。
- [x] 以目前 live 特徵組 `ret_60 + sma_gap_60` 訓練 3 桶版本，檢查 validation / test 的 `macro_f1`、`balanced_accuracy` 與各桶 confusion matrix。Performance: baseline 的 `validation_macro_f1=0.3039`, `validation_bal_acc=0.3149`, `test_macro_f1=0.2998`, `test_bal_acc=0.3204`。test confusion matrix 為 `[[17,37,14],[46,56,64],[113,135,148]]`，能學到一點層次，但距離可交易還很遠。
- [x] 在 3 桶版本上加入 `atr_pct_20`，確認波動狀態特徵是否比 binary 分類時更有幫助。Performance: `validation_macro_f1=0.2995`, `validation_bal_acc=0.3122`, `test_macro_f1=0.2971`, `test_bal_acc=0.3078`，沒有比 baseline 更好。
- [x] 在 3 桶版本上加入 `up_day_ratio_20`，確認結構型特徵是否能改善 `up / flat / down` 的分辨。Performance: `validation_macro_f1=0.3078` 小升，但 `test_macro_f1=0.2809`, `test_bal_acc=0.2997` 明顯更差，泛化不成立。
- [x] 在 3 桶版本上加入 `close_location_20`，確認區間位置特徵是否能提升 `flat` 與趨勢類別的切分。Performance: `validation_macro_f1=0.3054`, `validation_bal_acc=0.3162` 是 validation 最佳，但 `test_macro_f1=0.2972`, `test_bal_acc=0.3175` 仍略輸 baseline。

## 與 binary live 對照

- [x] 比較 3 桶 baseline 與目前 binary live 在最近 5 年的訊號密度與 forward return 摘要，確認 3 桶是否只是更細，還是真的更有交易解讀價值。Performance: binary live 在最近 5 年的正向訊號密度為 `89.43%`，平均 forward return `6.02%`；3 桶 baseline 則切成 `down/flat/up = 26.38%/32.81%/40.81%`，平均 forward return 分別為 `5.38%/4.79%/6.00%`。3 桶有把訊號拆細，但還沒有帶來比 binary 更清楚的交易分級。
- [x] 檢查 `predicted up / flat / down` 三組的平均報酬、命中率與最大回撤，確認三桶輸出是否具有清楚層次。Performance: 在 test split 上，baseline 預測 `up` 的平均報酬 `9.80%`、命中率 `86.28%`，優於 `flat` 的 `6.66% / 75.00%`；但 `down` 仍有 `8.65% / 82.39%`，排序沒有乾淨拉開。結論是 3 桶目前只能算研究輔助，不適合取代 binary live。

---

# 第 20 輪研究任務
## 3 桶標記再設計

- [ ] 將 3 桶邊界改成更保守版本，至少比較 `up >= +8% / down <= -4%` 與 `up >= +8% / down <= -6%`，確認是否能降低 `up` 桶在 test 過度膨脹的 regime shift。Performance:
- [ ] 以目前 3 桶 baseline `ret_60 + sma_gap_60` 在新邊界下重跑，檢查 `macro_f1`、`balanced_accuracy` 與 confusion matrix 是否比首輪更乾淨。Performance:

## 3 桶 regime 檢查

- [ ] 以 `above_200dma_flag` 將 3 桶資料切成兩段，先統計各 regime 的桶分布與 forward return，確認問題是否主要來自多頭年份堆積。Performance:
- [ ] 若 regime 分布差異明顯，對 `above_200dma=1/0` 各自跑 baseline 3 桶版本，確認簡單 regime-aware 分模是否比單一 3 桶模型更穩。Performance:

## 純 GLD 主線補充

- [ ] 重新檢查 `ret_60 + sma_gap_60 + rolling_vol_60`，確認它在純 GLD 正式 cohort 上較高的 `test_f1/test_bal_acc` 是否值得進入主線候選。Performance:
# 第 21 輪研究任務
## 3 桶結論

- [x] 對 3 桶做最後一輪驗證，包含 `up >= +8% / down <= -4%`、`up >= +8% / down <= -6%` 兩組更保守邊界，以及 `above_200dma` 的簡單 regime-aware 分模。Performance: `up8_down4` 的 `test_macro_f1=0.2124`, `test_bal_acc=0.3085`；`up8_down6` 也只有 `0.2194 / 0.3423`。`above_200dma` 分模後 `test_macro_f1=0.3109`, `test_bal_acc=0.3207`，仍未實質改善。結論：3 桶支線停止，不再列入後續正式 backlog。

## 純 GLD 主線延伸

- [x] 正式測試 `ret_60 + sma_gap_60 + rolling_vol_60`，確認它在純 GLD cohort 上較高的 `test_f1/test_bal_acc` 是否能站住。Performance: `validation_f1=0.5801`, `validation_bal_acc=0.5263`, `test_f1=0.8154`, `test_bal_acc=0.6048`, `headline_score=0.6762`。它在 test 面確實比 live 更好，但 validation 明顯較弱，因此目前只能算純 GLD 主線候選，不直接升級。
- [x] 若 `rolling_vol_60` 站得住，補做 `top 15% / top 17.5% / top 20%` walk-forward 規則比較，確認它提升的是模型面還是交易面。Performance: `rolling_vol_60` 的 walk-forward `avg_return` 為 `top 15%=4.66%`, `top 17.5%=4.41%`, `top 20%=4.82%`，全部高於 live 的 `3.44% / 3.16% / 3.23%`。交易面最亮的是 `top 20%`，這條線值得保留到下一輪。
# 第 22 輪研究任務
## ranking 首輪

- [x] 建立 `future_return_60` ranking target，先統計 train / validation / test 的報酬分布、分位數與年份差異。Performance: train / validation / test 的平均 `future_return_60` 為 `2.20% / 1.16% / 8.34%`，test `p90=19.66%` 明顯高於 train `13.58%`。ranking 目標同樣受到近期多頭 regime 影響。
- [x] 以目前 live 特徵組 `ret_60 + sma_gap_60` 訓練 ranking baseline，使用預測的 `future_return_60` 作為排序分數。Performance: baseline 的 `validation_spearman=0.0634`, `test_spearman=0.0333` 很弱；但 `top 15%` walk-forward `avg_return=4.55%`，已高於 binary live 的 `3.44%`。這條線交易面有潛力，但排序品質還不乾淨。
- [x] 在 ranking baseline 上加入 `atr_pct_20`，確認波動狀態特徵是否能提升 top-percentile 排序品質。Performance: `validation_spearman=0.1439` 最好，但 `test_spearman=-0.0322` 反向，`top 10%` walk-forward `avg_return=4.98%` 雖亮眼，但 `top 15%/20%` 退步，整體不穩。
- [x] 在 ranking baseline 上加入 `rolling_vol_60`，確認它是否比 `atr_pct_20` 更適合 ranking 目標。Performance: `validation_spearman=0.1043`, `test_spearman=0.0473` 是三者最佳；`top 20%` walk-forward `avg_return=4.76%` 也優於 binary live。這是目前最值得繼續追的 ranking 候選。

## 與 binary live 對照

- [x] 比較 ranking baseline 與 binary live 在 `top 10% / 15% / 20%` 的 test 非重疊回測。Performance: test 端 binary live 的 `top 15%` 為 `avg_return=8.93%`, `hit_rate=71.43%`；ranking baseline 的 `top 10%/15%/20%` 為 `7.41% / 6.54% / 6.32%`，不如 binary。單看 test，ranking 並沒有贏。
- [x] 比較 ranking baseline 與 binary live 在 `top 10% / 15% / 20%` 的 walk-forward 平均報酬、命中率與最大回撤。Performance: walk-forward 上反而是 ranking 佔優。binary live 為 `3.84% / 3.44% / 3.23%`；ranking baseline 為 `3.99% / 4.55% / 3.90%`；`ranking + rolling_vol_60` 更進一步到 `3.38% / 3.54% / 4.76%`。目前 ranking 的優勢主要出現在 walk-forward 交易面，不是 test 單點。
- [x] 檢查 ranking 分數分位數是否有 forward return 單調性，確認 top decile 是否明顯優於中位數區間。Performance: 三個 ranking 版本的 decile 都沒有乾淨單調。`ranking baseline` 的第 `5` 分位平均報酬 `11.64%` 反而高於第 `10` 分位 `8.38%`；`ranking + rolling_vol_60` 也在第 `6` 分位 `10.93%` 高於第 `10` 分位 `8.07%`。結論是排序規則已有交易價值，但分數本身還沒形成漂亮的單調結構。

---

# 第 23 輪研究任務
## ranking 主線收斂

- [ ] 以 `ret_60 + sma_gap_60 + rolling_vol_60` 為 ranking 主候選，補做更細的 `top 12.5% / 15% / 17.5% / 20%` walk-forward 比較，確認最佳交易密度。Performance:
- [ ] 在 ranking 主候選上加入 `atr_pct_20` 的小範圍組合複驗，確認 `top 10%` 優勢是否能在較高密度規則下延續。Performance:
- [ ] 比較 ranking 主候選與 `rolling_vol_60` binary 候選在最近 5 年的訊號密度、平均報酬與最大回撤，決定下一步該優先推哪條主線。Performance:
# 第 24 輪研究任務
## 第 23 輪結論

- [x] `ranking + rolling_vol_60` 的最佳密度是 `top 17.5%`，walk-forward `avg_return=4.91%`，略高於 `top 20%` 的 `4.76%`。但最近 5 年對照下，binary `rolling_vol_60` 在 `top 12.5%/17.5%/20%` 仍整體較強，只有 `top 15%` 這一點 ranking 稍微領先。結論：下一輪先優先推 binary `rolling_vol_60`，ranking 暫列次要候選。

## pure GLD binary 收斂

- [ ] 將 `ret_60 + sma_gap_60 + rolling_vol_60` 當主候選，正式比較 `top 12.5% / 15% / 17.5% / 20%` 的 test 與 walk-forward，確認最佳交易密度。Performance:
- [ ] 對 `ret_60 + sma_gap_60 + rolling_vol_60` 做 seed 與 walk-forward 複驗，確認它是否真能取代目前 live。Performance:

## ranking 暫存複驗

- [ ] 若 binary `rolling_vol_60` 沒有順利升級，再對 `ranking + rolling_vol_60` 做一次分數校準或去極端值處理，檢查是否能改善 decile 單調性。Performance:
# 第 25 輪研究任務
## 第 24 輪結論

- [x] `ret_60 + sma_gap_60 + rolling_vol_60` 在 seed `1/2/3` 完全一致，`validation_f1=0.5801`, `validation_bal_acc=0.5263`, `test_f1=0.8154`, `test_bal_acc=0.6048`。兩折 walk-forward 為 `test_f1=0.6049/0.7551`, `test_bal_acc=0.5182/0.5523`，平衡度整體優於目前 live，但 headline score 仍略低，因此目前維持 candidate，不直接升成 live。
- [x] binary `rolling_vol_60` 的最佳交易密度是 `top 20%`，test `avg_return=10.54%`, `hit_rate=77.78%`，walk-forward `avg_return=4.82%`，全面優於 live 的 `top 20%` (`8.38%`, `71.43%`, `3.23%`)。這條線目前最像「交易規則升級」，而不是 threshold/live 模型升級。
- [x] ranking `rolling_vol_60` 的最佳密度是 `top 17.5%`，walk-forward `avg_return=4.91%`。但最近 5 年直接對照下，binary `rolling_vol_60` 在 `top 12.5% / 17.5% / 20%` 仍較強，所以 ranking 暫列次要候選。

## binary 主線最後收斂

- [ ] 比較 `ret_60 + sma_gap_60 + rolling_vol_60` 的 `threshold` 訊號與 `top 20%` 規則，確認是否應把「正式 live 模型」與「正式 live 交易規則」分開管理。Performance:
- [ ] 若 `top 20%` 明顯優於 threshold，設計一個不改模型、只改 live 解讀的摘要方案，讓圖表與即時輸出能區分「模型分數」與「實際採用規則」。Performance:

## ranking 次線

- [ ] 若 binary 主線確認不升級 threshold 版本，再對 `ranking + rolling_vol_60` 做簡單分數校準或 winsorize，檢查 decile 單調性是否能改善。Performance:
# 第 26 輪研究任務
## 第 25 輪結果

- [x] 比較 `ret_60 + sma_gap_60 + rolling_vol_60` 的 `threshold` 與 `top 20%` 規則。Performance: candidate 模型本身仍是 `validation_f1=0.5801`, `validation_bal_acc=0.5263`, `test_f1=0.8154`, `test_bal_acc=0.6048`, `headline_score=0.6762`；但規則比較已經很明確，`top 20%` 在 test `avg_return=10.54%`, `hit_rate=77.78%`、walk-forward `avg_return=4.82%`、最近 5 年 `avg_return=5.99%`, `max_drawdown=-11.22%`，都優於同模型 threshold 的 `8.07%`, `72.73%`, `3.22%`, `5.62%`, `-15.45%`
- [x] 將 live 輸出拆成模型訊號與規則摘要。Performance: `predict_latest.py` 現在同時輸出 `model_signal_summary` 與 `rule_summary`；`chart_signals.py` 保留原本顏色代表模型 signal，但最近 5 天卡片與 tooltip 會額外顯示是否落在歷史 `top 20%` 規則內。最新 `2026-03-27` 訊號是 `bullish`，但 `top 20%` 參考規則為 `false`

## 決策收斂

- [ ] 正式決定是否把「live 模型」與「adopted trading rule」分開管理；若分開，需定義各自的命名與輸出欄位。Performance:
- [ ] 若決定分開管理，補一輪最近 30/60 個交易日對照，檢查當前 `live` threshold 與 `rolling_vol_60 top 20%` 的訊號重疊度與差異天數。Performance:
- [ ] 若決定不分開管理，則停止 `rolling_vol_60` 規則線，回到目前 `live` binary 路徑並只保留研究紀錄。Performance:

---

# 第 27 輪研究任務
## 第 26 輪結果

- [x] ranking 線正式停止。Performance: ranking 只在少數密度下有局部優勢，但整體排序穩定性、分位數單調性與最近 5 年表現都不如 binary 主線，因此從正式 backlog 與 README 主流程移除，只保留歷史研究紀錄

## binary 主線

- [ ] 正式決定是否把「live 模型」與「adopted trading rule」分開管理；若分開，需定義各自的命名與輸出欄位。Performance:
- [ ] 若決定分開管理，補一輪最近 30/60 個交易日對照，檢查當前 `live` threshold 與 `rolling_vol_60 top 20%` 的訊號重疊度與差異天數。Performance:
- [ ] 若決定不分開管理，則停止 `rolling_vol_60` 規則線，回到目前 `live` binary 路徑並只保留研究紀錄。Performance:

---

# 第 28 輪研究任務
## 第 27 輪結果

- [x] 完成第一輪對稱 exit/risk-off 研究。Performance: 以 `60d / -8% before +4% / drop-neutral` 定義 exit target 後，train / validation / test 的 exit 正類率為 `22.61% / 24.23% / 4.22%`，recent test 幾乎沒有 exit 樣本；baseline `validation_f1=0.3926`, `test_f1=0.0800`, `test_bal_acc=0.4943`，加入 `ret_60+sma_gap_60` 與 `rolling_vol_60` 都沒有改善，說明目前這個對稱 exit label 幾乎完全被 regime shift 壓垮

## binary 主線

- [ ] 正式決定是否把「live 模型」與「adopted trading rule」分開管理；若分開，需定義各自的命名與輸出欄位。Performance:
- [ ] 若決定分開管理，補一輪最近 30/60 個交易日對照，檢查當前 `live` threshold 與 `rolling_vol_60 top 20%` 的訊號重疊度與差異天數。Performance:
- [ ] 若決定不分開管理，則停止 `rolling_vol_60` 規則線，回到目前 `live` binary 路徑並只保留研究紀錄。Performance:

## exit 後續方向

- [ ] 若要繼續做 exit，改成更實用的風控定義再試一次，例如未來 `60d` 最大回撤是否超過 `-7%`，而不是對稱的 `-8% before +4%` barrier。Performance:
- [ ] 若要繼續做 exit，先統計最近 10 年與最近 5 年的 exit label 分布，確認是不是近年多頭 regime 讓對稱 exit target 幾乎失去樣本。Performance:

---

# 第 29 輪研究任務
## binary 主線決策

- [x] 正式決定是否把「live 模型」與「adopted trading rule」分開管理。Performance: 正式分開管理。`ret_60 + sma_gap_60` 仍保留為 GLD 的 live model，因為它的 `headline_score=0.6784` 仍是目前最穩的主線；但實際採用的交易規則改以 `ret_60 + sma_gap_60 + rolling_vol_60` 的 `top 20%` 作為 adopted trading rule，因為它在 test `avg_return=10.54%`, `hit_rate=77.78%`、walk-forward `avg_return=4.82%`、最近 5 年 `avg_return=5.99%`, `max_drawdown=-11.22%` 都明顯優於同模型 threshold。這代表 GLD 之後應明確分成「模型分數參考」與「實際採用規則」兩層，而不是再試圖把兩者硬壓成同一條 live 線。
## Round 30 Operator Breakthrough Check

- [x] Compare the new context-stack percentile rules directly against the current GLD live threshold line and the `rolling_vol_60 + top 20%` operator path. Performance: the context stack itself stayed strong at `validation_f1=0.5919`, `test_f1=0.8147`, and `test_bal_acc=0.6154`. More importantly, `top 7.5%` emerged as the cleanest rule-level follow-up with `hit_rate=85.71%`, `avg_return=10.61%`, and `max_drawdown_compound=-1.60%` on the static test split. That makes it slightly cleaner than the older `rolling_vol_60 top 20%` route and materially cleaner than the threshold live rule on drawdown, even though the underlying model still needs rolling-validation proof before it can displace the documented live default.
## Round 31 Live Candidate Wiring

- [x] Wire the GLD context-stack candidate into the live output configuration without changing the final execution gate yet. Performance: `assets/gld/config.json` now points live scoring at the context-stack feature set and uses `top 7.5%` as the live reference percentile. `predict_latest.py` and `chart_signals.py` now render that percentile dynamically, so the live payload and chart no longer hardcode `top 20%`. A fresh `AR_ASSET=gld python predict_latest.py` run confirmed the new live metadata with `reference_percentile_rule=top_7.5pct`, while the current latest row `2026-04-01` still stayed below the stronger percentile cutoff.

## Round 32 Active Status Alignment

- [x] Carry the GLD context-stack candidate through the monitor layer as well. Performance: `refresh_active_status.py` now labels the preferred GLD lane as `context_stack_live`, derives the usage note from live payload metadata, and keeps the reference rule text aligned with `top_7.5pct`. A fresh `AR_ASSET=gld python refresh_active_status.py` plus `refresh_monitor_snapshot.py` run now produces `preferred_line=context_stack_live` and `action=selected_now`, so the active-status board, monitor snapshot, latest payload, and chart all describe the same breakthrough line.

## Round 33 Adoption Compare

- [x] Run a formal side-by-side compare between the current GLD context-stack threshold line, the new `top 7.5%` reference operator, and the older `rolling_vol_60 top 20%` path. Performance: `assets/gld/operator_adoption_compare.tsv` confirmed that the decision is close but not ambiguous. The old `rolling_vol_60 top_20pct` path still leads on forward activity and forward average return with `30` trades at `5.17%`, while the context-stack `top_7_5pct` remains the cleaner selective rule on the static split with `85.71%` hit rate, `10.61%` average return, and only `-1.60%` compound drawdown. Recent live-like rows in `assets/gld/operator_recent_compare_summary.tsv` also showed that the context-stack percentile is much quieter right now, with only `3` selections in the latest `60` rows versus `5` for the older `top_20pct` path. So the current best GLD framing is: keep the context stack as the cleaner reference operator, but do not yet replace the older adopted-style `rolling_vol_60 top 20%` route on forward evidence alone.

## Round 34 Trade Divergence Check

- [x] Compare the actual date-level divergence between `context_stack top_7_5pct` and `rolling_vol_60 top_20pct` instead of only comparing aggregate metrics. Performance: `assets/gld/operator_trade_divergence_summary.tsv` showed that the context-stack percentile had only `8` context-only dates across the whole saved test window, but those were exceptionally strong with `100%` hit rate and `12.97%` average forward return. The shared dates were also very strong at `92.5%` hit rate and `8.20%` average forward return. The old `rolling_vol_60 top_20pct` path still had the broader footprint with `86` rule-only dates averaging `8.64%` and, importantly, it remained the only line with extra signals in the latest `60` rows: `assets/gld/operator_recent_divergence_summary.tsv` showed `0` recent context-only dates versus `2` recent rolling-vol-only dates (`2026-03-24` and `2026-03-26`). That means the new context operator really is cleaner on its own picks, but the older route is still the one carrying more recent live-like activity.

## Round 35 Context Ablation On Recent Misses

- [x] Test whether the recent `rv_only` misses are caused more by `trend_quality_20` or by `atr_pct_20_percentile` inside the GLD context stack. Performance: `assets/gld/operator_context_ablation.tsv` showed that dropping `trend_quality_20` barely changed the outcome, but dropping `atr_pct_20_percentile` was more interesting. The `context_no_atr top_7_5pct` variant still stayed close to the full context stack on core quality with `validation_f1=0.5895`, `test_f1=0.8118`, `test_bal_acc=0.6145`, and the same `-1.60%` test drawdown, while it improved test average return to `11.79%` and newly captured the missed `2026-03-24` date. It still did not capture `2026-03-26`, and its forward average return stayed slightly below the full stack, so this is not an adoption change yet. But it is the clearest new GLD follow-up candidate from this round.

## Round 36 XGBoost Prototype Check

- [x] Run a minimal XGBoost prototype on the same GLD context-stack feature set before spending more time on tree models. Performance: the first prototype was clearly weaker than the current logistic baseline. On the static split, the XGBoost line dropped to `validation_f1=0.5330`, `validation_bal_acc=0.4784`, `test_f1=0.7844`, and `test_bal_acc=0.5665`. Using the same `top 7.5%` selective rule, it reached only `71.43%` hit rate and `5.86%` average return on the test split, versus the logistic context stack at `85.71%` and `10.61%`. The forward compare was also worse at `4.11%` average return over `22` trades versus `4.87%` over `23`. So XGBoost is not the next breakthrough path for GLD in its current minimal form.

## Round 37 Context-No-ATR Adoption Compare

- [x] Promote `context_no_atr top_7.5pct` into the same formal compare used for the main GLD operator decision. Performance: `assets/gld/operator_adoption_compare_round37.tsv` showed that the no-ATR variant did improve its standing, but not enough to win adoption yet. It kept `validation_f1=0.5895`, `test_f1=0.8118`, and `test_bal_acc=0.6145`, while producing the strongest static test average return at `11.79%` with the same `-1.60%` drawdown as the full context stack. It also became a little less dormant in recent data, with `4` selections in the latest `60` rows versus `3` for the full context line. But the full context line still led on forward average return at `4.87%` versus `4.53%`, and the old `rolling_vol_60 top_20pct` path still led on forward activity and recency with `30` trades and `5` recent selections. So the breakthrough here is partial: `context_no_atr top_7.5pct` is now a stronger promotion candidate, but it is not yet the new adopted operator.

## Round 38 Recent Extra-Signal Check

- [x] Inspect the exact recent signal that `context_no_atr top_7.5pct` adds beyond the full context line. Performance: `assets/gld/operator_recent_compare_round38.tsv` and `assets/gld/operator_recent_no_atr_extra_signals.tsv` showed that there was exactly one extra recent selection in the latest `60` rows, on `2026-03-24`. That trade was not a low-quality loosened cutoff: it overlapped with the older `rolling_vol_60 top_20pct` operator and carried `future_return_60=8.34%`. The full context line missed it by a narrow probability gap of `-0.0030` versus its cutoff, while the no-ATR variant cleared its own cutoff by `+0.0005`. This gives the no-ATR line its first clear recent live-like advantage, even though the broader adoption decision still remains open.
