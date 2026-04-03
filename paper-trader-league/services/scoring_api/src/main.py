import uvicorn
from fastapi import FastAPI, HTTPException

from .db import get_conn

app = FastAPI(title='Paper Trader League Scoring API')

S5_BOTS = [
    {'id': 'loser_reversal_hunter', 'name': 'Loser Reversal Hunter', 'emoji': '🔄', 'color': '#10b981'},
    {'id': 'chaos_prophet', 'name': 'Chaos Prophet', 'emoji': '🔮', 'color': '#eab308'},
    {'id': 'pump_surfer', 'name': 'Pump Surfer', 'emoji': '🏄', 'color': '#3b82f6'},
    {'id': 'obsidian_flux', 'name': 'Obsidian Flux', 'emoji': '⚫', 'color': '#ec4899'},
]
S5_BOT_IDS = [bot['id'] for bot in S5_BOTS]
S5_MARKET_SYMBOLS = ['BTCUSDT', 'ETHUSDT', 'SOLUSDT', 'DOGEUSDT']
SATOSHIS_PER_BTC = 100_000_000


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


@app.get('/dashboard/export_s5')
def export_s5_dashboard(season_id: str = 'season-005', orders_limit: int = 20, history_days: int = 7):
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                WITH latest_metrics AS (
                    SELECT DISTINCT ON (bot_id)
                        bot_id,
                        equity_btc,
                        realized_pnl_btc,
                        trade_count,
                        ts
                    FROM bot_metrics
                    WHERE season_id = %s AND bot_id = ANY(%s)
                    ORDER BY bot_id, ts DESC
                ),
                equity_context AS (
                    SELECT
                        m.bot_id,
                        m.equity_btc,
                        m.realized_pnl_btc,
                        m.trade_count,
                        m.ts,
                        s.starting_equity_btc,
                        latest_btc.mark_price AS btc_usd
                    FROM latest_metrics m
                    JOIN seasons s ON s.season_id = %s
                    LEFT JOIN LATERAL (
                        SELECT mark_price
                        FROM market_marks
                        WHERE season_id = %s AND symbol = 'BTCUSDT'
                        ORDER BY ts DESC
                        LIMIT 1
                    ) latest_btc ON true
                ),
                order_stats AS (
                    SELECT
                        bot_id,
                        COUNT(*) AS orders_count,
                        COUNT(*) FILTER (WHERE status = 'filled') AS fills_count,
                        COUNT(*) FILTER (WHERE status NOT IN ('filled', 'canceled', 'rejected', 'expired')) AS open_orders
                    FROM bot_orders
                    WHERE season_id = %s AND bot_id = ANY(%s)
                    GROUP BY bot_id
                ),
                top_symbols AS (
                    SELECT DISTINCT ON (bot_id)
                        bot_id,
                        symbol,
                        COUNT(*) OVER (PARTITION BY bot_id, symbol) AS symbol_count
                    FROM bot_orders
                    WHERE season_id = %s AND bot_id = ANY(%s)
                    ORDER BY bot_id, symbol_count DESC, symbol ASC
                )
                SELECT
                    e.bot_id,
                    COALESCE(o.orders_count, 0) AS orders_count,
                    COALESCE(o.fills_count, 0) AS fills_count,
                    COALESCE(o.open_orders, 0) AS open_orders,
                    e.trade_count,
                    e.equity_btc,
                    e.realized_pnl_btc,
                    e.starting_equity_btc,
                    e.btc_usd,
                    e.ts,
                    t.symbol AS top_symbol
                FROM equity_context e
                LEFT JOIN order_stats o ON o.bot_id = e.bot_id
                LEFT JOIN top_symbols t ON t.bot_id = e.bot_id
                ORDER BY e.bot_id ASC
                """,
                (season_id, S5_BOT_IDS, season_id, season_id, season_id, S5_BOT_IDS, season_id, S5_BOT_IDS),
            )
            metric_rows = cur.fetchall()

            cur.execute(
                """
                SELECT
                    ts,
                    bot_id,
                    symbol,
                    side,
                    status,
                    COALESCE(executed_price, request_price) AS price,
                    COALESCE(executed_quantity, requested_quantity) AS quantity,
                    simulated_fee,
                    rationale,
                    metadata
                FROM bot_orders
                WHERE season_id = %s AND bot_id = ANY(%s)
                ORDER BY ts DESC, id DESC
                LIMIT %s
                """,
                (season_id, S5_BOT_IDS, orders_limit),
            )
            recent_orders = cur.fetchall()

            cur.execute(
                """
                SELECT
                    ts,
                    bot_id,
                    symbol,
                    side,
                    status,
                    COALESCE(executed_price, request_price) AS price,
                    COALESCE(executed_quantity, requested_quantity) AS quantity,
                    simulated_fee,
                    rationale,
                    metadata
                FROM bot_orders
                WHERE season_id = %s AND bot_id = ANY(%s)
                  AND ts >= NOW() - (%s || ' days')::interval
                ORDER BY ts DESC, id DESC
                LIMIT 1000
                """,
                (season_id, S5_BOT_IDS, history_days),
            )
            order_history = cur.fetchall()

            cur.execute(
                """
                WITH sampled AS (
                    SELECT
                        bot_id,
                        date_trunc('minute', ts) AS bucket_ts,
                        AVG(equity_btc) AS equity_btc
                    FROM bot_metrics
                    WHERE season_id = %s
                      AND bot_id = ANY(%s)
                      AND ts >= NOW() - (%s || ' days')::interval
                    GROUP BY bot_id, date_trunc('minute', ts)
                ),
                latest_btc AS (
                    SELECT mark_price
                    FROM market_marks
                    WHERE season_id = %s AND symbol = 'BTCUSDT'
                    ORDER BY ts DESC
                    LIMIT 1
                )
                SELECT
                    s.bot_id,
                    s.bucket_ts,
                    s.equity_btc,
                    b.mark_price AS btc_usd
                FROM sampled s
                CROSS JOIN latest_btc b
                ORDER BY s.bucket_ts ASC, s.bot_id ASC
                """,
                (season_id, S5_BOT_IDS, history_days, season_id),
            )
            equity_history_rows = cur.fetchall()

            cur.execute(
                """
                WITH sampled AS (
                    SELECT
                        symbol,
                        date_trunc('minute', ts) AS bucket_ts,
                        AVG(mark_price) AS mark_price
                    FROM market_marks
                    WHERE season_id = %s
                      AND symbol = ANY(%s)
                      AND ts >= NOW() - (%s || ' days')::interval
                    GROUP BY symbol, date_trunc('minute', ts)
                )
                SELECT symbol, bucket_ts, mark_price
                FROM sampled
                ORDER BY bucket_ts ASC, symbol ASC
                """,
                (season_id, S5_MARKET_SYMBOLS, history_days),
            )
            market_history_rows = cur.fetchall()

    def serialize_order(row):
        rationale = row.get('rationale') or {}
        metadata = row.get('metadata') or {}
        strategy = rationale.get('strategy') or metadata.get('strategy')
        note = rationale.get('note') or rationale.get('exit_reason')
        category = 'strategy_trade'
        if strategy == 'btc_reserve_refill_v1' or note == 'refill_usdt_liquidity':
            category = 'reserve_refill'
        return {
            'ts': row['ts'].isoformat() if row.get('ts') else None,
            'bot_id': row.get('bot_id'),
            'symbol': row.get('symbol'),
            'side': row.get('side'),
            'status': row.get('status'),
            'price': float(row.get('price') or 0),
            'quantity': float(row.get('quantity') or 0),
            'fee': float(row.get('simulated_fee') or 0),
            'strategy': strategy,
            'note': note,
            'category': category,
            'rationale': rationale,
            'metadata': metadata,
        }

    rows_by_bot = {row['bot_id']: row for row in metric_rows}
    traded_symbols = set()
    total_orders = 0
    total_fills = 0
    total_current_btc = 0.0
    total_start_btc = 0.0
    latest_btc_usd = 0.0
    bots = []

    for bot in S5_BOTS:
        row = rows_by_bot.get(bot['id']) or {}
        starting_btc = float(row.get('starting_equity_btc') or 0)
        equity_btc = float(row.get('equity_btc') or 0)
        btc_usd = float(row.get('btc_usd') or 0)
        latest_btc_usd = max(latest_btc_usd, btc_usd)
        total_current_btc += equity_btc
        total_start_btc += starting_btc

        orders_count = int(row.get('orders_count') or 0)
        fills_count = int(row.get('fills_count') or 0)
        total_orders += orders_count
        total_fills += fills_count
        pnl_btc = equity_btc - starting_btc
        roi_pct = ((equity_btc / starting_btc) - 1) * 100 if starting_btc else 0.0

        bots.append(
            {
                'id': bot['id'],
                'name': bot['name'],
                'emoji': bot['emoji'],
                'color': bot['color'],
                'starting_btc': starting_btc,
                'starting_sats': round(starting_btc * SATOSHIS_PER_BTC),
                'current_equity_btc': equity_btc,
                'current_equity_sats': round(equity_btc * SATOSHIS_PER_BTC),
                'current_pnl_btc': pnl_btc,
                'current_pnl_sats': round(pnl_btc * SATOSHIS_PER_BTC),
                'current_equity_usd': round(equity_btc * btc_usd, 2) if btc_usd else 0.0,
                'current_pnl_usd': round(pnl_btc * btc_usd, 2) if btc_usd else 0.0,
                'roi_pct': round(roi_pct, 2),
                'orders_count': orders_count,
                'fills_count': fills_count,
                'active_positions': int(row.get('open_orders') or 0),
                'top_symbol': row.get('top_symbol'),
                'last_metric_at': row['ts'].isoformat() if row.get('ts') else None,
            }
        )

    recent_orders_payload = [serialize_order(row) for row in recent_orders]
    order_history_payload = []
    orders_by_bot = {bot_id: [] for bot_id in S5_BOT_IDS}
    for row in order_history:
        if row.get('symbol'):
            traded_symbols.add(row['symbol'])
        order_row = serialize_order(row)
        order_history_payload.append(order_row)
        if row.get('bot_id') in orders_by_bot:
            orders_by_bot[row['bot_id']].append(order_row)

    equity_history = []
    for row in equity_history_rows:
        equity_btc = float(row.get('equity_btc') or 0)
        btc_usd = float(row.get('btc_usd') or 0)
        equity_history.append(
            {
                'ts': row['bucket_ts'].isoformat() if row.get('bucket_ts') else None,
                'bot_id': row.get('bot_id'),
                'equity_btc': equity_btc,
                'equity_sats': round(equity_btc * SATOSHIS_PER_BTC),
                'equity_usd': round(equity_btc * btc_usd, 2) if btc_usd else 0.0,
            }
        )

    market_history = [
        {
            'ts': row['bucket_ts'].isoformat() if row.get('bucket_ts') else None,
            'symbol': row.get('symbol'),
            'price': float(row.get('mark_price') or 0),
        }
        for row in market_history_rows
    ]

    portfolio_pnl_btc = total_current_btc - total_start_btc
    portfolio_roi_pct = ((total_current_btc / total_start_btc) - 1) * 100 if total_start_btc else 0.0

    return {
        'summary': {
            'season_id': season_id,
            'total_orders': total_orders,
            'total_fills': total_fills,
            'active_bots': len(S5_BOTS),
            'verified_pairs': len(traded_symbols),
        },
        'portfolio': {
            'start_btc': total_start_btc,
            'start_sats': round(total_start_btc * SATOSHIS_PER_BTC),
            'current_btc': total_current_btc,
            'current_sats': round(total_current_btc * SATOSHIS_PER_BTC),
            'pnl_btc': portfolio_pnl_btc,
            'pnl_sats': round(portfolio_pnl_btc * SATOSHIS_PER_BTC),
            'roi_pct': round(portfolio_roi_pct, 4),
            'btc_usd': round(latest_btc_usd, 2),
            'current_usd': round(total_current_btc * latest_btc_usd, 2) if latest_btc_usd else 0.0,
        },
        'bots': bots,
        'recent_orders': recent_orders_payload,
        'order_history': order_history_payload,
        'orders_by_bot': orders_by_bot,
        'equity_history': equity_history,
        'market_history': market_history,
        'meta': {
            'last_updated': max((bot['last_metric_at'] for bot in bots if bot['last_metric_at']), default=None),
            'data_source': 'scoring_api_export_s5',
        },
    }


if __name__ == '__main__':
    uvicorn.run(app, host='0.0.0.0', port=8090)
