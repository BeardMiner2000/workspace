from collections import defaultdict
from decimal import Decimal, ROUND_HALF_UP
from typing import Any

from psycopg2.extras import Json

from .config import DEFAULT_FEE_BPS, DEFAULT_MAKER_FEE_BPS, DEFAULT_TAKER_FEE_BPS, DEFAULT_SEASON_ID, DEFAULT_SLIPPAGE_BPS
from .db import get_conn

FOUR = Decimal('0.00000001')
ZERO = Decimal('0')


def d(value: Any) -> Decimal:
    return Decimal(str(value))


def q(value: Decimal) -> Decimal:
    return value.quantize(FOUR, rounding=ROUND_HALF_UP)


def split_symbol(symbol: str) -> tuple[str, str]:
    symbol = symbol.upper()
    for quote in ('USDT', 'BTC', 'USD'):
        if symbol.endswith(quote):
            return symbol[:-len(quote)], quote
    raise ValueError(f'Unsupported symbol: {symbol}')


def get_latest_balances(cur, season_id: str, bot_id: str) -> dict[str, Decimal]:
    cur.execute(
        """
        SELECT DISTINCT ON (asset) asset, free
        FROM bot_balances
        WHERE season_id = %s AND bot_id = %s
        ORDER BY asset, ts DESC
        """,
        (season_id, bot_id),
    )
    return {row['asset']: d(row['free']) for row in cur.fetchall()}


def get_latest_locked(cur, season_id: str, bot_id: str) -> dict[str, Decimal]:
    cur.execute(
        """
        SELECT DISTINCT ON (asset) asset, locked
        FROM bot_balances
        WHERE season_id = %s AND bot_id = %s
        ORDER BY asset, ts DESC
        """,
        (season_id, bot_id),
    )
    return {row['asset']: d(row['locked']) for row in cur.fetchall()}


def get_latest_marks(cur, season_id: str) -> dict[str, Decimal]:
    cur.execute(
        """
        SELECT DISTINCT ON (symbol) symbol, mark_price
        FROM market_marks
        WHERE season_id = %s
        ORDER BY symbol, ts DESC
        """,
        (season_id,),
    )
    return {row['symbol']: d(row['mark_price']) for row in cur.fetchall()}


def btc_value(asset: str, qty: Decimal, marks: dict[str, Decimal]) -> Decimal:
    if qty == ZERO:
        return ZERO
    if asset == 'BTC':
        return qty
    btc_usdt = marks.get('BTCUSDT')
    if asset == 'USDT':
        if not btc_usdt or btc_usdt == ZERO:
            return ZERO
        return qty / btc_usdt
    pair = f'{asset}USDT'
    if pair in marks and btc_usdt and btc_usdt != ZERO:
        return (qty * marks[pair]) / btc_usdt
    pair_btc = f'{asset}BTC'
    if pair_btc in marks:
        return qty * marks[pair_btc]
    return ZERO


def write_balance_snapshots(cur, season_id: str, bot_id: str, balances: dict[str, Decimal],
                            marks: dict[str, Decimal], locked: dict[str, Decimal] | None = None) -> None:
    locked = locked or {}
    all_assets = set(balances.keys()) | set(locked.keys())
    for asset in all_assets:
        free = balances.get(asset, ZERO)
        locked_amt = locked.get(asset, ZERO)
        # For short positions (negative free), btc_mark_value should be negative too
        cur.execute(
            """
            INSERT INTO bot_balances (season_id, bot_id, asset, free, locked, btc_mark_value)
            VALUES (%s, %s, %s, %s, %s, %s)
            """,
            (season_id, bot_id, asset, q(free), q(locked_amt), q(btc_value(asset, free, marks))),
        )


def recompute_metrics(cur, season_id: str, bot_id: str) -> dict[str, Any]:
    balances = get_latest_balances(cur, season_id, bot_id)
    locked = get_latest_locked(cur, season_id, bot_id)
    marks = get_latest_marks(cur, season_id)
    cur.execute(
        "SELECT starting_equity_btc FROM seasons WHERE season_id = %s",
        (season_id,),
    )
    season = cur.fetchone()
    if not season:
        raise ValueError(f'Season not found: {season_id}')
    starting_equity = d(season['starting_equity_btc'])

    cur.execute(
        "SELECT COALESCE(SUM(fee_btc), 0) AS fee_btc, COUNT(*) AS trade_count FROM bot_fills WHERE season_id = %s AND bot_id = %s",
        (season_id, bot_id),
    )
    fill_stats = cur.fetchone()
    fee_btc = d(fill_stats['fee_btc'])
    trade_count = int(fill_stats['trade_count'])

    # Equity = free balances (can be negative for shorts) + locked collateral (USDT margin reserves)
    equity_btc = sum((btc_value(asset, qty, marks) for asset, qty in balances.items()), ZERO)
    # Add locked USDT margin back into equity (it's still owned, just reserved)
    for asset, amt in locked.items():
        if amt > ZERO:
            equity_btc += btc_value(asset, amt, marks)
    realized_pnl_btc = equity_btc - starting_equity
    positions = {asset: float(q(qty)) for asset, qty in balances.items() if qty != ZERO}
    # Also include locked collateral in positions display
    for asset, amt in locked.items():
        if amt > ZERO:
            key = f'{asset}_locked'
            positions[key] = float(q(amt))
    cash_btc = btc_value('BTC', balances.get('BTC', ZERO), marks) + btc_value('USDT', balances.get('USDT', ZERO), marks)

    cur.execute(
        "SELECT COALESCE(MAX(equity_btc), %s) AS peak_equity FROM bot_metrics WHERE season_id = %s AND bot_id = %s",
        (starting_equity, season_id, bot_id),
    )
    peak_equity = d(cur.fetchone()['peak_equity'])
    if peak_equity <= ZERO:
        drawdown_pct = ZERO
    else:
        drawdown_pct = max(ZERO, (peak_equity - equity_btc) / peak_equity * Decimal('100'))

    cur.execute(
        """
        INSERT INTO bot_metrics (
          season_id, bot_id, equity_btc, realized_pnl_btc, unrealized_pnl_btc,
          drawdown_pct, trade_count, fee_btc, cash_btc, positions
        ) VALUES (%s, %s, %s, %s, 0, %s, %s, %s, %s, %s)
        """,
        (
            season_id,
            bot_id,
            q(equity_btc),
            q(realized_pnl_btc),
            q(drawdown_pct),
            trade_count,
            q(fee_btc),
            q(cash_btc),
            Json(positions),
        ),
    )
    return {
        'bot_id': bot_id,
        'equity_btc': float(q(equity_btc)),
        'realized_pnl_btc': float(q(realized_pnl_btc)),
        'drawdown_pct': float(q(drawdown_pct)),
        'trade_count': trade_count,
        'fee_btc': float(q(fee_btc)),
        'positions': positions,
    }


def submit_order(*, season_id: str = DEFAULT_SEASON_ID, bot_id: str, symbol: str, side: str,
                 order_type: str, quantity: Decimal, price: Decimal | None = None,
                 rationale: dict | None = None, metadata: dict | None = None,
                 fee_bps: Decimal | None = None, slippage_bps: Decimal = DEFAULT_SLIPPAGE_BPS) -> dict[str, Any]:
    # Market orders are always taker; limit orders are maker
    if fee_bps is None:
        fee_bps = DEFAULT_MAKER_FEE_BPS if order_type.upper() == 'LIMIT' else DEFAULT_TAKER_FEE_BPS
    symbol = symbol.upper()
    side = side.upper()
    order_type = order_type.upper()
    rationale = rationale or {}
    metadata = metadata or {}

    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute('SELECT 1 FROM seasons WHERE season_id = %s', (season_id,))
            if not cur.fetchone():
                raise ValueError(f'Season not found: {season_id}')

            balances = defaultdict(lambda: ZERO, get_latest_balances(cur, season_id, bot_id))
            marks = get_latest_marks(cur, season_id)
            reference_price = price or marks.get(symbol)
            if reference_price is None:
                raise ValueError(f'No price available for {symbol}; submit explicit price or mark the market first')

            slip = slippage_bps / Decimal('10000')
            fill_price = reference_price * (Decimal('1') + slip if side == 'BUY' else Decimal('1') - slip)
            base_asset, quote_asset = split_symbol(symbol)
            gross_quote = fill_price * quantity
            fee_qty = quantity * fee_bps / Decimal('10000') if side == 'BUY' else gross_quote * fee_bps / Decimal('10000')
            fee_asset = base_asset if side == 'BUY' else quote_asset
            fee_btc = btc_value(fee_asset, fee_qty, {**marks, symbol: fill_price})

            locked = defaultdict(lambda: ZERO, get_latest_locked(cur, season_id, bot_id))

            if side == 'BUY':
                available_quote = balances[quote_asset]
                if available_quote < gross_quote:
                    raise ValueError(f'Insufficient {quote_asset} balance for {bot_id}: need {gross_quote}, have {available_quote}')
                balances[quote_asset] = available_quote - gross_quote
                balances[base_asset] = balances[base_asset] + quantity - fee_qty
            elif side == 'SELL':
                available_base = balances[base_asset]
                if available_base < quantity:
                    raise ValueError(f'Insufficient {base_asset} balance for {bot_id}: need {quantity}, have {available_base}')
                balances[base_asset] = available_base - quantity
                balances[quote_asset] = balances[quote_asset] + gross_quote - fee_qty
            elif side == 'SHORT':
                # Margin required = notional * 1.1 safety factor
                margin_required = gross_quote * Decimal('1.1')
                available_quote = balances[quote_asset]
                if available_quote < margin_required:
                    raise ValueError(
                        f'Insufficient {quote_asset} margin for {bot_id} SHORT: '
                        f'need {margin_required} (notional {gross_quote} * 1.1), have {available_quote}'
                    )
                # Deduct margin from free USDT, add to locked
                balances[quote_asset] = available_quote - margin_required
                locked[quote_asset] = locked[quote_asset] + margin_required
                # Record short position as negative base asset balance
                balances[base_asset] = balances[base_asset] - quantity
                # Store fill price in metadata for COVER PnL calculation
                metadata['short_open_price'] = float(q(fill_price))
                # Fee comes from USDT (already deducted margin covers it notionally)
                fee_asset = quote_asset
                fee_qty = gross_quote * fee_bps / Decimal('10000')
                fee_btc = btc_value(fee_asset, fee_qty, {**marks, symbol: fill_price})
            elif side == 'COVER':
                # Must have a short position (negative base balance)
                current_base = balances[base_asset]
                if current_base >= ZERO:
                    raise ValueError(
                        f'No short position in {base_asset} for {bot_id}: balance is {current_base}'
                    )
                short_qty = abs(current_base)
                cover_qty = min(quantity, short_qty)

                # Look up the most recent SHORT order for this symbol to get open price
                cur.execute(
                    """
                    SELECT metadata->>'short_open_price' AS short_open_price
                    FROM bot_orders
                    WHERE season_id = %s AND bot_id = %s AND symbol = %s AND side = 'SHORT'
                    ORDER BY ts DESC
                    LIMIT 1
                    """,
                    (season_id, bot_id, symbol),
                )
                short_order = cur.fetchone()
                if short_order and short_order['short_open_price']:
                    short_open_price = d(short_order['short_open_price'])
                else:
                    # Fallback: assume break-even
                    short_open_price = fill_price

                # PnL = (open_price - cover_price) * qty
                pnl = (short_open_price - fill_price) * cover_qty
                metadata['short_open_price'] = float(q(short_open_price))
                metadata['cover_price'] = float(q(fill_price))
                metadata['pnl_usdt'] = float(q(pnl))

                # Release locked margin proportional to coverage
                proportion = cover_qty / short_qty if short_qty > ZERO else Decimal('1')
                margin_to_release = locked[quote_asset] * proportion
                locked[quote_asset] = locked[quote_asset] - margin_to_release

                # Zero out the covered short position
                balances[base_asset] = current_base + cover_qty  # brings it back toward 0

                # Return margin + PnL to free USDT
                balances[quote_asset] = balances[quote_asset] + margin_to_release + pnl

                # Fee on cover
                fee_asset = quote_asset
                cover_notional = fill_price * cover_qty
                fee_qty = cover_notional * fee_bps / Decimal('10000')
                fee_btc = btc_value(fee_asset, fee_qty, {**marks, symbol: fill_price})
                balances[quote_asset] = balances[quote_asset] - fee_qty
                quantity = cover_qty
            else:
                raise ValueError(f'Unsupported side: {side}')

            cur.execute(
                """
                INSERT INTO bot_orders (
                  season_id, bot_id, symbol, side, order_type, request_price, requested_quantity,
                  executed_price, executed_quantity, status, rationale, metadata
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, 'filled', %s, %s)
                RETURNING id, ts
                """,
                (
                    season_id, bot_id, symbol, side, order_type, price, q(quantity), q(fill_price), q(quantity),
                    Json(rationale), Json({**metadata, 'reference_price': float(q(reference_price))}),
                ),
            )
            order = cur.fetchone()
            cur.execute(
                """
                INSERT INTO bot_fills (
                  season_id, order_id, bot_id, symbol, side, fill_price, fill_quantity,
                  fee_asset, fee_amount, fee_btc, slippage_bps, metadata
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id, ts
                """,
                (
                    season_id, order['id'], bot_id, symbol, side, q(fill_price), q(quantity), fee_asset,
                    q(fee_qty), q(fee_btc), q(slippage_bps), Json(metadata),
                ),
            )
            fill = cur.fetchone()
            write_balance_snapshots(cur, season_id, bot_id, balances, {**marks, symbol: fill_price},
                                    locked=dict(locked) if side in ('SHORT', 'COVER') else None)
            metrics = recompute_metrics(cur, season_id, bot_id)
            return {
                'accepted': True,
                'season_id': season_id,
                'order_id': order['id'],
                'fill_id': fill['id'],
                'status': 'filled',
                'fill_price': float(q(fill_price)),
                'fill_quantity': float(q(quantity)),
                'fee_asset': fee_asset,
                'fee_amount': float(q(fee_qty)),
                'fee_btc': float(q(fee_btc)),
                'slippage_bps': float(q(slippage_bps)),
                'metrics': metrics,
            }


def mark_to_market(season_id: str, marks_in: dict[str, Decimal]) -> dict[str, Any]:
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute('SELECT bot_id FROM season_bots WHERE season_id = %s ORDER BY bot_id', (season_id,))
            bots = [row['bot_id'] for row in cur.fetchall()]
            for symbol, price in marks_in.items():
                cur.execute(
                    'INSERT INTO market_marks (season_id, symbol, mark_price) VALUES (%s, %s, %s)',
                    (season_id, symbol.upper(), q(d(price))),
                )
            metrics = [recompute_metrics(cur, season_id, bot_id) for bot_id in bots]
            return {
                'season_id': season_id,
                'marks': {symbol.upper(): float(q(d(price))) for symbol, price in marks_in.items()},
                'metrics': metrics,
            }
