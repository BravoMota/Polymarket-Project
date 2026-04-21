# polyclaude-bot — CLAUDE.md

## Role split (critical)

**Bot = data pipeline only.** Fetches, filters, ranks markets, writes handoff files.
**Claude Cowork = decision maker.** Reads handoff files and decides all trades.
Never add trade decision logic to the bot.

## Project state

- `.venv` created, all deps installed (`pip install -e ".[dev]"`)
- 15/15 tests passing (`pytest tests/ -v`)
- Live data flowing from `gamma-api.polymarket.com`
- `export-shortlist` CLI producing real handoff files

## Architecture

```
src/polyclaude_bot/
  cli.py                  # export-shortlist entry point
  data/polymarket_client.py   # live Polymarket API (gamma-api)
  features/feature_engine.py  # MarketFeatures + edge formula
  strategy/decision_engine.py
  risk/risk_guard.py
  paper/ledger.py
  llm/claude_client.py
  eval/

data/handoff/
  latest_shortlist.json   # full ranked shortlist
  latest_shortlist.csv
  latest_delta.json       # only new/changed >10 bps vs prior run

scripts/
  run_cowork_cycle.bat    # hourly pipeline runner
  hourly_scan.bat
```

## Pipeline

```
export-shortlist CLI
  → gamma-api.polymarket.com (active, non-closed markets)
  → filter (liquidity, spread, edge)
  → rank by edge_bps desc
  → write handoff files
  → user pastes into Claude Cowork
```

## Data source

`https://gamma-api.polymarket.com/markets?active=true&closed=false`

Key fields: `outcomePrices` (yes/no prices), `liquidityNum`, `volume24hr`, `id`, `question`.
Spread = `max(1 - yes - no, 0.001)` — gamma returns mid prices, no raw bid/ask.

## Edge formula

`src/polyclaude_bot/features/feature_engine.py`

```python
liquidity_score = snapshot.liquidity_usd / 100000  # capped 0–1
spread_penalty  = snapshot.spread_pct / 0.10        # capped 0–1
adjustment = (liquidity_score - spread_penalty) * 0.10 * implied
estimated  = implied + adjustment
edge_bps   = (estimated - implied) * 10000
```

Adjustment is **proportional to implied** — prevents low-prob markets from getting fake 500 bps edges from the liquidity/spread signal alone. Heuristic baseline until a trained model replaces it.

## Token strategy (Cowork)

1. Read `latest_delta.json` first — only entries new or shifted >10 bps (typically 0–3 items)
2. Fall back to `latest_shortlist.json` only if delta is empty
3. Keep `--top-n` ≤ 5

## CLI reference

```
polyclaude export-shortlist [OPTIONS]
  --limit            INT    Markets to fetch (default: 20)
  --top-n            INT    Top opportunities to export (default: 5)
  --min-liquidity    FLOAT  Min liquidity USD (default: 10000)
  --max-spread       FLOAT  Max spread fraction (default: 0.05)
  --min-abs-edge-bps FLOAT  Min absolute edge bps (default: 50)
```

## Constraints

- `paper_mode=true` always — no live trading ever
- No LLM calls in the pipeline — Cowork is the LLM step
- No paid API usage in `export-shortlist` — pipeline must be free/offline
- Windows 11 — use `.venv\Scripts\python`, `Path()` for paths, BAT syntax for scripts

## Running tests

```
.venv\Scripts\pytest tests/ -v
```

## Before starting a session

Run `start_session.bat` from desktop (starts claude-mem worker + transcript watcher).
