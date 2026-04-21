from __future__ import annotations

from polyclaude_bot.llm.claude_client import ClaudeDecision


def default_decision(
    implied: float,
    estimated: float,
    edge_bps: float,
    ev: float,
    liquidity_score: float,
) -> ClaudeDecision:
    action = "SKIP"
    if edge_bps >= 150 and ev > 0:
        action = "YES"
    elif edge_bps <= -150:
        action = "NO"
    return ClaudeDecision(
        action=action,
        confidence=min(0.95, max(0.5, abs(edge_bps) / 1000)),
        estimated_prob_yes=estimated,
        market_implied_prob_yes=implied,
        edge_bps=edge_bps,
        expected_value_per_1usd=ev,
        liquidity_score=liquidity_score,
        risk_flags=[],
        rationale_bullets=[
            f"edge_bps={edge_bps}",
            f"ev_per_1usd={ev}",
            f"liquidity_score={liquidity_score}",
        ],
    )


def enforce_risk(decision: ClaudeDecision, risk_flags: list[str]) -> ClaudeDecision:
    if risk_flags:
        decision.action = "SKIP"
    decision.risk_flags = sorted(set(decision.risk_flags + risk_flags))
    return decision
