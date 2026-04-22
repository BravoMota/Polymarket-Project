from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path

import httpx

GAMMA_MARKETS_URL = "https://gamma-api.polymarket.com/markets"
PER_PAGE_CAP = 100
REQUEST_TIMEOUT_SECONDS = 10.0


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
    """Thin adapter around Polymarket's public Gamma API."""

    def fetch_markets(self, limit: int = 25) -> list[MarketSnapshot]:
        if limit <= 0:
            return []

        timestamp = datetime.now(timezone.utc).isoformat()
        snapshots: list[MarketSnapshot] = []
        offset = 0

        try:
            with httpx.Client(timeout=REQUEST_TIMEOUT_SECONDS) as client:
                while len(snapshots) < limit:
                    params = {
                        "active": "true",
                        "closed": "false",
                        "limit": PER_PAGE_CAP,
                        "offset": offset,
                    }
                    response = client.get(GAMMA_MARKETS_URL, params=params)
                    response.raise_for_status()
                    rows = response.json()
                    if not isinstance(rows, list) or not rows:
                        break

                    for raw in rows:
                        snapshot = _row_to_snapshot(raw, timestamp)
                        if snapshot is not None:
                            snapshots.append(snapshot)
                            if len(snapshots) >= limit:
                                break

                    if len(rows) < PER_PAGE_CAP:
                        break
                    offset += len(rows)
        except httpx.HTTPError:
            return []

        return snapshots[:limit]

    @staticmethod
    def persist_snapshot_batch(markets: list[MarketSnapshot], snapshot_dir: str) -> Path:
        path = Path(snapshot_dir)
        path.mkdir(parents=True, exist_ok=True)
        outfile = path / f"snapshot_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}.json"
        payload = [asdict(m) for m in markets]
        outfile.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        return outfile


def _row_to_snapshot(raw: dict, timestamp: str) -> MarketSnapshot | None:
    try:
        outcomes = json.loads(raw["outcomes"])
        if outcomes != ["Yes", "No"]:
            return None

        prices = json.loads(raw["outcomePrices"])
        if not isinstance(prices, list) or len(prices) != 2:
            return None
        yes = float(prices[0])
        no = float(prices[1])

        return MarketSnapshot(
            market_id=str(raw["id"]),
            question=raw["question"],
            yes_price=yes,
            no_price=no,
            volume_24h=float(raw.get("volume24hr") or 0.0),
            liquidity_usd=float(raw.get("liquidityNum") or 0.0),
            spread_pct=max(1.0 - yes - no, 0.001),
            timestamp_utc=timestamp,
        )
    except (KeyError, ValueError, TypeError, json.JSONDecodeError):
        return None
