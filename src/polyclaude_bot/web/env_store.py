"""Safe .env read/write for the five tunables exposed in the web UI.

The web UI MUST NOT touch anything outside this whitelist. Untouched
lines (PAPER_MODE, ANTHROPIC_API_KEY, paths, CLAUDE_MODEL, comments,
blank lines) are preserved byte-for-byte on save.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Callable

ENV_PATH = Path(".env")


@dataclass(frozen=True)
class EnvField:
    key: str
    label: str
    kind: str  # "int" | "float"
    min_value: float
    max_value: float | None
    step: float
    help_text: str


EDITABLE_FIELDS: tuple[EnvField, ...] = (
    EnvField(
        key="SCAN_LIMIT",
        label="Scan limit",
        kind="int",
        min_value=1,
        max_value=500,
        step=1,
        help_text="Markets to fetch per scan / decide call.",
    ),
    EnvField(
        key="MIN_LIQUIDITY_USD",
        label="Min liquidity (USD)",
        kind="float",
        min_value=0,
        max_value=None,
        step=500,
        help_text="Drop markets with less book liquidity than this.",
    ),
    EnvField(
        key="MAX_SPREAD_PCT",
        label="Max spread",
        kind="float",
        min_value=0,
        max_value=1,
        step=0.01,
        help_text="Drop markets with spread wider than this fraction (e.g. 0.05 = 5%).",
    ),
    EnvField(
        key="MIN_ABS_EDGE_BPS",
        label="Min |edge| (bps)",
        kind="float",
        min_value=0,
        max_value=None,
        step=10,
        help_text="Only keep markets whose |edge_bps| clears this threshold.",
    ),
    EnvField(
        key="MIN_CONFIDENCE",
        label="Min confidence",
        kind="float",
        min_value=0,
        max_value=1,
        step=0.01,
        help_text="Risk guard: decisions below this confidence are downgraded.",
    ),
)

EDITABLE_KEYS: frozenset[str] = frozenset(f.key for f in EDITABLE_FIELDS)


def _parse_line(line: str) -> tuple[str, str] | None:
    """Return (key, value) for a KEY=VALUE line, else None (comment/blank/malformed)."""
    stripped = line.strip()
    if not stripped or stripped.startswith("#"):
        return None
    if "=" not in stripped:
        return None
    key, value = stripped.split("=", 1)
    return key.strip(), value.strip()


def read_values(path: Path = ENV_PATH) -> dict[str, str]:
    """Return current values for every editable key (missing → empty string)."""
    values: dict[str, str] = {k: "" for k in EDITABLE_KEYS}
    if not path.exists():
        return values
    for raw in path.read_text(encoding="utf-8").splitlines():
        parsed = _parse_line(raw)
        if parsed is None:
            continue
        key, value = parsed
        if key in EDITABLE_KEYS:
            values[key] = value
    return values


class EnvValidationError(ValueError):
    """Raised when a submitted value fails field constraints."""


def _coerce(field: EnvField, raw: str) -> str:
    if raw == "" or raw is None:
        raise EnvValidationError(f"{field.key} is required")
    try:
        if field.kind == "int":
            value: float = int(raw)
        else:
            value = float(raw)
    except ValueError as exc:
        raise EnvValidationError(f"{field.key} must be a {field.kind}") from exc
    if value < field.min_value:
        raise EnvValidationError(f"{field.key} must be >= {field.min_value}")
    if field.max_value is not None and value > field.max_value:
        raise EnvValidationError(f"{field.key} must be <= {field.max_value}")
    # Normalize: ints without decimal point, floats trimmed of trailing zeros.
    if field.kind == "int":
        return str(int(value))
    formatted = f"{value:.6f}".rstrip("0").rstrip(".")
    return formatted or "0"


def validate(submitted: dict[str, str]) -> dict[str, str]:
    """Coerce and bounds-check every editable field. Raises on first failure."""
    cleaned: dict[str, str] = {}
    for field in EDITABLE_FIELDS:
        cleaned[field.key] = _coerce(field, submitted.get(field.key, ""))
    return cleaned


def write_values(
    updates: dict[str, str],
    path: Path = ENV_PATH,
    *,
    validator: Callable[[dict[str, str]], dict[str, str]] = validate,
) -> dict[str, str]:
    """Persist the five editable keys, preserving every other line.

    - Lines for editable keys are rewritten in place.
    - Editable keys that were missing from the file are appended at the end.
    - Untouched keys, comments, and blank lines are preserved byte-for-byte.
    """
    cleaned = validator(updates)

    original = path.read_text(encoding="utf-8") if path.exists() else ""
    had_trailing_newline = original.endswith("\n") or original == ""
    lines = original.splitlines()

    seen: set[str] = set()
    rewritten: list[str] = []
    for raw in lines:
        parsed = _parse_line(raw)
        if parsed is None:
            rewritten.append(raw)
            continue
        key, _ = parsed
        if key in cleaned:
            rewritten.append(f"{key}={cleaned[key]}")
            seen.add(key)
        else:
            rewritten.append(raw)

    for key in cleaned:
        if key not in seen:
            rewritten.append(f"{key}={cleaned[key]}")

    body = "\n".join(rewritten)
    if had_trailing_newline and not body.endswith("\n"):
        body += "\n"
    path.write_text(body, encoding="utf-8")
    return cleaned
