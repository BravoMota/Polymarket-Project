# polyclaude-bot

Python paper-trading Polymarket analyst bot that computes measurable market features, asks Claude for structured `YES`/`NO`/`SKIP` decisions, and logs all decisions for evaluation.

## v1 Scope

- Paper mode only (`PAPER_MODE=true`).
- Quantified decision fields (edge, EV, confidence, liquidity, spread).
- Risk gates before any suggestion is accepted.
- Snapshot, ledger, and report outputs for iteration.

## Quickstart

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -e ".[dev]"
copy .env.example .env
polyclaude paper-run --limit 20
```

## CLI Commands

- `polyclaude scan` - save snapshot batch to `data/snapshots/`.
- `polyclaude decide` - generate decisions and append to ledger.
- `polyclaude paper-run` - run decisions + generate report.
- `polyclaude report` - regenerate report from existing ledger.

## Output Contracts

Each decision includes:
- `action`: `YES | NO | SKIP`
- `confidence`: 0..1
- `estimated_prob_yes`: 0..1
- `market_implied_prob_yes`: 0..1
- `edge_bps`
- `expected_value_per_1usd`
- `liquidity_score`: 0..1
- `risk_flags`
- `rationale_bullets`

## Collaboration Workflow

See `docs/collaboration.md` for branch/PR standards and review checklist.

## Reference Repositories

- [pmxt](https://github.com/pmxt-dev/pmxt)
- [polymarket/agents](https://github.com/polymarket/agents)
- [fastmcp](https://github.com/prefecthq/fastmcp)
- [polymarket-mcp-server](https://github.com/caiovicentino/polymarket-mcp-server)
- [polyrec](https://github.com/txbabaxyz/polyrec)
