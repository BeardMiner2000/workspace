# Local Runbook

## First run

1. Copy env file:
   ```bash
   cp .env.example .env
   ```
2. Start the stack:
   ```bash
   docker compose up --build
   ```
3. Open Grafana:
   - http://localhost:3000
   - default login from `.env`
4. Check service health:
   - Trade engine: http://localhost:8088/health
   - Scoring API: http://localhost:8090/health

## Notes

- Current services are scaffolds only.
- TimescaleDB schema is initialized on first startup.
- Grafana auto-loads the placeholder leaderboard dashboard.
- Review `BOT_PERSONAS.md`, `BOT_STRATEGY_SPECS.md`, and `config/` before implementing strategy logic.
- Next implementation step is wiring DB access and the bot/trade-engine contract.
