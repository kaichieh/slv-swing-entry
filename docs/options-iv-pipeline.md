# Options IV Pipeline Skeleton

This repo currently works from spot OHLCV plus macro-volatility context such as `VIX` and `VIX3M`. It does not yet ingest a single-stock options chain. This document defines the smallest data contract and script flow needed to add per-asset implied volatility support.

## Goal

Compute a practical per-asset `30D ATM IV` summary from an options chain file and write the result into the asset cache directory.

Current script:

- `refresh_options_chain.py`
- `options_iv.py`

Default paths:

- input: `.cache/<asset>-swing-entry/<asset>_options_chain.csv`
- output: `.cache/<asset>-swing-entry/options_iv_summary.json`
- history: `assets/<asset>/options_iv_history.csv`

The script uses `AR_ASSET` in the same way as the rest of the repo.

## Minimum Input Schema

Required fields, with accepted aliases:

| Canonical field | Accepted aliases |
|---|---|
| `asof_date` | `asof_date`, `quote_date`, `date`, `timestamp` |
| `underlying` | `underlying`, `symbol`, `ticker`, `root` |
| `spot` | `spot`, `underlying_price`, `underlier_price`, `stock_price`, `close` |
| `expiry` | `expiry`, `expiration`, `expiration_date`, `expiry_date`, `maturity` |
| `strike` | `strike`, `strike_price`, `exercise_price` |
| `option_type` | `option_type`, `call_put`, `cp`, `right`, `type`, `side` |

Optional liquidity and pricing fields:

| Canonical field | Accepted aliases |
|---|---|
| `bid` | `bid`, `bid_price` |
| `ask` | `ask`, `ask_price` |
| `mark` | `mark`, `mid`, `mid_price`, `mark_price` |
| `last` | `last`, `last_price`, `trade_price`, `premium` |
| `open_interest` | `open_interest`, `oi` |
| `volume` | `volume`, `contract_volume` |
| `rate` | `rate`, `risk_free_rate`, `rf_rate` |

Price selection priority:

1. use `mid = (bid + ask) / 2`
2. otherwise use `mark`
3. otherwise use `last`

## Sample CSV

```csv
quote_date,ticker,underlying_price,expiration_date,strike_price,right,bid_price,ask_price,contract_volume,oi
2026-04-20,NVDA,101.25,2026-05-16,100,C,4.95,5.15,850,4200
2026-04-20,NVDA,101.25,2026-05-16,100,P,4.60,4.85,910,3900
2026-04-20,NVDA,101.25,2026-06-20,100,C,6.85,7.10,530,2500
2026-04-20,NVDA,101.25,2026-06-20,100,P,6.55,6.80,600,2100
```

## What The Script Does

`refresh_options_chain.py`:

1. Query Yahoo's options endpoint for the asset symbol.
2. Read the available expiration dates.
3. Keep near-term expiries in the practical `7` to `60` day window.
4. Download calls and puts for those expiries.
5. Save a normalized chain CSV into the asset cache directory.

`options_iv.py`:

1. Load the raw chain file from the asset cache directory.
2. Normalize common provider column names to one canonical schema.
3. Filter to usable expiries in a configurable practical window, currently `7` to `60` trading days.
4. Pick the most ATM call and put for each expiry.
5. Back out Black-Scholes implied volatility from each selected quote.
6. Build a per-expiry ATM IV summary.
7. Interpolate to a target `30` trading day ATM IV when two surrounding expiries exist.
8. Write the summary JSON back into the cache directory.
9. Append a one-row snapshot into `assets/<asset>/options_iv_history.csv` for later feature engineering.

## Output Shape

`options_iv_summary.json` includes:

- `asof_date`
- `underlying`
- `spot`
- `input_rows`
- `usable_expiries`
- `target_30d_atm_iv`
- `interpolation`
- `expiry_summaries`

`options_iv_history.csv` includes one row per as-of date:

- `date`
- `underlying`
- `spot`
- `target_30d_atm_iv`
- `interpolation_method`
- `usable_expiries`
- `near_expiry_days`
- `near_expiry_iv`
- `far_expiry_days`
- `far_expiry_iv`

This keeps the first integration small. Once a real chain source is stable, the next extensions would be:

- `IV Rank`
- term structure features such as `atm_iv_30`, `atm_iv_60`, `atm_iv_30_60_ratio`
- skew features using OTM put vs OTM call IV
- event-aware handling for earnings weeks

## Run

```powershell
$env:AR_ASSET="nvda"
C:\Python313\python.exe .\refresh_options_chain.py
C:\Python313\python.exe .\options_iv.py
```

If the input chain file is missing, the script will fail fast so the missing feed is obvious.

## Prepare.py Integration

`prepare.py` now supports optional options-IV-derived experimental features when `AR_EXTRA_BASE_FEATURES` includes any of:

- `options_iv_30`
- `options_iv_30_change_1`
- `options_iv_30_z_20`
- `options_iv_30_percentile_20`
- `options_iv_30_iv_rank_126`
- `options_iv_30_iv_rank_252`
- `options_iv_30_high_regime_flag`

These are built from the lagged `options_iv_history.csv` series so the feature alignment matches the repo's existing anti-lookahead pattern.

`options_iv_30_iv_rank_252` is the classic rolling one-year IV Rank style feature:

\[
\frac{IV_{now} - IV_{rolling\ min}}{IV_{rolling\ max} - IV_{rolling\ min}}
\]

and `options_iv_30_iv_rank_126` is the same idea on a shorter half-year lookback.
