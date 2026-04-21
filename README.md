# polyclaude-bot

A paper-trading Polymarket analysis pipeline built by **Luís Oliveira** and **Bravo Mota**.

The bot fetches live market data from Polymarket, ranks opportunities by edge, and writes handoff files for Claude to review. **The bot does not make trading decisions** — it surfaces data. Claude (in Cowork mode) reads the handoff files and decides all trades.

## Role Split (Critical)

| Component | Role |
|---|---|
| **Bot (this repo)** | Fetch → filter → rank → write handoff files |
| **Claude Cowork** | Read handoff files → decide all trades |

Never add trade decision logic to the bot.

## How It Works

Every run (manual or hourly via Task Scheduler):

1. Fetches active markets from `gamma-api.polymarket.com`
2. Filters by liquidity (≥ $10k), spread (≤ 5%), edge (≥ 50 bps)
3. Ranks by `edge_bps` descending
4. Writes 3 handoff files to `data/handoff/`:
   - `latest_shortlist.json` — top 5 ranked markets
   - `latest_shortlist.csv` — same as CSV
   - `latest_delta.json` — **only what changed** vs prior run (>10 bps shift)
5. Logs to `data/logs/hourly_scan.log`

Bravo: paste `latest_delta.json` into Claude Cowork to get trade decisions. If delta is empty, fall back to `latest_shortlist.json`.

## Quickstart

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -e ".[dev]"
copy .env.example .env
```

Run the pipeline once:

```bash
polyclaude export-shortlist --limit 200 --top-n 5
```

Output lands in `data/handoff/`.

## CLI Reference

```
polyclaude export-shortlist [OPTIONS]
  --limit            INT    Markets to fetch (default: 20)
  --top-n            INT    Top opportunities to export (default: 5)
  --min-liquidity    FLOAT  Min liquidity USD (default: 10000)
  --max-spread       FLOAT  Max spread fraction (default: 0.05)
  --min-abs-edge-bps FLOAT  Min absolute edge bps (default: 50)
```

Other commands:
- `polyclaude scan` — save raw snapshot to `data/snapshots/`
- `polyclaude report` — regenerate report from existing ledger

## Hourly Automation (Windows)

```
scripts\run_cowork_cycle.bat
```

Wire to Windows Task Scheduler (hourly trigger) to run automatically.

## Cowork Token Strategy

1. Read `latest_delta.json` first — typically 0–3 items
2. Fall back to `latest_shortlist.json` only if delta is empty
3. Prompt template: `prompts/cowork_decide_prompt.txt`
4. Keep `--top-n` ≤ 5

## Edge Formula

```python
liquidity_score = liquidity_usd / 100_000        # capped 0–1
spread_penalty  = spread_pct / 0.10              # capped 0–1
adjustment = (liquidity_score - spread_penalty) * 0.10 * implied_prob
edge_bps   = adjustment * 10_000
```

Proportional to implied probability — prevents low-probability markets from getting artificially inflated edges. Heuristic baseline; a trained model replaces this later.

## Running Tests

```bash
.venv\Scripts\pytest tests/ -v
```

15/15 passing.

## Constraints

- `PAPER_MODE=true` always — no live trading
- No LLM calls in the pipeline — Cowork is the LLM step
- No paid API usage in `export-shortlist` — pipeline is free

## Reference Repositories

- [polymarket/agents](https://github.com/polymarket/agents)
- [polymarket-mcp-server](https://github.com/caiovicentino/polymarket-mcp-server)
