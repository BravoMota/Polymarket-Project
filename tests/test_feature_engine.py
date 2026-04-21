from polyclaude_bot.data.polymarket_client import MarketSnapshot
from polyclaude_bot.features.feature_engine import compute_features


def test_compute_features_ranges() -> None:
    s = MarketSnapshot(
        market_id="m1",
        question="Will X happen?",
        yes_price=0.55,
        no_price=0.44,
        volume_24h=100000,
        liquidity_usd=40000,
        spread_pct=0.02,
        timestamp_utc="2026-01-01T00:00:00Z",
    )
    f = compute_features(s)
    assert 0 <= f.market_implied_prob_yes <= 1
    assert 0 <= f.estimated_prob_yes <= 1
    assert 0 <= f.liquidity_score <= 1
