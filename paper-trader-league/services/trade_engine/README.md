# Trade Engine

Minimal execution simulator for the Paper Trader League.

## Endpoints

- `GET /health`
- `POST /season/bootstrap` — reset season state and seed three bots at 0.05 BTC each
- `POST /marks` — persist latest market marks and recompute metrics
- `POST /orders` — submit a market-style order and immediately simulate a fill with fee/slippage

## Notes

- Current scope is deliberately practical: simple SQL-backed execution, no matching engine.
- Balances are stored as append-only snapshots so Grafana and scoring can query latest state.
- Symbol support is intentionally small and works best with `BTCUSDT` plus any `*USDT` marks needed for valuation.
