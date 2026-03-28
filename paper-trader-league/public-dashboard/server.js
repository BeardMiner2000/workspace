const express = require('express');
const fetch = require('node-fetch');
const path = require('path');
const { Pool, types } = require('pg');

types.setTypeParser(20, (value) => Number(value));
types.setTypeParser(1700, (value) => Number(value));

const app = express();
const PORT = Number(process.env.PORT || 3001);
const CACHE_TTL_MS = Number(process.env.CACHE_TTL_MS || 15000);
const HISTORY_LIMIT = Number(process.env.HISTORY_LIMIT || 240);
const ORDERS_LIMIT = Number(process.env.ORDERS_LIMIT || 20);

const SCORING_API_URL = (process.env.SCORING_API_URL || '').replace(/\/$/, '');
const SCORING_API_TOKEN = process.env.SCORING_API_TOKEN || '';

const dbConfig = process.env.DATABASE_URL
  ? {
      connectionString: process.env.DATABASE_URL,
      ssl: process.env.PGSSLMODE === 'disable' ? false : { rejectUnauthorized: false },
    }
  : process.env.POSTGRES_HOST
    ? {
        host: process.env.POSTGRES_HOST,
        port: Number(process.env.POSTGRES_PORT || 5432),
        user: process.env.POSTGRES_USER || 'paperbot',
        password: process.env.POSTGRES_PASSWORD || 'paperbot',
        database: process.env.POSTGRES_DB || 'paperbot',
        ssl: process.env.PGSSLMODE === 'require' ? { rejectUnauthorized: false } : false,
      }
    : null;

const pool = dbConfig ? new Pool(dbConfig) : null;
const cache = new Map();

app.use(express.static(path.join(__dirname, 'public')));

function cacheKey(seasonId, historyLimit, ordersLimit) {
  return JSON.stringify({ seasonId, historyLimit, ordersLimit, source: dataSource() });
}

function dataSource() {
  if (pool) {
    return 'postgres';
  }
  if (SCORING_API_URL) {
    return 'scoring_api';
  }
  return 'unconfigured';
}

async function withCache(key, loader) {
  const now = Date.now();
  const hit = cache.get(key);
  if (hit && hit.expiresAt > now) {
    return hit.value;
  }
  const value = await loader();
  cache.set(key, { value, expiresAt: now + CACHE_TTL_MS });
  return value;
}

async function query(sql, params = []) {
  if (!pool) {
    throw new Error('Postgres data source is not configured');
  }
  const result = await pool.query(sql, params);
  return result.rows;
}

async function fetchJson(url) {
  const headers = { Accept: 'application/json' };
  if (SCORING_API_TOKEN) {
    headers.Authorization = `Bearer ${SCORING_API_TOKEN}`;
  }
  const response = await fetch(url, { headers });
  if (!response.ok) {
    const body = await response.text();
    throw new Error(`Scoring API ${response.status}: ${body}`);
  }
  return response.json();
}

async function getDashboardFromScoringApi(seasonId, historyLimit, ordersLimit) {
  const params = new URLSearchParams();
  if (seasonId) {
    params.set('season_id', seasonId);
  }
  params.set('history_limit', String(historyLimit));
  params.set('orders_limit', String(ordersLimit));
  const url = `${SCORING_API_URL}/dashboard/summary?${params.toString()}`;
  const payload = await fetchJson(url);
  return {
    ...payload,
    meta: {
      ...payload.meta,
      data_source: 'scoring_api',
      generated_at: new Date().toISOString(),
    },
  };
}

async function getDashboardFromPostgres(seasonId, historyLimit, ordersLimit) {
  const seasons = await query(
    `
    SELECT
      s.season_id,
      s.status,
      s.base_asset,
      s.starting_equity_btc,
      s.created_at,
      s.started_at,
      s.ended_at,
      COUNT(sb.bot_id) AS bot_count
    FROM seasons s
    LEFT JOIN season_bots sb ON sb.season_id = s.season_id
    GROUP BY s.season_id, s.status, s.base_asset, s.starting_equity_btc, s.created_at, s.started_at, s.ended_at
    ORDER BY COALESCE(s.started_at, s.created_at) DESC, s.season_id DESC
    `,
  );

  if (seasons.length === 0) {
    return {
      meta: {
        data_source: 'postgres',
        generated_at: new Date().toISOString(),
        selected_season_id: null,
        available_seasons: 0,
      },
      seasons: [],
      summary: {
        total_equity_btc: 0,
        total_realized_pnl_btc: 0,
        total_trades: 0,
        total_bots: 0,
        last_metric_at: null,
      },
      selectedSeason: null,
      leaderboard: [],
      equityHistory: [],
      recentOrders: [],
    };
  }

  const selectedSeasonId = seasonId || seasons[0].season_id;

  const [seasonSummaries, leaderboard, equityHistory, recentOrders] = await Promise.all([
    query(
      `
      WITH latest AS (
        SELECT DISTINCT ON (season_id, bot_id)
          season_id, bot_id, equity_btc, realized_pnl_btc, drawdown_pct, trade_count, ts
        FROM bot_metrics
        ORDER BY season_id, bot_id, ts DESC
      )
      SELECT
        season_id,
        COUNT(*) AS active_bots,
        COALESCE(SUM(equity_btc), 0) AS total_equity_btc,
        COALESCE(SUM(realized_pnl_btc), 0) AS total_realized_pnl_btc,
        COALESCE(SUM(trade_count), 0) AS total_trades,
        MAX(ts) AS last_metric_at
      FROM latest
      GROUP BY season_id
      `,
    ),
    query(
      `
      WITH latest AS (
        SELECT DISTINCT ON (m.bot_id)
          m.season_id,
          m.bot_id,
          m.equity_btc,
          m.realized_pnl_btc,
          m.unrealized_pnl_btc,
          m.drawdown_pct,
          m.trade_count,
          m.fee_btc,
          m.cash_btc,
          m.positions,
          m.ts
        FROM bot_metrics m
        WHERE m.season_id = $1
        ORDER BY m.bot_id, m.ts DESC
      )
      SELECT
        l.season_id,
        l.bot_id,
        COALESCE(sb.bot_name, l.bot_id) AS bot_name,
        l.equity_btc,
        l.realized_pnl_btc,
        l.unrealized_pnl_btc,
        l.drawdown_pct,
        l.trade_count,
        l.fee_btc,
        l.cash_btc,
        l.positions,
        l.ts
      FROM latest l
      LEFT JOIN season_bots sb ON sb.season_id = l.season_id AND sb.bot_id = l.bot_id
      ORDER BY l.equity_btc DESC, l.realized_pnl_btc DESC, l.bot_id ASC
      `,
      [selectedSeasonId],
    ),
    query(
      `
      SELECT season_id, bot_id, equity_btc, realized_pnl_btc, drawdown_pct, trade_count, ts
      FROM (
        SELECT season_id, bot_id, equity_btc, realized_pnl_btc, drawdown_pct, trade_count, ts
        FROM bot_metrics
        WHERE season_id = $1
        ORDER BY ts DESC
        LIMIT $2
      ) recent
      ORDER BY ts ASC, bot_id ASC
      `,
      [selectedSeasonId, historyLimit],
    ),
    query(
      `
      SELECT
        id,
        ts,
        season_id,
        bot_id,
        symbol,
        side,
        order_type,
        request_price,
        requested_quantity,
        executed_price,
        executed_quantity,
        status
      FROM bot_orders
      WHERE season_id = $1
      ORDER BY ts DESC, id DESC
      LIMIT $2
      `,
      [selectedSeasonId, ordersLimit],
    ),
  ]);

  const summaryBySeasonId = new Map(seasonSummaries.map((row) => [row.season_id, row]));
  const enrichedSeasons = seasons.map((season) => {
    const seasonSummary = summaryBySeasonId.get(season.season_id) || {};
    return {
      ...season,
      active_bots: seasonSummary.active_bots || 0,
      total_equity_btc: seasonSummary.total_equity_btc || 0,
      total_realized_pnl_btc: seasonSummary.total_realized_pnl_btc || 0,
      total_trades: seasonSummary.total_trades || 0,
      last_metric_at: seasonSummary.last_metric_at || null,
    };
  });

  const globalSummary = enrichedSeasons.reduce(
    (acc, season) => {
      acc.total_equity_btc += Number(season.total_equity_btc || 0);
      acc.total_realized_pnl_btc += Number(season.total_realized_pnl_btc || 0);
      acc.total_trades += Number(season.total_trades || 0);
      acc.total_bots += Number(season.active_bots || 0);
      if (!acc.last_metric_at || (season.last_metric_at && season.last_metric_at > acc.last_metric_at)) {
        acc.last_metric_at = season.last_metric_at;
      }
      return acc;
    },
    {
      total_equity_btc: 0,
      total_realized_pnl_btc: 0,
      total_trades: 0,
      total_bots: 0,
      last_metric_at: null,
    },
  );

  return {
    meta: {
      data_source: 'postgres',
      generated_at: new Date().toISOString(),
      selected_season_id: selectedSeasonId,
      available_seasons: enrichedSeasons.length,
    },
    seasons: enrichedSeasons,
    summary: globalSummary,
    selectedSeason: enrichedSeasons.find((season) => season.season_id === selectedSeasonId) || null,
    leaderboard,
    equityHistory,
    recentOrders,
  };
}

async function getDashboardData(seasonId, historyLimit = HISTORY_LIMIT, ordersLimit = ORDERS_LIMIT) {
  const source = dataSource();
  if (source === 'postgres') {
    return getDashboardFromPostgres(seasonId, historyLimit, ordersLimit);
  }
  if (source === 'scoring_api') {
    return getDashboardFromScoringApi(seasonId, historyLimit, ordersLimit);
  }
  throw new Error('No data source configured. Set DATABASE_URL or POSTGRES_* or SCORING_API_URL.');
}

app.get('/health', async (req, res) => {
  try {
    if (pool) {
      await query('SELECT 1 AS ok');
    } else if (SCORING_API_URL) {
      await fetchJson(`${SCORING_API_URL}/health`);
    }
    res.json({ ok: true, service: 'public_dashboard', data_source: dataSource() });
  } catch (error) {
    res.status(503).json({ ok: false, service: 'public_dashboard', error: error.message });
  }
});

app.get('/api/dashboard', async (req, res) => {
  const seasonId = req.query.season_id || '';
  const historyLimit = Number(req.query.history_limit || HISTORY_LIMIT);
  const ordersLimit = Number(req.query.orders_limit || ORDERS_LIMIT);
  const key = cacheKey(seasonId, historyLimit, ordersLimit);

  try {
    const payload = await withCache(key, () => getDashboardData(seasonId, historyLimit, ordersLimit));
    res.json(payload);
  } catch (error) {
    console.error('Dashboard load failed:', error);
    res.status(503).json({
      error: 'Failed to load dashboard data',
      detail: error.message,
      data_source: dataSource(),
    });
  }
});

app.get('*', (req, res, next) => {
  if (req.path.startsWith('/api/') || req.path === '/health') {
    next();
    return;
  }
  res.sendFile(path.join(__dirname, 'public', 'index.html'));
});

app.listen(PORT, () => {
  console.log(`Public dashboard server running on port ${PORT}`);
  console.log(`Data source: ${dataSource()}`);
});
