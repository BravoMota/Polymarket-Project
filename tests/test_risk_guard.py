from polyclaude_bot.config import Settings
from polyclaude_bot.features.feature_engine import MarketFeatures
from polyclaude_bot.llm.claude_client import ClaudeDecision
from polyclaude_bot.risk.risk_guard import evaluate_risk


def test_risk_flags() -> None:
    settings = Settings()
    features = MarketFeatures(
        market_id="m1",
        question="q",
        market_implied_prob_yes=0.5,
        estimated_prob_yes=0.51,
        edge_bps=50,
        expected_value_per_1usd=-0.01,
        liquidity_score=0.01,
        spread_pct=0.2,
        volatility_proxy=0.2,
    )
    decision = ClaudeDecision(
        action="YES",
        confidence=0.4,
        estimated_prob_yes=0.51,
        market_implied_prob_yes=0.5,
        edge_bps=50,
        expected_value_per_1usd=-0.01,
        liquidity_score=0.01,
        risk_flags=[],
        rationale_bullets=[],
    )
    flags = evaluate_risk(features, decision, settings)
    assert "low_liquidity" in flags
    assert "high_spread" in flags
    assert "insufficient_edge" in flags
    assert "low_confidence" in flags
