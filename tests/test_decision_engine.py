from polyclaude_bot.strategy.decision_engine import default_decision, enforce_risk


def test_enforce_risk_forces_skip() -> None:
    d = default_decision(
        implied=0.5,
        estimated=0.6,
        edge_bps=200,
        ev=0.02,
        liquidity_score=0.8,
    )
    out = enforce_risk(d, ["high_spread"])
    assert out.action == "SKIP"
    assert "high_spread" in out.risk_flags
