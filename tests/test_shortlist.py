"""Tests for shortlist filtering, sorting, and delta generation."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from polyclaude_bot.cli import _apply_filters, _compute_delta
from polyclaude_bot.data.polymarket_client import MarketSnapshot
from polyclaude_bot.features.feature_engine import MarketFeatures, compute_features


def _snap(
    market_id: str,
    yes_price: float = 0.55,
    liquidity_usd: float = 50_000,
    spread_pct: float = 0.02,
) -> MarketSnapshot:
    return MarketSnapshot(
        market_id=market_id,
        question=f"Will {market_id} happen?",
        yes_price=yes_price,
        no_price=round(1 - yes_price - spread_pct, 4),
        volume_24h=100_000,
        liquidity_usd=liquidity_usd,
        spread_pct=spread_pct,
        timestamp_utc="2026-01-01T00:00:00Z",
    )


def _features(market_id: str, **kwargs) -> MarketFeatures:
    return compute_features(_snap(market_id, **kwargs))


# ── filter tests ──────────────────────────────────────────────────────────────


def test_filter_min_liquidity_removes_low_liquidity() -> None:
    rows = [_features("low", liquidity_usd=5_000), _features("ok", liquidity_usd=50_000)]
    result = _apply_filters(rows, min_liquidity=10_000, max_spread=0.10, min_abs_edge_bps=0)
    ids = [r.market_id for r in result]
    assert "low" not in ids
    assert "ok" in ids


def test_filter_max_spread_removes_wide_spread() -> None:
    rows = [_features("wide", spread_pct=0.10), _features("tight", spread_pct=0.02)]
    result = _apply_filters(rows, min_liquidity=0, max_spread=0.05, min_abs_edge_bps=0)
    ids = [r.market_id for r in result]
    assert "wide" not in ids
    assert "tight" in ids


def _feat_with_edge(market_id: str, edge_bps: float) -> MarketFeatures:
    """Build a MarketFeatures with a specific edge_bps for filter unit tests."""
    f = _features(market_id)
    return MarketFeatures(
        market_id=f.market_id,
        question=f.question,
        market_implied_prob_yes=f.market_implied_prob_yes,
        estimated_prob_yes=f.estimated_prob_yes,
        edge_bps=edge_bps,
        expected_value_per_1usd=f.expected_value_per_1usd,
        liquidity_score=f.liquidity_score,
        spread_pct=f.spread_pct,
        volatility_proxy=f.volatility_proxy,
    )


def test_filter_min_abs_edge_bps() -> None:
    rows = [_feat_with_edge("flat", edge_bps=50), _feat_with_edge("edgy", edge_bps=200)]
    result = _apply_filters(rows, min_liquidity=0, max_spread=1.0, min_abs_edge_bps=100)
    ids = [r.market_id for r in result]
    assert "flat" not in ids
    assert "edgy" in ids


def test_filter_all_pass() -> None:
    rows = [_features("m1"), _features("m2")]
    result = _apply_filters(rows, min_liquidity=0, max_spread=1.0, min_abs_edge_bps=0)
    assert len(result) == 2


def test_filter_all_fail() -> None:
    rows = [_features("m1", liquidity_usd=100)]
    result = _apply_filters(rows, min_liquidity=10_000, max_spread=1.0, min_abs_edge_bps=0)
    assert result == []


# ── sorting test ──────────────────────────────────────────────────────────────


def test_sorted_highest_edge_first() -> None:
    rows = [_feat_with_edge("low", edge_bps=100), _feat_with_edge("high", edge_bps=400)]
    rows.sort(key=lambda r: (abs(r.edge_bps), r.expected_value_per_1usd), reverse=True)
    assert rows[0].market_id == "high"


# ── delta tests ───────────────────────────────────────────────────────────────


def test_delta_all_new_when_no_previous(tmp_path: Path) -> None:
    current = [{"market_id": "m1", "edge_bps": 200}]
    delta = _compute_delta(current, tmp_path / "nonexistent.json")
    assert len(delta) == 1
    assert delta[0]["_delta"] == "new"


def test_delta_unchanged_not_included(tmp_path: Path) -> None:
    prev = [{"market_id": "m1", "edge_bps": 200}]
    prev_path = tmp_path / "prev.json"
    prev_path.write_text(json.dumps(prev), encoding="utf-8")
    current = [{"market_id": "m1", "edge_bps": 205}]  # change < 10 bps
    delta = _compute_delta(current, prev_path)
    assert delta == []


def test_delta_changed_included(tmp_path: Path) -> None:
    prev = [{"market_id": "m1", "edge_bps": 200}]
    prev_path = tmp_path / "prev.json"
    prev_path.write_text(json.dumps(prev), encoding="utf-8")
    current = [{"market_id": "m1", "edge_bps": 350}]  # change > 10 bps
    delta = _compute_delta(current, prev_path)
    assert len(delta) == 1
    assert delta[0]["_delta"] == "changed"


def test_delta_new_market_flagged(tmp_path: Path) -> None:
    prev = [{"market_id": "m1", "edge_bps": 200}]
    prev_path = tmp_path / "prev.json"
    prev_path.write_text(json.dumps(prev), encoding="utf-8")
    current = [{"market_id": "m1", "edge_bps": 200}, {"market_id": "m2", "edge_bps": 100}]
    delta = _compute_delta(current, prev_path)
    assert len(delta) == 1
    assert delta[0]["market_id"] == "m2"
    assert delta[0]["_delta"] == "new"


def test_delta_corrupt_previous_treats_all_as_new(tmp_path: Path) -> None:
    prev_path = tmp_path / "bad.json"
    prev_path.write_text("NOT JSON", encoding="utf-8")
    current = [{"market_id": "m1", "edge_bps": 200}]
    delta = _compute_delta(current, prev_path)
    assert delta[0]["_delta"] == "new"


def test_delta_empty_previous_delta_does_not_cause_false_new(tmp_path: Path) -> None:
    """Regression: comparing against an empty delta (not full shortlist) wrongly
    marks all current entries as 'new' every run after a no-change cycle.
    The fix is to always reference the previous *shortlist*, not the previous delta."""
    # Simulate: previous shortlist = [m1], delta was empty (no changes that run)
    prev_shortlist = [{"market_id": "m1", "edge_bps": 200}]
    shortlist_path = tmp_path / "latest_shortlist.json"
    shortlist_path.write_text(json.dumps(prev_shortlist), encoding="utf-8")

    # Current run: same markets, same edge — should produce empty delta
    current = [{"market_id": "m1", "edge_bps": 200}]
    delta = _compute_delta(current, shortlist_path)
    assert delta == [], "Unchanged markets must not appear as 'new' after empty-delta run"
