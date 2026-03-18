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

## 2) Bootstrap a season

```bash
curl -s http://localhost:8088/season/bootstrap \
  -H 'Content-Type: application/json' \
  -d '{"season_id":"season-001","starting_btc":0.05}' | jq
```

## 3) Seed market marks

```bash
curl -s http://localhost:8088/marks \
  -H 'Content-Type: application/json' \
  -d '{"season_id":"season-001","marks":{"BTCUSDT":65000}}' | jq
```

## 4) Submit a sample trade

Sell part of a bot's initial BTC bankroll into USDT:

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
    "rationale":{"note":"risk trim"}
  }' | jq
```

## 5) Inspect standings

```bash
curl -s 'http://localhost:8090/leaderboard?season_id=season-001' | jq
curl -s 'http://localhost:8090/metrics/latest?season_id=season-001&limit=20' | jq
curl -s 'http://localhost:8090/orders/latest?season_id=season-001&limit=20' | jq
```

## 6) Grafana

- Login with `GRAFANA_ADMIN_USER` / `GRAFANA_ADMIN_PASSWORD`
- Open the provisioned `Paper Trader League - Leaderboard Overview` dashboard
- Choose the season from the dashboard variable if more than one exists

## Troubleshooting

### Trade engine/scoring API cannot reach Postgres

- Confirm `.env` exists
- Check `docker compose ps`
- Wait for `timescaledb` to become healthy before expecting API health checks to pass

### Need a hard reset

```bash
docker compose down -v
```

That wipes the local Timescale volume and forces schema re-init on next start.

## Notes for future bot work

- Each bot can remain a separate container/process with its own config and persona docs
- Use the trade engine as the single write path for orders/fills/metrics
- Keep strategy logic outside the scoring API; scoring should stay read-only
