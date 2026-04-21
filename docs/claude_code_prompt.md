You are helping build `polyclaude-bot`, a Python paper-trading Polymarket analyst.

Follow `docs/system_design.md`.

Keep outputs strictly measurable and machine-parseable.

For each market snapshot, compute and log:
- implied probability
- estimated probability
- edge in bps
- EV per $1
- spread
- liquidity score
- volatility proxy
- confidence

Produce action as JSON only: `YES`, `NO`, or `SKIP`, with `risk_flags`.

Never execute real trades; `paper_mode=true` is mandatory.

Add tests for each metric and decision threshold.

Prefer small PR-sized commits and update docs for every interface change.
