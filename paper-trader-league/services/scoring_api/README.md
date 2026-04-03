# Scoring API

Read-only API for Grafana, the hosted dashboard, and quick inspection.

## Endpoints

- `GET /health`
- `GET /seasons`
- `GET /leaderboard?season_id=season-001`
- `GET /metrics/latest?season_id=season-001&limit=50`
- `GET /history/equity?season_id=season-001&limit=240`
- `GET /orders/latest?season_id=season-001&limit=25`
- `GET /dashboard/summary?season_id=season-001&history_limit=240&orders_limit=20`
- `GET /dashboard/export_s5?season_id=season-005&orders_limit=20&history_days=7`
