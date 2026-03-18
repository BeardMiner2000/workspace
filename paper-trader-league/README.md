# Paper Trader League

Live, multi-bot paper trading tournament with sentiment-aware strategies, unified execution simulator, and Grafana leaderboard.

## Goals

- Run at least three distinct trading agents (“bots”) with different data inputs and risk appetites
- Paper trade continuously for 3-day “seasons,” starting each bot with 0.05 BTC
- Track performance (BTC-denominated) after fees/slippage; store full trade history
- Surface real-time standings and analytics via Grafana
- Archive all data for post-season reports

## Architecture (high-level)

```
Exchanges/API feeds → Data Ingest → Trade Engine / Simulator ← Bot Sandbox (Docker)
                                                ↓
                                         TimescaleDB → Grafana Leaderboard
```

- **Data Ingest** – Streams price/order book data (CCXT Pro), plus macro/news/sentiment feeds.
- **Trade Engine** – Normalizes orders, simulates fills, applies fees, records ledger events.
- **Bots** – Each bot container subscribes to state updates and submits orders via a simple SDK/API.
- **Scoring API** – Exposes metrics/leaderboard endpoints for Grafana and reports.
- **Storage** – TimescaleDB (Postgres) for trades/balances/metrics + raw logs for narrative reporting.

## Repo layout

```
bots/
  aurora_quanta/
  stormchaser_delta/
  mercury_micro/
services/
  data_ingest/
  trade_engine/
  scoring_api/
infra/
  grafana/
  timescaledb/
docker-compose.yml
.env.example
```

## Next steps

1. Flesh out service contracts (order submission, market data schema).
2. Implement Timescale schema + migrations.
3. Build bot SDK and plug in first strategy prototypes.
4. Configure Grafana dashboards + alerting.
5. Document runbook + GitHub actions for deployment.
