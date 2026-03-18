# Paper Trader League

Live, multi-bot paper trading tournament with sentiment-aware strategies, unified execution simulator, and Grafana leaderboard.

## What works now

- Local Docker stack for TimescaleDB, Grafana, trade engine, scoring API, and a placeholder data-ingest worker
- SQL-backed season bootstrap/reset for three bots:
  - `aurora_quanta`
  - `stormchaser_delta`
  - `mercury_micro`
- Trade engine endpoints for:
  - season bootstrap
  - order submission
  - mark-to-market equity refresh
- Immediate paper fills with configurable fee/slippage defaults
- Scoring API endpoints for leaderboard, latest metrics, and latest orders
- Grafana dashboard with leaderboard, equity history, recent metrics, and recent orders

## Architecture (high-level)

```text
Exchanges/API feeds → Data Ingest → Trade Engine / Simulator ← Bot Sandbox (future)
                                                ↓
                                         TimescaleDB → Grafana Leaderboard
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
- mark-to-market depends on submitted prices/marks
- valuation currently assumes `BTC` as the season accounting asset and works best with `BTCUSDT` plus any relevant `*USDT` or `*BTC` marks
- there is no bot SDK yet; the service boundary is now in place for one

## Next logical step

Build a tiny bot client/SDK that can poll market state, submit orders, and write rationale/metadata back into the trade engine.
