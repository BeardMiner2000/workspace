# Render Hosting Plan

## What changed

The old approach was wrong because it shipped a public page that linked users back to `http://localhost:3000` for Grafana.

The new approach hosts the dashboard itself on Render and pulls live data server-side.

## Recommended production shape

```text
Render public-dashboard service
  -> read-only Postgres connection to the league database
  -> hosted HTML + JSON dashboard
```

This is the simplest setup that satisfies the requirement that the Render URL itself is the live dashboard.

## Alternate shape

If the database cannot be reached from Render, deploy `services/scoring_api` somewhere reachable and set:

```text
SCORING_API_URL=https://your-scoring-api.example.com
```

The dashboard will use that read-only API instead.

## Render setup

1. Push the repo to GitHub.
2. In Render, create a Blueprint or Web Service from `BeardMiner2000/workspace`.
3. If using the blueprint, Render will read `render.yaml` from the repo root.
4. If configuring manually for the dashboard service:
   - Root directory: `public-dashboard`
   - Environment: `Node`
   - Build command: `npm install`
   - Start command: `npm start`
   - Health check path: `/health`
5. Add env vars for one data-source mode:
   - Preferred: `DATABASE_URL`
   - Or fallback: `SCORING_API_URL`
6. Deploy.

## Required external prerequisite

Render must be able to reach a live read-only data source.

That means one of:

- A Postgres instance reachable from Render with a read-only dashboard user
- A deployed `scoring_api` reachable from Render

Without one of those, the dashboard can build but it cannot show live data.

## Suggested read-only Postgres role

```sql
CREATE ROLE paper_dashboard LOGIN PASSWORD 'strong-password';
GRANT CONNECT ON DATABASE paperbot TO paper_dashboard;
GRANT USAGE ON SCHEMA public TO paper_dashboard;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO paper_dashboard;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT ON TABLES TO paper_dashboard;
```

## Validation URLs

- Dashboard health: `/health`
- Dashboard data: `/api/dashboard`
