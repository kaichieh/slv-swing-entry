from __future__ import annotations

import json

import pandas as pd

import asset_config as ac


def normalize_date(value: object) -> pd.Timestamp | None:
    if value is None:
        return None
    if bool(pd.isna(value)):
        return None
    text = str(value).strip()
    if not text or text.lower() == "nan":
        return None
    return pd.to_datetime(text)


def decide_action(status: str, latest_selected: bool, recent_selected_count: int, lane_type: str, role: str) -> str:
    status_tokens = set(status.lower().split("_"))
    lane_tokens = set(lane_type.lower().split("_"))
    role_tokens = set(role.lower().split("_"))
    if latest_selected:
        return "selected_now"
    if "reference" in status_tokens or "reference" in lane_tokens or "reference" in role_tokens:
        return "reference_only"
    if "research" in status_tokens or "research" in lane_tokens or "research" in role_tokens:
        return "research_only"
    if recent_selected_count > 0:
        return "watchlist_wait"
    return "inactive_wait"


def build_snapshot() -> pd.DataFrame:
    frame = pd.read_csv(ac.get_active_status_output_path(), sep="\t")
    preferred = frame.loc[frame["preferred"] == True].copy()
    if preferred.empty:
        raise ValueError("No preferred line found in active status summary.")
    row = preferred.iloc[0]

    latest_date = normalize_date(row["latest_date"])
    last_selected_date = normalize_date(row["last_selected_date"])
    days_since_last = None
    if latest_date is not None and last_selected_date is not None:
        days_since_last = int((latest_date - last_selected_date).days)

    latest_selected = bool(row["latest_selected"])
    recent_selected_count = int(row["recent_selected_count"])
    lane_type = str(row["lane_type"])
    status = str(row["status"])
    role = str(row["role"])
    action = decide_action(status, latest_selected, recent_selected_count, lane_type, role)
    latest_value = None if pd.isna(row["latest_value"]) else float(row["latest_value"])
    cutoff = None if pd.isna(row["cutoff"]) else float(row["cutoff"])
    if action == "watchlist_wait" and status == "inactive" and latest_value is not None and cutoff is not None and latest_value >= cutoff:
        action = "watchlist_blocked"

    if latest_selected:
        action_note = "Preferred line is currently selected."
    elif action == "watchlist_blocked":
        action_note = "Preferred line clears threshold, but the buy-point overlay blocks entry today."
    elif action == "reference_only":
        action_note = "Keep as market/reference context only."
    elif action == "research_only":
        action_note = "Research-only line; no live operating action."
    elif recent_selected_count > 0:
        action_note = "Preferred line is valid but currently waiting below cutoff."
    else:
        action_note = "Preferred line is inactive; continue monitoring without action."

    snapshot = pd.DataFrame(
        [
            {
                "asset_key": ac.get_asset_key(),
                "symbol": ac.get_asset_symbol(),
                "preferred_line": str(row["line_id"]),
                "lane_type": lane_type,
                "role": role,
                "status": status,
                "action": action,
                "recent_selected_count": recent_selected_count,
                "latest_date": "" if latest_date is None else latest_date.strftime("%Y-%m-%d"),
                "latest_value": latest_value,
                "latest_selected": latest_selected,
                "cutoff": cutoff,
                "last_selected_date": "" if last_selected_date is None else last_selected_date.strftime("%Y-%m-%d"),
                "days_since_last_selected": days_since_last,
                "action_note": action_note,
            }
        ]
    )
    return snapshot


def main() -> None:
    snapshot = build_snapshot()
    output_path = ac.get_monitor_snapshot_path()
    snapshot.to_csv(output_path, sep="\t", index=False)
    print(
        json.dumps(
            {
                "asset_key": ac.get_asset_key(),
                "output_path": str(output_path),
                "preferred_line": str(snapshot.iloc[0]["preferred_line"]),
                "action": str(snapshot.iloc[0]["action"]),
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
