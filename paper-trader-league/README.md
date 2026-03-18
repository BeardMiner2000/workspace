# Paper Trader League

Live, multi-bot paper trading tournament with sentiment-aware strategies, unified execution simulator, and Grafana leaderboard.

## What works now

- Local Docker stack for TimescaleDB, Grafana, trade engine, scoring API, and a data-ingest/runtime worker
- SQL-backed season bootstrap/reset for three bots:
  - `aurora_quanta`
  - `stormchaser_delta`
  - `mercury_vanta`
- Trade engine endpoints for:
  - season bootstrap
  - order submission
  - mark-to-market equity refresh
- Immediate paper fills with configurable fee/slippage defaults
- Scoring API endpoints for leaderboard, latest metrics, and latest orders
- Grafana dashboard with leaderboard, equity history, recent metrics, and recent orders
- Synthetic market mark generator that continuously publishes `BTCUSDT`, `ETHUSDT`, `SOLUSDT`, and `DOGEUSDT`
- First-pass bot runtime heuristics wired through the trade engine so orders, fills, balances, and metrics all update live

## What is real vs synthetic in this pass

### Real
- Timescale-backed season state, balances, marks, fills, and metrics
- Trade engine order handling and mark-to-market refresh
- Scoring API and Grafana leaderboard
- Continuous runtime loop that places real paper orders against the simulator

### Synthetic
- Market data is currently deterministic synthetic tape, not exchange live data
- "Narrative" and "event" inputs are synthetic proxies derived from seeded pulses/shocks rather than live news APIs
- Execution is still immediate-fill simulation, not a queue/matching engine

That trade-off is intentional: the league now actually runs end-to-end instead of waiting on paid/fragile live integrations.

## Architecture (high-level)

```text
Synthetic market/runtime worker → Trade Engine / Simulator ← Bot heuristics
                          ↓                    ↓
                     TimescaleDB → Scoring API / Grafana Leaderboard
```

## Repo layout

```text
bots/
config/
infra/
services/
  data_ingest/
  trade_engine/
  scoring_api/
BOT_LEAGUE_SPEC.md
BOT_PERSONAS.md
BOT_STRATEGY_SPECS.md
docker-compose.yml
.env.example
RUNBOOK.md
```

## Runtime heuristics in this pass

- **Aurora Quanta**
  - conviction swing logic
  - rotates into `ETHUSDT` / `SOLUSDT` when relative strength vs BTC and synthetic narrative regime align
  - exits on thesis deterioration / narrative breakdown
- **StormChaser Delta**
  - event-driven breakout logic
  - chases fast momentum in `SOLUSDT`, `DOGEUSDT`, or `ETHUSDT` when synthetic catalyst and volatility pulse line up
  - cuts quickly on momentum failure
- **Mercury Vanta**
  - short-horizon mean reversion / expectancy logic
  - buys local overextensions downward when near-term expectancy exceeds friction
  - exits rapidly when edge decays or price snaps back

## Current service contracts

### Trade engine

- `GET /health`
- `POST /season/bootstrap`
- `POST /marks`
- `POST /orders`

### Scoring API

- `GET /health`
- `GET /leaderboard`
- `GET /metrics/latest`
- `GET /orders/latest`

## Practical limitations

This pass is intentionally simple:

- fills are immediate, not queue-based
- market data is synthetic and seeded for repeatable local runs
- valuation still assumes `BTC` as the season accounting asset
- the runtime reads state from the DB and writes orders through the trade engine; there is not yet a dedicated bot SDK/service boundary
- heuristics are first-pass persona-aligned rules, not production alpha models

## Next logical steps

- swap synthetic proxies for lightweight live feeds where free sources are reliable enough
- add cooldown/risk budget config per bot
- expose richer read endpoints so the runtime no longer needs direct DB reads
- split bot runtime into separate per-bot services if/when isolation matters
