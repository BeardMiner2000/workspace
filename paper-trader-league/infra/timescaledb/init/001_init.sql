CREATE EXTENSION IF NOT EXISTS timescaledb;

CREATE TABLE IF NOT EXISTS seasons (
  season_id TEXT PRIMARY KEY,
  status TEXT NOT NULL DEFAULT 'draft',
  base_asset TEXT NOT NULL DEFAULT 'BTC',
  starting_equity_btc NUMERIC NOT NULL DEFAULT 0.05,
  notes JSONB NOT NULL DEFAULT '{}'::jsonb,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  started_at TIMESTAMPTZ,
  ended_at TIMESTAMPTZ
);

CREATE TABLE IF NOT EXISTS season_bots (
  season_id TEXT NOT NULL REFERENCES seasons(season_id) ON DELETE CASCADE,
  bot_id TEXT NOT NULL,
  bot_name TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'ready',
  config JSONB NOT NULL DEFAULT '{}'::jsonb,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  PRIMARY KEY (season_id, bot_id)
);

CREATE TABLE IF NOT EXISTS bot_balances (
  ts TIMESTAMPTZ NOT NULL DEFAULT now(),
  season_id TEXT NOT NULL,
  bot_id TEXT NOT NULL,
  asset TEXT NOT NULL,
  free NUMERIC NOT NULL DEFAULT 0,
  locked NUMERIC NOT NULL DEFAULT 0,
  btc_mark_value NUMERIC NOT NULL DEFAULT 0,
  PRIMARY KEY (ts, season_id, bot_id, asset)
);

CREATE TABLE IF NOT EXISTS bot_orders (
  id BIGSERIAL PRIMARY KEY,
  ts TIMESTAMPTZ NOT NULL DEFAULT now(),
  season_id TEXT NOT NULL,
  bot_id TEXT NOT NULL,
  symbol TEXT NOT NULL,
  side TEXT NOT NULL,
  order_type TEXT NOT NULL,
  request_price NUMERIC,
  requested_quantity NUMERIC NOT NULL,
  executed_price NUMERIC,
  executed_quantity NUMERIC NOT NULL DEFAULT 0,
  status TEXT NOT NULL,
  rationale JSONB NOT NULL DEFAULT '{}'::jsonb,
  metadata JSONB NOT NULL DEFAULT '{}'::jsonb
);

CREATE TABLE IF NOT EXISTS bot_fills (
  id BIGSERIAL PRIMARY KEY,
  ts TIMESTAMPTZ NOT NULL DEFAULT now(),
  season_id TEXT NOT NULL,
  order_id BIGINT REFERENCES bot_orders(id) ON DELETE CASCADE,
  bot_id TEXT NOT NULL,
  symbol TEXT NOT NULL,
  side TEXT NOT NULL,
  fill_price NUMERIC NOT NULL,
  fill_quantity NUMERIC NOT NULL,
  fee_asset TEXT NOT NULL,
  fee_amount NUMERIC NOT NULL DEFAULT 0,
  fee_btc NUMERIC NOT NULL DEFAULT 0,
  slippage_bps NUMERIC NOT NULL DEFAULT 0,
  metadata JSONB NOT NULL DEFAULT '{}'::jsonb
);

CREATE TABLE IF NOT EXISTS bot_metrics (
  ts TIMESTAMPTZ NOT NULL DEFAULT now(),
  season_id TEXT NOT NULL,
  bot_id TEXT NOT NULL,
  equity_btc NUMERIC NOT NULL,
  realized_pnl_btc NUMERIC NOT NULL DEFAULT 0,
  unrealized_pnl_btc NUMERIC NOT NULL DEFAULT 0,
  drawdown_pct NUMERIC NOT NULL DEFAULT 0,
  trade_count INTEGER NOT NULL DEFAULT 0,
  fee_btc NUMERIC NOT NULL DEFAULT 0,
  cash_btc NUMERIC NOT NULL DEFAULT 0,
  positions JSONB NOT NULL DEFAULT '{}'::jsonb,
  PRIMARY KEY (ts, season_id, bot_id)
);

CREATE TABLE IF NOT EXISTS market_marks (
  ts TIMESTAMPTZ NOT NULL DEFAULT now(),
  season_id TEXT NOT NULL,
  symbol TEXT NOT NULL,
  mark_price NUMERIC NOT NULL,
  PRIMARY KEY (ts, season_id, symbol)
);

SELECT create_hypertable('bot_balances', 'ts', if_not_exists => TRUE);
SELECT create_hypertable('bot_metrics', 'ts', if_not_exists => TRUE);
SELECT create_hypertable('market_marks', 'ts', if_not_exists => TRUE);
