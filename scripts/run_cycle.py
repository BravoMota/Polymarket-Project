"""Cross-platform runner for the polyclaude-bot export-shortlist pipeline.

Mirrors the combined behavior of scripts/hourly_scan.bat and
scripts/run_cowork_cycle.bat so macOS/Linux users have an equivalent
entry point. The .bat files remain the canonical Windows flow.

Usage:
    python scripts/run_cycle.py
    # or, without activating the venv:
    .venv/bin/python scripts/run_cycle.py        # macOS / Linux
    .venv\\Scripts\\python.exe scripts\\run_cycle.py  # Windows
"""

from __future__ import annotations

import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
LOG_DIR = REPO_ROOT / "data" / "logs"
LOG_FILE = LOG_DIR / "hourly_scan.log"
HANDOFF_DIR = REPO_ROOT / "data" / "handoff"
REQUIRED_HANDOFF_FILES = (
    "latest_shortlist.csv",
    "latest_shortlist.json",
    "latest_delta.json",
)

COWORK_NEXT_STEPS = """
====================================================
 Cowork next steps
====================================================

 STEP 1 (token-efficient):
   Open Claude Cowork, paste prompts/cowork_decide_prompt.txt,
   then ask it to read data/handoff/latest_delta.json
   (only new/changed opportunities - smallest token cost).

 STEP 2 (if delta is empty or more context needed):
   Ask Cowork to read data/handoff/latest_shortlist.json
   (full ranked shortlist).

 STEP 3:
   Save Cowork JSON output to data/handoff/cowork_decisions.json

====================================================
"""


def _venv_python() -> Path:
    if os.name == "nt":
        return REPO_ROOT / ".venv" / "Scripts" / "python.exe"
    return REPO_ROOT / ".venv" / "bin" / "python"


def _log(message: str) -> None:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with LOG_FILE.open("a", encoding="utf-8") as fh:
        fh.write(f"[{stamp}] {message}\n")


def _missing_venv_message(venv_py: Path) -> None:
    if os.name == "nt":
        activate = ".venv\\Scripts\\activate"
    else:
        activate = "source .venv/bin/activate"
    print()
    print(f"ERROR: {venv_py} not found.")
    print("Run these commands to create it:")
    print("  python -m venv .venv")
    print(f"  {activate}")
    print('  pip install -e ".[dev]"')
    print()


def main() -> int:
    _log("hourly_scan START")

    venv_py = _venv_python()
    if not venv_py.exists():
        _log("ERROR: .venv not found")
        _missing_venv_message(venv_py)
        return 1

    cmd = [
        str(venv_py),
        "-m",
        "polyclaude_bot.cli",
        "export-shortlist",
        "--limit",
        "20",
        "--top-n",
        "5",
        "--min-liquidity",
        "10000",
        "--max-spread",
        "0.05",
        "--min-abs-edge-bps",
        "50",
    ]

    try:
        completed = subprocess.run(cmd, cwd=REPO_ROOT, check=False)
    except OSError as exc:
        _log(f"ERROR: failed to launch export-shortlist: {exc}")
        print(f"ERROR: failed to launch export-shortlist: {exc}")
        return 1

    rc = completed.returncode
    if rc != 0:
        _log(f"ERROR: export-shortlist exited {rc}")
        print(f"ERROR: export-shortlist failed (exit {rc})")
        return rc

    missing = [
        name for name in REQUIRED_HANDOFF_FILES if not (HANDOFF_DIR / name).exists()
    ]
    if missing:
        _log("ERROR: one or more handoff files missing: " + ", ".join(missing))
        print(
            "ERROR: handoff output files not found in data/handoff/: "
            + ", ".join(missing)
        )
        return 1

    _log("hourly_scan OK")
    _log("cowork_cycle scan OK")
    print("Handoff files verified in data/handoff/")
    print(COWORK_NEXT_STEPS)
    return 0


if __name__ == "__main__":
    sys.exit(main())
