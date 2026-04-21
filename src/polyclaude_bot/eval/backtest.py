from __future__ import annotations

import json
from pathlib import Path


def summarize_ledger(ledger_path: str) -> dict:
    path = Path(ledger_path)
    if not path.exists():
        return {"trades": 0, "yes": 0, "no": 0, "skip": 0, "avg_confidence": 0.0}
    rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    trades = len(rows)
    yes = sum(1 for r in rows if r["action"] == "YES")
    no = sum(1 for r in rows if r["action"] == "NO")
    skip = sum(1 for r in rows if r["action"] == "SKIP")
    avg_conf = round(sum(r["confidence"] for r in rows) / trades, 4) if trades else 0.0
    return {"trades": trades, "yes": yes, "no": no, "skip": skip, "avg_confidence": avg_conf}
