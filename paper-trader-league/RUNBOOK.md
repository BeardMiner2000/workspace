# Local Runbook

## 1) Start the stack

```bash
cp .env.example .env
docker compose up --build
```

Services:

- Grafana: http://localhost:3000
- Trade engine: http://localhost:8088
- Scoring API: http://localhost:8090
- TimescaleDB: localhost:5432
- Data/runtime worker: runs inside `data_ingest`

## 2) What happens automatically

By default, `data_ingest` now does three things continuously:

1. bootstraps the configured season on first startup only (and skips bootstrap on restart if the season already exists)
2. generates seeded synthetic market marks for `BTCUSDT`, `ETHUSDT`, `SOLUSDT`, and `DOGEUSDT`
3. runs the three bot heuristics and submits paper orders through the trade engine

So after startup, the leaderboard should begin moving on its own within a few seconds.

## 3) Watch the runtime

```bash
docker compose logs -f data_ingest
```

You should see periodic mark publication plus order activity.

## 4) Inspect standings

```bash
curl -s 'http://localhost:8090/leaderboard?season_id=season-001' | jq
curl -s 'http://localhost:8090/metrics/latest?season_id=season-001&limit=20' | jq
curl -s 'http://localhost:8090/orders/latest?season_id=season-001&limit=20' | jq
```

## 5) Optional manual controls

### Manual season reset

```bash
curl -s http://localhost:8088/season/bootstrap \
  -H 'Content-Type: application/json' \
  -d '{"season_id":"season-001","starting_btc":0.05}' | jq
```

### Manual mark injection

```bash
curl -s http://localhost:8088/marks \
  -H 'Content-Type: application/json' \
  -d '{"season_id":"season-001","marks":{"BTCUSDT":65000,"ETHUSDT":3500}}' | jq
```

### Manual sample trade

```bash
curl -s http://localhost:8088/orders \
  -H 'Content-Type: application/json' \
  -d '{
    "season_id":"season-001",
    "bot_id":"aurora_quanta",
    "symbol":"BTCUSDT",
    "side":"SELL",
    "order_type":"market",
    "quantity":0.01,
    "price":65000,
    "rationale":{"note":"manual risk trim"}
  }' | jq
```

## 6) Grafana

- Login with `GRAFANA_ADMIN_USER` / `GRAFANA_ADMIN_PASSWORD`
- Open the provisioned `Paper Trader League - Leaderboard Overview` dashboard
- Choose the season from the dashboard variable if more than one exists

## 7) Continuity / health check

Run this from the repo root:

```bash
python3 scripts/runtime_healthcheck.py
```

What it checks:

- all core containers are running
- trade engine / scoring API / Grafana health endpoints respond
- the configured season still exists
- bot and market tables are non-empty
- latest `market_marks`, `bot_orders`, and `bot_metrics` timestamps are still fresh
- leaderboard still returns all three bots

Useful options:

```bash
python3 scripts/runtime_healthcheck.py --stale-after-seconds 300
python3 scripts/runtime_healthcheck.py --season-id season-001
```

The script exits non-zero on failure, so it can also be used in cron or other automation.

## 8) Useful env knobs

```env
MARKET_DATA_SOURCE=synthetic
AUTO_BOOTSTRAP_SEASON=true
INGEST_LOOP_SECONDS=5
SYNTHETIC_SEED=42
SYNTHETIC_HISTORY_SIZE=180
```

Notes:

- `MARKET_DATA_SOURCE` is effectively `synthetic` in this pass
- the synthetic tape is deterministic for a fixed seed
- shorter loop intervals create more fills and faster leaderboard movement

## Troubleshooting

### Trade engine/scoring API cannot reach Postgres

- Confirm `.env` exists
- Check `docker compose ps`
- Wait for `timescaledb` to become healthy before expecting API health checks to pass

### Data ingest keeps retrying dependencies

- Confirm `trade_engine` is healthy: `curl -s http://localhost:8088/health`
- Check DB connectivity via `docker compose logs timescaledb trade_engine data_ingest`

### Need a hard reset

```bash
docker compose down -v
```

That wipes the local Timescale volume and forces schema re-init on next start.

## Current limitations

- synthetic data + synthetic event/narrative proxies only
- runtime heuristics are deliberately simple and aggressive
- execution remains immediate-fill simulation
- runtime currently reads balances directly from Postgres but submits all orders through the trade engine
