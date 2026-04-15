# Wire New Strategies Into Monitoring Board Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make SLV, NVDA, and TSLA use the newly chosen preferred strategies so `refresh_active_status.py`, `refresh_monitor_snapshot.py`, and the monitoring board all reflect the new defaults.

**Architecture:** Keep the existing pipeline intact: `refresh_active_status.py` chooses the preferred line, `refresh_monitor_snapshot.py` derives board action from that preferred row, and `refresh_reports.py` republishes tracked artifacts. The change should make the preferred-line choice explicit and testable for SLV, NVDA, and TSLA without redesigning the snapshot or board layers.

**Tech Stack:** Python, pandas, unittest, TSV/JSON-generated reporting

---

## File Structure

- **Modify:** `refresh_active_status.py`
  - Wire the chosen preferred/live lines for SLV, NVDA, and TSLA.
- **Modify:** `tests/test_refresh_active_status_gld.py`
  - Add SLV-focused preferred-line tests here only if the existing file is already the repo’s “builder-style” test home; otherwise prefer a new focused test file.
- **Modify:** `tests/test_refresh_active_status_tsla.py`
  - Extend coverage for the TSLA adopted XGBoost line if needed.
- **Create:** `tests/test_refresh_active_status_slv_nvda.py`
  - Focused tests for SLV and NVDA preferred-line wiring.
- **Modify:** tracked generated artifacts after refresh:
  - `assets/slv/active_status_summary.tsv`
  - `assets/slv/active_status.html`
  - `assets/slv/monitor_snapshot.tsv`
  - `assets/nvda/active_status_summary.tsv`
  - `assets/nvda/active_status.html`
  - `assets/nvda/monitor_snapshot.tsv`
  - `assets/tsla/active_status_summary.tsv`
  - `assets/tsla/active_status.html`
  - `assets/tsla/monitor_snapshot.tsv`
  - `monitor_board.tsv`
  - `monitor_board.html`

Do **not** redesign `refresh_monitor_snapshot.py`; it already consumes the preferred row correctly.

---

### Task 1: Lock down the desired preferred-line behavior with tests

**Files:**
- Create: `tests/test_refresh_active_status_slv_nvda.py`
- Modify: `tests/test_refresh_active_status_tsla.py`

- [ ] **Step 1: Write the failing SLV/NVDA tests**

```python
from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import pandas as pd

import refresh_active_status as ras


class RefreshActiveStatusSlvNvdaTests(unittest.TestCase):
    def test_build_slv_promotes_gdx_hard_gate_breakthrough(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            asset_dir = Path(tmp)
            cache_dir = asset_dir / ".cache"
            cache_dir.mkdir()
            (cache_dir / "latest_prediction.json").write_text(
                json.dumps(
                    {
                        "latest_raw_date": "2026-04-15",
                        "signal_summary": {
                            "signal": "bullish",
                            "predicted_probability": 0.9607,
                            "decision_threshold": 0.9399,
                        },
                        "model_summary": {
                            "model_family": "hard_gate_two_expert",
                            "label_mode": "future-return-top-bottom-15pct",
                            "reference_percentile_rule": "top_15pct",
                        },
                        "model_extra_features": ["price_ratio_benchmark_z_20"],
                    }
                ),
                encoding="utf-8",
            )
            pd.DataFrame(
                [
                    {"date": "2026-04-14", "signal": "no_entry"},
                    {"date": "2026-04-15", "signal": "bullish"},
                ]
            ).to_csv(cache_dir / "signal_rows.tsv", sep="\t", index=False)

            with mock.patch.object(ras.ac, "get_latest_prediction_path", return_value=cache_dir / "latest_prediction.json"):
                result = ras.build_slv(asset_dir)

        row = result.iloc[0]
        self.assertEqual(row["line_id"], "hard_gate_two_expert_gdx_live")
        self.assertEqual(row["role"], "primary")
        self.assertEqual(row["preferred"], True)
        self.assertIn("GDX", str(row["usage_note"]))

    def test_build_nvda_prefers_best_current_candidate_line(self) -> None:
        pref = pd.DataFrame(
            [
                {"model_name": "binary_top12_5", "cutoff": 0.41},
                {"model_name": "ret_60_sma_gap_60_atr_pct_20", "cutoff": 0.45},
            ]
        )
        usage = pd.DataFrame(
            [
                {"model_name": "binary_top12_5", "recent_selected_count": 3, "latest_date": "2026-04-15", "latest_score": 0.44, "latest_selected": False, "cutoff": 0.41, "last_selected_date": "2026-04-11"},
                {"model_name": "ret_60_sma_gap_60_atr_pct_20", "recent_selected_count": 4, "latest_date": "2026-04-15", "latest_score": 0.62, "latest_selected": True, "cutoff": 0.45, "last_selected_date": "2026-04-15"},
            ]
        )

        with mock.patch.object(ras, "read_tsv", side_effect=[pref, usage]):
            result = ras.build_nvda(Path("unused"))

        preferred = result.loc[result["preferred"] == True].iloc[0]
        self.assertEqual(preferred["line_id"], "ret_60_sma_gap_60_atr_pct_20")
        self.assertEqual(preferred["role"], "primary")
```

- [ ] **Step 2: Extend the TSLA test so it locks the already-approved adopted live line**

```python
def test_build_tsla_keeps_tuned_xgboost_tb30_distance_live_as_preferred(self) -> None:
    # assert line_id == "xgboost_tb30_distance_live"
    # assert preferred is True
    # assert role == "execution_preference"
```

- [ ] **Step 3: Run the tests to confirm they fail for the current preferred-line behavior**

Run: `python -m unittest tests.test_refresh_active_status_slv_nvda tests.test_refresh_active_status_tsla -v`
Expected: FAIL because SLV still emits `baseline_threshold` and NVDA still prefers `binary_top12_5`.

- [ ] **Step 4: Commit the red tests**

```bash
git add tests/test_refresh_active_status_slv_nvda.py tests/test_refresh_active_status_tsla.py
git commit -m "Lock preferred strategy wiring for SLV NVDA and TSLA"
```

---

### Task 2: Implement the preferred-line rewiring in `refresh_active_status.py`

**Files:**
- Modify: `refresh_active_status.py`
- Test: `tests/test_refresh_active_status_slv_nvda.py`
- Test: `tests/test_refresh_active_status_tsla.py`

- [ ] **Step 1: Update SLV to emit the adopted breakthrough line instead of the research-only baseline**

```python
def build_slv(asset_dir: Path) -> pd.DataFrame:
    latest_prediction_path = ac.get_latest_prediction_path("slv")
    payload = json.loads(latest_prediction_path.read_text(encoding="utf-8"))
    rows = read_signal_rows_from_cache(latest_prediction_path.parent, "slv", 60)
    selected_rows = rows.loc[rows["signal"].astype(str) != "no_entry"]
    signal = str(payload["signal_summary"]["signal"])
    return pd.DataFrame(
        [
            {
                "line_id": "hard_gate_two_expert_gdx_live",
                "lane_type": "binary_operator",
                "role": "primary",
                "preferred": True,
                "status": "active" if signal != "no_entry" else "inactive",
                "recent_selected_count": int(len(selected_rows)),
                "latest_date": str(payload["latest_raw_date"]),
                "latest_value": float(payload["signal_summary"]["predicted_probability"]),
                "latest_selected": signal != "no_entry",
                "cutoff": float(payload["signal_summary"]["decision_threshold"]),
                "last_selected_date": fmt_date(selected_rows.iloc[-1]["date"]) if not selected_rows.empty else "",
                "usage_note": "Primary SLV live line uses the adopted GDX-relative hard-gate two-expert breakthrough.",
            }
        ]
    )
```

- [ ] **Step 2: Update NVDA so the preferred row is the chosen best-current candidate**

```python
def build_nvda(asset_dir: Path) -> pd.DataFrame:
    preferred_line = "ret_60_sma_gap_60_atr_pct_20"
    pref = read_tsv(asset_dir / "operator_preference_summary.tsv")
    usage = read_tsv(asset_dir / "operator_usage_summary.tsv")
    usage_map = {str(row["model_name"]): row for _, row in usage.iterrows()}
    rows: list[dict[str, object]] = []
    for _, row in pref.iterrows():
        key = str(row["model_name"])
        usage_row = usage_map[key]
        rows.append(
            {
                "line_id": key,
                "lane_type": "binary_watchlist",
                "role": "primary" if key == preferred_line else "sidecar",
                "preferred": key == preferred_line,
                "status": "watchlist_ready" if key == preferred_line else "secondary",
                ...
            }
        )
```

- [ ] **Step 3: Keep TSLA on the adopted tuned XGBoost live line, but make that expectation explicit in code/comments if it is still implicit**

```python
if ac.get_live_model_family("tsla") == "xgboost":
    return pd.DataFrame(
        [
            {
                "line_id": "xgboost_tb30_distance_live",
                ...
                "usage_note": "Primary TSLA live line uses the adopted tuned XGBoost TB30 distance_to_252_high strategy.",
            }
        ]
    )
```

- [ ] **Step 4: Run the focused tests and make them pass**

Run: `python -m unittest tests.test_refresh_active_status_slv_nvda tests.test_refresh_active_status_tsla -v`
Expected: PASS

- [ ] **Step 5: Commit the preferred-line wiring**

```bash
git add refresh_active_status.py tests/test_refresh_active_status_slv_nvda.py tests/test_refresh_active_status_tsla.py
git commit -m "Wire SLV NVDA and TSLA preferred strategies"
```

---

### Task 3: Refresh tracked outputs and verify the monitoring board

**Files:**
- Modify: `assets/slv/active_status_summary.tsv`
- Modify: `assets/slv/active_status.html`
- Modify: `assets/slv/monitor_snapshot.tsv`
- Modify: `assets/nvda/active_status_summary.tsv`
- Modify: `assets/nvda/active_status.html`
- Modify: `assets/nvda/monitor_snapshot.tsv`
- Modify: `assets/tsla/active_status_summary.tsv`
- Modify: `assets/tsla/active_status.html`
- Modify: `assets/tsla/monitor_snapshot.tsv`
- Modify: `monitor_board.tsv`
- Modify: `monitor_board.html`

- [ ] **Step 1: Refresh only the three affected assets and the board**

Run: `python refresh_reports.py slv nvda tsla`
Expected: success output for the three assets and a rebuilt `monitor_board.html`.

- [ ] **Step 2: Verify the refreshed preferred lines from the generated TSVs**

Run: `python -c "import pandas as pd; print(pd.read_csv('assets/slv/active_status_summary.tsv', sep='\t').loc[lambda df: df['preferred'] == True, ['line_id']]); print(pd.read_csv('assets/nvda/active_status_summary.tsv', sep='\t').loc[lambda df: df['preferred'] == True, ['line_id']]); print(pd.read_csv('assets/tsla/active_status_summary.tsv', sep='\t').loc[lambda df: df['preferred'] == True, ['line_id']])"`
Expected: `hard_gate_two_expert_gdx_live`, `ret_60_sma_gap_60_atr_pct_20`, and `xgboost_tb30_distance_live`.

- [ ] **Step 3: Verify the board snapshot lines**

Run: `python -c "import pandas as pd; board = pd.read_csv('monitor_board.tsv', sep='\t'); print(board.loc[board['asset_key'].isin(['slv','nvda','tsla']), ['asset_key', 'preferred_line', 'action']])"`
Expected: the three assets show the new preferred lines and their updated board actions.

- [ ] **Step 4: Run the relevant regression suite one more time**

Run: `python -m unittest tests.test_refresh_active_status_slv_nvda tests.test_refresh_active_status_tsla tests.test_refresh_monitor_snapshot tests.test_refresh_monitor_board tests.test_refresh_reports -v`
Expected: PASS

- [ ] **Step 5: Commit the regenerated outputs**

```bash
git add assets/slv/active_status_summary.tsv assets/slv/active_status.html assets/slv/monitor_snapshot.tsv assets/nvda/active_status_summary.tsv assets/nvda/active_status.html assets/nvda/monitor_snapshot.tsv assets/tsla/active_status_summary.tsv assets/tsla/active_status.html assets/tsla/monitor_snapshot.tsv monitor_board.tsv monitor_board.html
git commit -m "Refresh monitoring board for new SLV NVDA and TSLA defaults"
```

---

## Self-Review

- **Spec coverage:** The plan covers all three requested assets, preserves the existing board/snapshot architecture, and includes end-to-end refresh verification.
- **Placeholder scan:** No TODO/TBD placeholders remain; each task names concrete files, tests, and commands.
- **Type consistency:** Preferred-line names are used consistently as `hard_gate_two_expert_gdx_live`, `ret_60_sma_gap_60_atr_pct_20`, and `xgboost_tb30_distance_live` across tests, implementation, and verification.
