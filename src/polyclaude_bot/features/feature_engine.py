from __future__ import annotations

from dataclasses import dataclass

from polyclaude_bot.data.polymarket_client import MarketSnapshot


@dataclass
class MarketFeatures:
    market_id: str
    question: str
    market_implied_prob_yes: float
    estimated_prob_yes: float
    edge_bps: float
    expected_value_per_1usd: float
    liquidity_score: float
    spread_pct: float
    volatility_proxy: float


def _bounded(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def compute_features(snapshot: MarketSnapshot) -> MarketFeatures:
    implied = snapshot.yes_price
    liquidity_score = _bounded(snapshot.liquidity_usd / 100000, 0.0, 1.0)
    spread_penalty = _bounded(snapshot.spread_pct / 0.10, 0.0, 1.0)
    volatility_proxy = _bounded(abs(0.5 - implied) * 2, 0.0, 1.0)

    # Heuristic baseline until a trained model is added.
    estimated = _bounded(implied + (liquidity_score - spread_penalty) * 0.05, 0.01, 0.99)
    edge = (estimated - implied) * 10000
    ev = estimated * (1 / max(snapshot.yes_price, 0.01) - 1) - (1 - estimated)

    return MarketFeatures(
        market_id=snapshot.market_id,
        question=snapshot.question,
        market_implied_prob_yes=round(implied, 4),
        estimated_prob_yes=round(estimated, 4),
        edge_bps=round(edge, 2),
        expected_value_per_1usd=round(ev, 4),
        liquidity_score=round(liquidity_score, 4),
        spread_pct=round(snapshot.spread_pct, 4),
        volatility_proxy=round(volatility_proxy, 4),
    )
