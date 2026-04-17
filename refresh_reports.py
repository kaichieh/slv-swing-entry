from __future__ import annotations

import argparse
import concurrent.futures
import json
import os
import subprocess
import sys
import time
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
    start = time.perf_counter()
    print(f"[{asset_key}] start", flush=True)
    run_step("prepare.py", asset_key)
    if ac.uses_regression_chart(asset_key):
        run_step("research_regression_recent.py", asset_key)
        run_step("research_regression_recent_chart.py", asset_key)
    else:
        run_step("chart_signals.py", asset_key)
    run_step("refresh_active_status.py", asset_key)
    run_step("render_active_status.py", asset_key)
    run_step("refresh_monitor_snapshot.py", asset_key)
    elapsed = time.perf_counter() - start
    print(f"[{asset_key}] done in {elapsed:.1f}s", flush=True)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Refresh asset charts and monitor reports.")
    parser.add_argument(
        "assets",
        nargs="*",
        help="Optional asset keys. Default: monitor board assets.",
    )
    parser.add_argument(
        "--jobs",
        type=int,
        default=None,
        help="Number of assets to refresh in parallel. Default: min(4, number of assets).",
    )
    return parser.parse_args()


def resolve_jobs(args: argparse.Namespace, asset_count: int) -> int:
    if asset_count <= 1:
        return 1
    if args.jobs is not None:
        if args.jobs < 1:
            raise ValueError("--jobs must be at least 1")
        return min(args.jobs, asset_count)
    return min(4, asset_count)


def main() -> None:
    args = parse_args()
    asset_keys = [asset.strip().lower() for asset in args.assets if asset.strip()]
    if not asset_keys:
        asset_keys = list(ac.MONITOR_BOARD_ASSET_KEYS)

    unknown = [key for key in asset_keys if key not in ac.ASSET_DEFAULTS]
    if unknown:
        raise ValueError(f"Unsupported assets: {', '.join(unknown)}")

    jobs = resolve_jobs(args, len(asset_keys))
    if jobs == 1:
        for asset_key in asset_keys:
            refresh_asset(asset_key)
    else:
        with concurrent.futures.ThreadPoolExecutor(max_workers=jobs) as executor:
            future_to_asset = {executor.submit(refresh_asset, asset_key): asset_key for asset_key in asset_keys}
            for future in concurrent.futures.as_completed(future_to_asset):
                asset_key = future_to_asset[future]
                try:
                    future.result()
                except Exception as exc:
                    raise RuntimeError(f"Failed while refreshing asset '{asset_key}'") from exc

    run_step("refresh_monitor_board.py")

    print(
        json.dumps(
            {
                "refreshed_assets": asset_keys,
                "parallel_jobs": jobs,
                "monitor_board_html": str(ac.get_monitor_board_chart_path()),
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
