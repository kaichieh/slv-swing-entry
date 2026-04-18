from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


REPO_DIR = Path(__file__).resolve().parent
REPORT_SCRIPTS = (
    "refresh_mu_gap_volume_ignition_v82_shadow.py",
    "refresh_mu_gap_volume_ignition_v82_divergence_report.py",
    "refresh_mu_gap_volume_ignition_v82_live_bucket_report.py",
)


def run_step(script_name: str) -> None:
    subprocess.run([sys.executable, script_name], cwd=REPO_DIR, check=True)


def main() -> None:
    for script_name in REPORT_SCRIPTS:
        run_step(script_name)

    print(
        json.dumps(
            {
                "report_scripts": list(REPORT_SCRIPTS),
                "runner": str(Path(__file__).name),
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
