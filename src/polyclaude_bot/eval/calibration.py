from __future__ import annotations

import json
from pathlib import Path


def calibration_proxy(ledger_path: str) -> dict:
    path = Path(ledger_path)
    if not path.exists():
        return {"confidence_distribution": {}, "note": "No ledger yet"}
    bins = {"0.5-0.6": 0, "0.6-0.7": 0, "0.7-0.8": 0, "0.8-0.9": 0, "0.9-1.0": 0}
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        conf = json.loads(line)["confidence"]
        if conf < 0.6:
            bins["0.5-0.6"] += 1
        elif conf < 0.7:
            bins["0.6-0.7"] += 1
        elif conf < 0.8:
            bins["0.7-0.8"] += 1
        elif conf < 0.9:
            bins["0.8-0.9"] += 1
        else:
            bins["0.9-1.0"] += 1
    return {"confidence_distribution": bins}
