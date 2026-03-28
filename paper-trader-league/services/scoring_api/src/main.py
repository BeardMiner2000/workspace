import uvicorn
from fastapi import FastAPI, HTTPException

from .db import get_conn

app = FastAPI(title='Paper Trader League Scoring API')


def get_seasons_with_summary():
    query = """
    WITH latest AS (
      SELECT DISTINCT ON (season_id, bot_id)
        season_id, bot_id, equity_btc, realized_pnl_btc, drawdown_pct, trade_count, ts
      FROM bot_metrics
      ORDER BY season_id, bot_id, ts DESC
    ),
    summaries AS (
      SELECT
        season_id,
        COUNT(*) AS active_bots,
        COALESCE(SUM(equity_btc), 0) AS total_equity_btc,
        COALESCE(SUM(realized_pnl_btc), 0) AS total_realized_pnl_btc,
        COALESCE(SUM(trade_count), 0) AS total_trades,
        MAX(ts) AS last_metric_at
      FROM latest
      GROUP BY season_id
    )
    SELECT
      s.season_id,
      s.status,
      s.base_asset,
      s.starting_equity_btc,
      s.created_at,
      s.started_at,
      s.ended_at,
      COUNT(sb.bot_id) AS bot_count,
      COALESCE(sm.active_bots, 0) AS active_bots,
      COALESCE(sm.total_equity_btc, 0) AS total_equity_btc,
      COALESCE(sm.total_realized_pnl_btc, 0) AS total_realized_pnl_btc,
      COALESCE(sm.total_trades, 0) AS total_trades,
      sm.last_metric_at
    FROM seasons s
    LEFT JOIN season_bots sb ON sb.season_id = s.season_id
    LEFT JOIN summaries sm ON sm.season_id = s.season_id
    GROUP BY
      s.season_id, s.status, s.base_asset, s.starting_equity_btc, s.created_at, s.started_at, s.ended_at,
      sm.active_bots, sm.total_equity_btc, sm.total_realized_pnl_btc, sm.total_trades, sm.last_metric_at
    ORDER BY COALESCE(s.started_at, s.created_at) DESC, s.season_id DESC
    """
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(query)
            return cur.fetchall()


@app.get('/health')
def health():
    try:
        with get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute('SELECT 1 AS ok')
                cur.fetchone()
        return {'ok': True, 'service': 'scoring_api'}
    except Exception as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@app.get('/seasons')
def seasons():
    return {'seasons': get_seasons_with_summary()}


@app.get('/leaderboard')
def leaderboard(season_id: str = 'season-001'):
    query = """
    WITH latest AS (
      SELECT DISTINCT ON (m.bot_id)
        m.season_id, m.bot_id, m.equity_btc, m.realized_pnl_btc, m.unrealized_pnl_btc,
        m.drawdown_pct, m.trade_count, m.fee_btc, m.cash_btc, m.positions, m.ts
      FROM bot_metrics m
      WHERE season_id = %s
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
    """
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(query, (season_id,))
            rows = cur.fetchall()
    return {'season_id': season_id, 'bots': rows}


@app.get('/metrics/latest')
def latest_metrics(season_id: str = 'season-001', limit: int = 50):
    query = """
    SELECT season_id, bot_id, equity_btc, realized_pnl_btc, unrealized_pnl_btc,
           drawdown_pct, trade_count, fee_btc, cash_btc, positions, ts
    FROM bot_metrics
    WHERE season_id = %s
    ORDER BY ts DESC, bot_id ASC
    LIMIT %s
    """
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(query, (season_id, limit))
            rows = cur.fetchall()
    return {'season_id': season_id, 'metrics': rows}


@app.get('/history/equity')
def equity_history(season_id: str = 'season-001', limit: int = 240):
    query = """
    SELECT season_id, bot_id, equity_btc, realized_pnl_btc, drawdown_pct, trade_count, ts
    FROM (
      SELECT season_id, bot_id, equity_btc, realized_pnl_btc, drawdown_pct, trade_count, ts
      FROM bot_metrics
      WHERE season_id = %s
      ORDER BY ts DESC
      LIMIT %s
    ) recent
    ORDER BY ts ASC, bot_id ASC
    """
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(query, (season_id, limit))
            rows = cur.fetchall()
    return {'season_id': season_id, 'history': rows}


@app.get('/orders/latest')
def latest_orders(season_id: str = 'season-001', limit: int = 25):
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT id, ts, season_id, bot_id, symbol, side, order_type, request_price,
                       requested_quantity, executed_price, executed_quantity, status
                FROM bot_orders
                WHERE season_id = %s
                ORDER BY ts DESC, id DESC
                LIMIT %s
                """,
                (season_id, limit),
            )
            rows = cur.fetchall()
    return {'season_id': season_id, 'orders': rows}


@app.get('/dashboard/summary')
def dashboard_summary(season_id: str | None = None, history_limit: int = 240, orders_limit: int = 20):
    seasons = get_seasons_with_summary()
    selected_season_id = season_id or (seasons[0]['season_id'] if seasons else None)

    leaderboard_rows = []
    history_rows = []
    order_rows = []
    if selected_season_id:
        leaderboard_rows = leaderboard(selected_season_id)['bots']
        history_rows = equity_history(selected_season_id, history_limit)['history']
        order_rows = latest_orders(selected_season_id, orders_limit)['orders']

    summary = {
        'total_equity_btc': 0,
        'total_realized_pnl_btc': 0,
        'total_trades': 0,
        'total_bots': 0,
        'last_metric_at': None,
    }
    for season in seasons:
        summary['total_equity_btc'] += float(season['total_equity_btc'] or 0)
        summary['total_realized_pnl_btc'] += float(season['total_realized_pnl_btc'] or 0)
        summary['total_trades'] += int(season['total_trades'] or 0)
        summary['total_bots'] += int(season['active_bots'] or 0)
        if season['last_metric_at'] and (
            summary['last_metric_at'] is None or season['last_metric_at'] > summary['last_metric_at']
        ):
            summary['last_metric_at'] = season['last_metric_at']

    return {
        'meta': {
            'selected_season_id': selected_season_id,
            'available_seasons': len(seasons),
        },
        'seasons': seasons,
        'summary': summary,
        'selectedSeason': next((season for season in seasons if season['season_id'] == selected_season_id), None),
        'leaderboard': leaderboard_rows,
        'equityHistory': history_rows,
        'recentOrders': order_rows,
    }


if __name__ == '__main__':
    uvicorn.run(app, host='0.0.0.0', port=8090)
