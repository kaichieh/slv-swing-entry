# VIX Monitor Board Experiment Report

## Summary

This experiment tested whether adding a shared VIX feature pack helps the current `monitor_board` asset set.

> Later GLD-only follow-up superseded the initial GLD interpretation in this report.
> The early shared daily-VIX pack looked positive for GLD in this coarse board-wide screen, but deeper GLD-specific follow-up did not find a surviving VIX-driven core replacement model. The only GLD+VIX path that remained justified was a VIX/VIX3M term-panic overlay line.

- Scope: all 9 board assets (`gld`, `slv`, `iwm`, `spy`, `tlt`, `xle`, `nvda`, `qqq`, `tsla`)
- Strategy shape: add VIX as a shared feature source, not as a new board renderer rule
- VIX pack: `vix_close_lag1`, `vix_change_1`, `vix_change_5`, `vix_z_20`, `vix_percentile_20`, `vix_high_regime_flag`
- Data source: FRED `VIXCLS` daily close, cached locally for reproducible runs

## Method

### What changed

- Added VIX download/normalize/merge/feature engineering in `prepare.py`
- Plumbed VIX into binary live consumers and regression consumers
- Extended hard-gate live-family experiments so GLD and SLV can also accept selected VIX features during evaluation

### How assets were evaluated

- **Binary assets** (`gld`, `slv`, `iwm`, `spy`, `nvda`, `tsla`): compared baseline vs `baseline + VIX pack` using the asset’s current live family and looked mainly at out-of-sample **test top-rule average return**, **test top-rule hit rate**, and **test balanced accuracy**
- **Regression assets** (`qqq`, `tlt`, `xle`): compared baseline vs `baseline + VIX pack` using **test bottom-15% bucket average return**, **test bottom-15% hit rate**, and **walk-forward average test bucket return**

Raw experiment output was saved to `.sisyphus/vix_experiment_results.json`.

## Results

### Binary assets

| Asset | Result | Key takeaways |
|---|---|---|
| GLD | Early positive, later superseded | This board-wide daily-VIX pack improved GLD here, but later GLD-specific follow-up did **not** confirm a surviving VIX-driven core replacement model |
| SLV | Negative | Test top-rule avg return dropped from **0.3531** to **0.2084** (`-0.1447`), hit rate fell from **1.00** to **0.75**, balance unchanged |
| IWM | Mild positive | Test top-rule avg return rose from **0.0433** to **0.0445** (`+0.0011`), test balanced accuracy improved from **0.5378** to **0.5678** |
| SPY | Mixed / weak | Avg return improved from **0.0238** to **0.0327**, but hit rate fell and balanced accuracy slipped slightly |
| NVDA | Neutral to negative | Avg return fell from **0.1772** to **0.1740**, hit rate unchanged, balanced accuracy unchanged at **0.5000** |
| TSLA | Positive but riskier | Avg return improved strongly from **0.0864** to **0.1810** (`+0.0946`) and hit rate rose from **0.50** to **0.75**, but balanced accuracy fell from **0.7640** to **0.7422** |

### Regression assets

| Asset | Result | Key takeaways |
|---|---|---|
| QQQ | Negative | Test bottom-15% avg return fell from **0.0518** to **0.0491**, and walk-forward avg test bucket return fell from **0.0700** to **0.0499** |
| TLT | Mixed / weak | Static test bottom-15% avg return improved from **-0.0053** to **0.0015**, but walk-forward avg test bucket return worsened from **0.00015** to **-0.00319** |
| XLE | Positive | Test bottom-15% avg return improved from **0.0363** to **0.0450**, hit rate improved from **0.5613** to **0.6387**, and walk-forward avg test bucket return improved from **0.0341** to **0.0523** |

## Interpretation

### Clear wins

- **GLD (early board-wide result only)**: the first shared daily-VIX pack improved GLD in this screen, but later GLD-only research superseded that interpretation
- **TSLA**: strongest binary return improvement, though with a slight balance trade-off
- **XLE**: cleanest regression improvement because both static and walk-forward metrics improved

### Weak or mixed cases

- **IWM**: slight improvement, probably worth keeping as a research-side enhancement rather than immediate promotion
- **SPY**: return improved but quality metrics did not clearly improve; not a convincing upgrade
- **TLT**: test-period result improved, but walk-forward degraded; not stable enough yet

### Clear losers

- **SLV**: VIX degraded the current hard-gate path materially on return and hit rate
- **QQQ**: VIX hurt both static and walk-forward return quality
- **NVDA**: essentially flat to slightly worse

## Recommendation

### Promote / keep for deeper validation

- **XLE**

### Positive, but validate more before any live promotion

- **TSLA**

### Keep as research-only for now

- **IWM**
- **SPY**
- **TLT**

### Reject for current live direction

- **SLV**
- **QQQ**
- **NVDA**

## Caveats

1. This was a **feature-source experiment**, not a full retune of every custom winner script.
2. Binary evaluation used each asset’s current live family with static out-of-sample test comparisons; regression evaluation also included walk-forward checks.
3. VIX came from daily close data, so this experiment is appropriate for the repo’s daily-bar workflow, not intraday inference.
4. The strongest future extension is not “more raw VIX,” but selective follow-up on winners: VIX as gate/regime input for GLD/TSLA/XLE-style candidates.
5. This was a 9-asset screening pass, so mild positives should be treated as decision-quality signals rather than proof of a generalized VIX edge.

## Bottom line

Adding VIX **did help some monitor-board assets, but not the board as a whole**.

For **GLD specifically**, this report should now be read as historical context only: the later GLD-only follow-up replaced the original daily-VIX interpretation with a narrower conclusion — keep the non-VIX mixed core model, and only adopt a VIX/VIX3M term-panic overlay at runtime.

The best evidence supports **asset-specific adoption**, not a blanket rollout:

- Adopt or deepen validation on **XLE**
- Keep **TSLA** as a strong follow-up candidate, but validate more before any live promotion
- Keep **IWM**, **SPY**, and **TLT** in research mode
- Do not roll VIX into **SLV**, **QQQ**, or **NVDA** in the current form
