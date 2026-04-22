"""Tolerant loaders for the data/handoff/*.json files the UI displays.

Every loader returns a HandoffFile with:
    - rows: list of dicts (empty if the file is missing or corrupt)
    - path: canonical on-disk path (for the UI)
    - mtime: last modified timestamp (None when missing)
    - error: short string when something went wrong (None otherwise)
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

HANDOFF_DIR = Path("data/handoff")

SHORTLIST_PATH = HANDOFF_DIR / "latest_shortlist.json"
DELTA_PATH = HANDOFF_DIR / "latest_delta.json"
DECISIONS_PATH = HANDOFF_DIR / "cowork_decisions.json"
PROMPT_PATH = Path("prompts/cowork_decide_prompt.txt")


@dataclass
class HandoffFile:
    path: Path
    rows: list[dict[str, Any]] = field(default_factory=list)
    mtime: datetime | None = None
    error: str | None = None

    @property
    def exists(self) -> bool:
        return self.mtime is not None

    @property
    def count(self) -> int:
        return len(self.rows)

    @property
    def mtime_display(self) -> str:
        if self.mtime is None:
            return "never"
        return self.mtime.astimezone().strftime("%Y-%m-%d %H:%M:%S")


def _load(path: Path) -> HandoffFile:
    if not path.exists():
        return HandoffFile(path=path)
    try:
        mtime = datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc)
        raw = path.read_text(encoding="utf-8")
        parsed = json.loads(raw) if raw.strip() else []
        if not isinstance(parsed, list):
            return HandoffFile(path=path, mtime=mtime, error="expected a JSON list")
        rows = [r for r in parsed if isinstance(r, dict)]
        return HandoffFile(path=path, rows=rows, mtime=mtime)
    except json.JSONDecodeError as exc:
        return HandoffFile(path=path, mtime=mtime, error=f"invalid JSON: {exc.msg}")
    except OSError as exc:
        return HandoffFile(path=path, error=f"read error: {exc}")


def load_shortlist() -> HandoffFile:
    return _load(SHORTLIST_PATH)


def load_delta() -> HandoffFile:
    return _load(DELTA_PATH)


def load_decisions() -> HandoffFile:
    return _load(DECISIONS_PATH)


def load_shortlist_raw() -> str:
    """Return the raw shortlist JSON text for copy-to-clipboard.

    Returns "[]" if the file does not exist so the clipboard is never empty.
    """
    if not SHORTLIST_PATH.exists():
        return "[]"
    try:
        return SHORTLIST_PATH.read_text(encoding="utf-8")
    except OSError:
        return "[]"


def load_prompt_text() -> str:
    """Return the contents of prompts/cowork_decide_prompt.txt (empty if missing)."""
    try:
        return PROMPT_PATH.read_text(encoding="utf-8")
    except OSError:
        return ""


def build_prompt_with_shortlist() -> str:
    """Prompt text + a short intro + the current shortlist JSON, ready to paste."""
    prompt = load_prompt_text().rstrip()
    body = load_shortlist_raw().rstrip()
    intro = (
        "\n\nCurrent shortlist (data/handoff/latest_shortlist.json). "
        "Use the delta-first rules above; fall back to this full list if the delta is empty.\n"
    )
    return f"{prompt}{intro}```json\n{body}\n```\n"


def write_decisions(text: str) -> tuple[bool, str | None]:
    """Validate + persist pasted cowork decisions JSON.

    Accepts: a JSON array of objects. Rewrites `cowork_decisions.json`
    pretty-printed with 2-space indent so the UI stays readable.
    """
    stripped = text.strip()
    if not stripped:
        return False, "paste is empty"
    try:
        parsed = json.loads(stripped)
    except json.JSONDecodeError as exc:
        return False, f"invalid JSON: {exc.msg} at line {exc.lineno}"
    if not isinstance(parsed, list):
        return False, "expected a JSON array at the top level"
    for i, row in enumerate(parsed):
        if not isinstance(row, dict):
            return False, f"entry #{i} is not a JSON object"
    DECISIONS_PATH.parent.mkdir(parents=True, exist_ok=True)
    DECISIONS_PATH.write_text(json.dumps(parsed, indent=2) + "\n", encoding="utf-8")
    return True, None
