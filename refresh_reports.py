from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

import asset_config as ac

REPO_DIR = Path(__file__).resolve().parent


def build_env(asset_key: str | None = None) -> dict[str, str]:
    env = os.environ.copy()
    package_dir = REPO_DIR / ".packages"
    existing = env.get("PYTHONPATH", "").strip()
    if package_dir.exists():
        env["PYTHONPATH"] = str(package_dir) if not existing else f"{package_dir}{os.pathsep}{existing}"
    if asset_key:
        env["AR_ASSET"] = asset_key
    return env


def run_step(script_name: str, asset_key: str | None = None) -> None:
    command = [sys.executable, script_name]
    subprocess.run(command, cwd=REPO_DIR, env=build_env(asset_key), check=True)


def refresh_asset(asset_key: str) -> None:
    run_step("prepare.py", asset_key)
    if ac.uses_regression_chart(asset_key):
        run_step("research_regression_recent.py", asset_key)
        run_step("research_regression_recent_chart.py", asset_key)
    else:
        run_step("predict_latest.py", asset_key)
        run_step("chart_signals.py", asset_key)
    run_step("refresh_active_status.py", asset_key)
    run_step("refresh_monitor_snapshot.py", asset_key)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Refresh asset charts and monitor reports.")
    parser.add_argument(
        "assets",
        nargs="*",
        help="Optional asset keys. Default: all assets.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    asset_keys = [asset.strip().lower() for asset in args.assets if asset.strip()]
    if not asset_keys:
        asset_keys = list(ac.ASSET_DEFAULTS)

    unknown = [key for key in asset_keys if key not in ac.ASSET_DEFAULTS]
    if unknown:
        raise ValueError(f"Unsupported assets: {', '.join(unknown)}")

    for asset_key in asset_keys:
        refresh_asset(asset_key)

    run_step("refresh_monitor_board.py")

    print(
        json.dumps(
            {
                "refreshed_assets": asset_keys,
                "monitor_board_html": str(ac.get_monitor_board_chart_path()),
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
