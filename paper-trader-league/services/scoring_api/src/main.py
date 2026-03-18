import uvicorn
from fastapi import FastAPI, HTTPException

from .db import get_conn

app = FastAPI(title='Paper Trader League Scoring API')


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


@app.get('/leaderboard')
def leaderboard(season_id: str = 'season-001'):
    query = """
    WITH latest AS (
      SELECT DISTINCT ON (bot_id)
        season_id, bot_id, equity_btc, realized_pnl_btc, unrealized_pnl_btc,
        drawdown_pct, trade_count, fee_btc, cash_btc, positions, ts
      FROM bot_metrics
      WHERE season_id = %s
      ORDER BY bot_id, ts DESC
    )
    SELECT * FROM latest ORDER BY equity_btc DESC, realized_pnl_btc DESC, bot_id ASC
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


@app.get('/orders/latest')
def latest_orders(season_id: str = 'season-001', limit: int = 25):
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT id, ts, bot_id, symbol, side, order_type, request_price,
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


if __name__ == '__main__':
    uvicorn.run(app, host='0.0.0.0', port=8090)
