from decimal import Decimal
from typing import Iterable

from .config import DEFAULT_BOTS, DEFAULT_SEASON_ID, DEFAULT_STARTING_BTC
from .db import get_conn


def reset_season(season_id: str = DEFAULT_SEASON_ID, starting_btc: Decimal = DEFAULT_STARTING_BTC,
                 bots: Iterable[tuple[str, str]] = DEFAULT_BOTS) -> dict:
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM bot_fills WHERE season_id = %s", (season_id,))
            cur.execute("DELETE FROM bot_orders WHERE season_id = %s", (season_id,))
            cur.execute("DELETE FROM bot_metrics WHERE season_id = %s", (season_id,))
            cur.execute("DELETE FROM bot_balances WHERE season_id = %s", (season_id,))
            cur.execute("DELETE FROM market_marks WHERE season_id = %s", (season_id,))
            cur.execute("DELETE FROM season_bots WHERE season_id = %s", (season_id,))
            cur.execute("DELETE FROM seasons WHERE season_id = %s", (season_id,))
            cur.execute(
                """
                INSERT INTO seasons (season_id, status, base_asset, starting_equity_btc, started_at)
                VALUES (%s, 'active', 'BTC', %s, now())
                """,
                (season_id, starting_btc),
            )
            for bot_id, bot_name in bots:
                cur.execute(
                    """
                    INSERT INTO season_bots (season_id, bot_id, bot_name, status)
                    VALUES (%s, %s, %s, 'ready')
                    """,
                    (season_id, bot_id, bot_name),
                )
                cur.execute(
                    """
                    INSERT INTO bot_balances (season_id, bot_id, asset, free, locked, btc_mark_value)
                    VALUES (%s, %s, 'BTC', %s, 0, %s)
                    """,
                    (season_id, bot_id, starting_btc, starting_btc),
                )
                cur.execute(
                    """
                    INSERT INTO bot_metrics (
                      season_id, bot_id, equity_btc, realized_pnl_btc, unrealized_pnl_btc,
                      drawdown_pct, trade_count, fee_btc, cash_btc, positions
                    ) VALUES (%s, %s, %s, 0, 0, 0, 0, 0, %s, '{}'::jsonb)
                    """,
                    (season_id, bot_id, starting_btc, starting_btc),
                )
    return {
        'season_id': season_id,
        'starting_btc': str(starting_btc),
        'bots': [{'bot_id': bot_id, 'bot_name': bot_name} for bot_id, bot_name in bots],
    }
