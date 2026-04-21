from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path

from polyclaude_bot.features.feature_engine import MarketFeatures
from polyclaude_bot.llm.claude_client import ClaudeDecision


@dataclass
class LedgerEntry:
    timestamp_utc: str
    market_id: str
    question: str
    action: str
    confidence: float
    edge_bps: float
    expected_value_per_1usd: float
    liquidity_score: float
    risk_flags: list[str]


def append_entry(path: str, features: MarketFeatures, decision: ClaudeDecision) -> None:
    out = Path(path)
    out.parent.mkdir(parents=True, exist_ok=True)
    entry = LedgerEntry(
        timestamp_utc=datetime.now(timezone.utc).isoformat(),
        market_id=features.market_id,
        question=features.question,
        action=decision.action,
        confidence=decision.confidence,
        edge_bps=decision.edge_bps,
        expected_value_per_1usd=decision.expected_value_per_1usd,
        liquidity_score=decision.liquidity_score,
        risk_flags=decision.risk_flags,
    )
    with out.open("a", encoding="utf-8") as f:
        f.write(json.dumps(asdict(entry)) + "\n")
