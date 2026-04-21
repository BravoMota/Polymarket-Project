from __future__ import annotations

from polyclaude_bot.config import Settings
from polyclaude_bot.features.feature_engine import MarketFeatures
from polyclaude_bot.llm.claude_client import ClaudeDecision


def evaluate_risk(features: MarketFeatures, decision: ClaudeDecision, settings: Settings) -> list[str]:
    flags: list[str] = []
    if features.liquidity_score * 100000 < settings.min_liquidity_usd:
        flags.append("low_liquidity")
    if features.spread_pct > settings.max_spread_pct:
        flags.append("high_spread")
    if abs(features.edge_bps) < settings.min_abs_edge_bps:
        flags.append("insufficient_edge")
    if decision.confidence < settings.min_confidence:
        flags.append("low_confidence")
    return flags
