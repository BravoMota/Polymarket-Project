from __future__ import annotations

from polyclaude_bot.features.feature_engine import MarketFeatures


def build_decision_prompt(features: MarketFeatures) -> str:
    return f"""
You are a quant analyst for prediction markets.
Return JSON only with keys:
action, confidence, estimated_prob_yes, market_implied_prob_yes, edge_bps,
expected_value_per_1usd, liquidity_score, risk_flags, rationale_bullets.

Rules:
- action must be YES, NO, or SKIP
- confidence must be [0,1]
- rationale_bullets must be a list of short measurable statements

Input market:
- market_id: {features.market_id}
- question: {features.question}
- market_implied_prob_yes: {features.market_implied_prob_yes}
- estimated_prob_yes: {features.estimated_prob_yes}
- edge_bps: {features.edge_bps}
- expected_value_per_1usd: {features.expected_value_per_1usd}
- liquidity_score: {features.liquidity_score}
- spread_pct: {features.spread_pct}
- volatility_proxy: {features.volatility_proxy}
""".strip()
