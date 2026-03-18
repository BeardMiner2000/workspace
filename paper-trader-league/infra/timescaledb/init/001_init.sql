CREATE EXTENSION IF NOT EXISTS timescaledb;

CREATE TABLE IF NOT EXISTS bot_balances (
  ts TIMESTAMPTZ NOT NULL DEFAULT now(),
  bot_id TEXT NOT NULL,
  asset TEXT NOT NULL,
  free NUMERIC NOT NULL DEFAULT 0,
  locked NUMERIC NOT NULL DEFAULT 0,
  btc_mark_value NUMERIC NOT NULL DEFAULT 0,
  PRIMARY KEY (ts, bot_id, asset)
);

CREATE TABLE IF NOT EXISTS bot_orders (
  id BIGSERIAL PRIMARY KEY,
  ts TIMESTAMPTZ NOT NULL DEFAULT now(),
  bot_id TEXT NOT NULL,
  symbol TEXT NOT NULL,
  side TEXT NOT NULL,
  order_type TEXT NOT NULL,
  price NUMERIC,
  quantity NUMERIC NOT NULL,
  status TEXT NOT NULL,
  rationale JSONB NOT NULL DEFAULT '{}'::jsonb,
  metadata JSONB NOT NULL DEFAULT '{}'::jsonb
);

CREATE TABLE IF NOT EXISTS bot_fills (
  id BIGSERIAL PRIMARY KEY,
  ts TIMESTAMPTZ NOT NULL DEFAULT now(),
  order_id BIGINT REFERENCES bot_orders(id),
  bot_id TEXT NOT NULL,
  symbol TEXT NOT NULL,
  side TEXT NOT NULL,
  fill_price NUMERIC NOT NULL,
  fill_quantity NUMERIC NOT NULL,
  fee_asset TEXT NOT NULL,
  fee_amount NUMERIC NOT NULL DEFAULT 0,
  slippage_bps NUMERIC NOT NULL DEFAULT 0,
  metadata JSONB NOT NULL DEFAULT '{}'::jsonb
);

CREATE TABLE IF NOT EXISTS bot_metrics (
  ts TIMESTAMPTZ NOT NULL DEFAULT now(),
  bot_id TEXT NOT NULL,
  equity_btc NUMERIC NOT NULL,
  realized_pnl_btc NUMERIC NOT NULL DEFAULT 0,
  unrealized_pnl_btc NUMERIC NOT NULL DEFAULT 0,
  drawdown_pct NUMERIC NOT NULL DEFAULT 0,
  trade_count INTEGER NOT NULL DEFAULT 0,
  fee_btc NUMERIC NOT NULL DEFAULT 0,
  PRIMARY KEY (ts, bot_id)
);

SELECT create_hypertable('bot_balances', 'ts', if_not_exists => TRUE);
SELECT create_hypertable('bot_metrics', 'ts', if_not_exists => TRUE);
