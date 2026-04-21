from __future__ import annotations

import json
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path
from random import random


@dataclass
class MarketSnapshot:
    market_id: str
    question: str
    yes_price: float
    no_price: float
    volume_24h: float
    liquidity_usd: float
    spread_pct: float
    timestamp_utc: str


class PolymarketClient:
    """Thin adapter. Uses mock fallback until live adapter is wired."""

    def fetch_markets(self, limit: int = 25) -> list[MarketSnapshot]:
        now = datetime.now(timezone.utc).isoformat()
        snapshots: list[MarketSnapshot] = []
        for i in range(limit):
            yes = 0.35 + random() * 0.30
            no = max(0.01, 1 - yes - 0.01)
            spread = 0.01 + random() * 0.06
            snapshots.append(
                MarketSnapshot(
                    market_id=f"mkt-{i + 1}",
                    question=f"Sample market {i + 1}: Will event happen?",
                    yes_price=round(yes, 4),
                    no_price=round(no, 4),
                    volume_24h=round(5000 + random() * 250000, 2),
                    liquidity_usd=round(2000 + random() * 150000, 2),
                    spread_pct=round(spread, 4),
                    timestamp_utc=now,
                )
            )
        return snapshots

    @staticmethod
    def persist_snapshot_batch(markets: list[MarketSnapshot], snapshot_dir: str) -> Path:
        path = Path(snapshot_dir)
        path.mkdir(parents=True, exist_ok=True)
        outfile = path / f"snapshot_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}.json"
        payload = [asdict(m) for m in markets]
        outfile.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        return outfile
