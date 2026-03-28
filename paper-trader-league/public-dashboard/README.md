# Paper Trader League Hosted Dashboard

This app is the production-safe replacement for the old Grafana redirect page.

It serves a live dashboard directly from the Render URL and keeps data access on the server side.

## Architecture

Preferred deployment path:

```text
Render web service (public-dashboard)
  -> server-side reads from reachable Postgres using read-only credentials
  -> returns dashboard JSON and HTML to the browser
```

Fallback deployment path:

```text
Render web service (public-dashboard)
  -> server-side fetches read-only data from scoring_api
  -> returns dashboard JSON and HTML to the browser
```

The browser never talks to localhost, Grafana, or Postgres directly.

## Features

- Live season overview across all tracked seasons
- Season switcher
- Leaderboard table
- Recent orders feed
- Equity history chart
- Server-side cache to reduce DB/API load
- Works with either direct Postgres access or a reachable scoring API

## Local Run

Direct Postgres mode:

```bash
cd public-dashboard
npm install
POSTGRES_HOST=127.0.0.1 POSTGRES_PORT=5432 POSTGRES_USER=paperbot POSTGRES_PASSWORD=paperbot POSTGRES_DB=paperbot npm start
```

Scoring API mode:

```bash
cd public-dashboard
npm install
SCORING_API_URL=http://127.0.0.1:8090 npm start
```

Open `http://127.0.0.1:3001`.

## Environment Variables

- `PORT`: HTTP port for the dashboard service. Default `3001`.
- `DATABASE_URL`: Preferred Postgres connection string for Render.
- `POSTGRES_HOST`, `POSTGRES_PORT`, `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB`: Discrete Postgres settings if not using `DATABASE_URL`.
- `PGSSLMODE`: Set to `require` on managed Postgres when SSL is needed. Set to `disable` locally if required.
- `SCORING_API_URL`: Optional fallback read API URL when direct DB access is not available.
- `SCORING_API_TOKEN`: Optional bearer token for the scoring API.
- `CACHE_TTL_MS`: Server-side cache TTL. Default `15000`.
- `HISTORY_LIMIT`: Number of `bot_metrics` points returned to the chart. Default `240`.
- `ORDERS_LIMIT`: Number of recent orders to show. Default `20`.

## Render Deployment

Use the root [`render.yaml`](../render.yaml) blueprint or configure manually:

- Root directory: `public-dashboard`
- Build command: `npm install`
- Start command: `npm start`
- Health check path: `/health`

Set one of these data source modes:

1. Direct Postgres: set `DATABASE_URL` to a reachable read-only database user.
2. Scoring API fallback: set `SCORING_API_URL` to a reachable deployment of `services/scoring_api`.

Direct Postgres is the better single-service setup.

## Data Safety

- Use a read-only Postgres role for the dashboard.
- Do not expose DB credentials to the browser.
- Do not point the app at local Grafana or `localhost` in production.
