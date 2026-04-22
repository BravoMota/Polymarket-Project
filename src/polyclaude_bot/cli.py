from __future__ import annotations

import json
from pathlib import Path

import typer
from rich import print

from polyclaude_bot.config import Settings
from polyclaude_bot.data.polymarket_client import PolymarketClient
from polyclaude_bot.eval.backtest import summarize_ledger
from polyclaude_bot.eval.calibration import calibration_proxy
from polyclaude_bot.features.feature_engine import MarketFeatures, compute_features
from polyclaude_bot.llm.claude_client import ClaudeClient
from polyclaude_bot.llm.prompt_templates import build_decision_prompt
from polyclaude_bot.paper.ledger import append_entry
from polyclaude_bot.risk.risk_guard import evaluate_risk
from polyclaude_bot.strategy.decision_engine import default_decision, enforce_risk

app = typer.Typer(help="Paper-trading Polymarket Claude analyst")


@app.command()
def scan(limit: int | None = None) -> None:
    settings = Settings()
    client = PolymarketClient()
    markets = client.fetch_markets(limit=limit or settings.scan_limit)
    outfile = client.persist_snapshot_batch(markets, settings.snapshot_dir)
    print(f"[green]Saved snapshot:[/green] {outfile}")


@app.command()
def decide(limit: int | None = None) -> None:
    settings = Settings()
    data = PolymarketClient()
    llm = ClaudeClient(settings.anthropic_api_key, settings.claude_model)
    markets = data.fetch_markets(limit=limit or settings.scan_limit)
    for m in markets:
        features = compute_features(m)
        fallback = default_decision(
            implied=features.market_implied_prob_yes,
            estimated=features.estimated_prob_yes,
            edge_bps=features.edge_bps,
            ev=features.expected_value_per_1usd,
            liquidity_score=features.liquidity_score,
        )
        prompt = build_decision_prompt(features)
        decision = llm.decide(prompt, fallback=fallback)
        flags = evaluate_risk(features, decision, settings)
        decision = enforce_risk(decision, flags)
        append_entry(settings.ledger_path, features, decision)
        print(
            f"[cyan]{features.market_id}[/cyan] {decision.action} "
            f"edge={decision.edge_bps} confidence={decision.confidence:.2f} flags={decision.risk_flags}"
        )


@app.command("paper-run")
def paper_run(limit: int | None = None) -> None:
    decide(limit=limit)
    report()


@app.command()
def report() -> None:
    settings = Settings()
    summary = summarize_ledger(settings.ledger_path)
    calib = calibration_proxy(settings.ledger_path)
    payload = {"summary": summary, "calibration": calib}
    out = Path(settings.report_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(f"[green]Wrote report:[/green] {out}")
    print(json.dumps(payload, indent=2))


_LIQUIDITY_SCORE_DENOM = 100_000.0
_DELTA_THRESHOLD_BPS = 10.0


def _apply_filters(
    rows: list[MarketFeatures],
    *,
    min_liquidity: float,
    max_spread: float,
    min_abs_edge_bps: float,
) -> list[MarketFeatures]:
    return [
        r
        for r in rows
        if r.liquidity_score * _LIQUIDITY_SCORE_DENOM >= min_liquidity
        and r.spread_pct <= max_spread
        and abs(r.edge_bps) >= min_abs_edge_bps
    ]


def _compute_delta(
    current: list[dict],
    previous_path: Path,
) -> list[dict]:
    try:
        parsed = json.loads(Path(previous_path).read_text(encoding="utf-8"))
        prev_map: dict[str, float] | None = {
            row["market_id"]: float(row.get("edge_bps", 0.0))
            for row in parsed
            if isinstance(row, dict) and "market_id" in row
        }
    except (FileNotFoundError, OSError, json.JSONDecodeError, TypeError, ValueError):
        prev_map = None

    out: list[dict] = []
    for row in current:
        mid = row.get("market_id")
        edge = float(row.get("edge_bps", 0.0))
        if prev_map is None or mid not in prev_map:
            out.append({**row, "_delta": "new"})
            continue
        if abs(edge - prev_map[mid]) > _DELTA_THRESHOLD_BPS:
            out.append({**row, "_delta": "changed"})
    return out


if __name__ == "__main__":
    app()
