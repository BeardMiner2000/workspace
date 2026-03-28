#!/usr/bin/env python3
"""Season 4 bot executor for the two live long-only bots."""

import asyncio
import json
import os
from datetime import datetime, timedelta
from decimal import Decimal
from pathlib import Path

import psycopg2
import requests
from psycopg2 import sql
from psycopg2.extras import RealDictCursor

SEASON_ID = os.getenv("SEASON_ID", "season-004")
TRADE_ENGINE_URL = os.getenv("TRADE_ENGINE_URL", "http://localhost:8088")
DB_HOST = os.getenv("POSTGRES_HOST", "timescaledb")
DB_PORT = os.getenv("POSTGRES_PORT", "5432")
DB_USER = os.getenv("POSTGRES_USER", "paperbot")
DB_PASS = os.getenv("POSTGRES_PASSWORD", "paperbot")
DB_NAME = os.getenv("POSTGRES_DB", "paperbot")

COMPETITION_DURATION_HOURS = 72
REFRESH_INTERVAL_SECONDS = 5
FUNDING_TARGET_PCT = Decimal("0.25")
FUNDING_MAX_SELL_PCT = Decimal("0.10")
FUNDING_COOLDOWN_SECONDS = 600
MIN_FUNDING_BTC = Decimal("0.00001")
LOOKBACK_WINDOWS_HOURS = (24, 6, 1)
MAX_MOVERS = 15
MIN_MOVERS_FOR_WINDOW = 10
LATEST_MAX_AGE_MINUTES = 15
PAST_PRICE_MAX_AGE_MULTIPLIER = 2
MIN_ORDER_NOTIONAL_USDT = Decimal("40")
MIN_POSITION_NOTIONAL_USDT = Decimal("30")
DUST_EXIT_NOTIONAL_USDT = Decimal("10")
BOT_COOLDOWN_SECONDS = 180
SYMBOL_COOLDOWN_SECONDS = 900
EXCLUDED_BASE_ASSETS = {
    "USDT", "USDC", "USD", "USD1", "USDS", "USDP", "USDX", "USDT0", "USDM",
    "USDB", "USDD", "USDE", "GUSD", "DAI", "FDUSD", "PAX", "PYUSD", "WBTC",
    "CBETH", "LSETH", "STETH", "WETH", "AUSD", "SUSD",
}
ACTIVE_BOT_IDS = ["loser_reversal_hunter", "gainer_momentum_catcher"]

STRATEGIES_FILE = Path(__file__).parent / "bot_strategies.json"
with open(STRATEGIES_FILE) as f:
    STRATEGIES_DATA = json.load(f)
ALL_BOT_STRATEGIES = STRATEGIES_DATA["bot_strategies"]
BOT_STRATEGIES = {bot_id: ALL_BOT_STRATEGIES[bot_id] for bot_id in ACTIVE_BOT_IDS}


def get_db():
    return psycopg2.connect(
        host=DB_HOST,
        port=DB_PORT,
        user=DB_USER,
        password=DB_PASS,
        database=DB_NAME,
        cursor_factory=RealDictCursor,
    )


def _base_asset(symbol: str) -> str:
    for suffix in ("USDT", "USD"):
        if symbol.endswith(suffix):
            return symbol[: -len(suffix)]
    return symbol


def _table_exists(cur, table_name: str) -> bool:
    cur.execute("SELECT to_regclass(%s) IS NOT NULL AS exists", (table_name,))
    row = cur.fetchone()
    return bool(row and row.get("exists"))


def _fetch_coinbase_big_movers(table_name: str, order: str) -> list[dict]:
    with get_db() as conn:
        with conn.cursor() as cur:
            if not _table_exists(cur, table_name):
                return []
            query = sql.SQL("""
                WITH latest_feed AS (
                    SELECT DISTINCT ON (symbol) symbol, change_24h_pct
                    FROM {table}
                    ORDER BY symbol, last_updated DESC
                ),
                latest_marks AS (
                    SELECT DISTINCT ON (symbol) symbol, mark_price
                    FROM market_marks
                    WHERE season_id = %s
                    ORDER BY symbol, ts DESC
                )
                SELECT f.symbol, f.change_24h_pct, m.mark_price
                FROM latest_feed f
                JOIN latest_marks m ON m.symbol = f.symbol
                ORDER BY f.change_24h_pct {order}
                LIMIT %s
            """).format(table=sql.Identifier(*table_name.split(".")), order=sql.SQL(order))
            cur.execute(query, (SEASON_ID, MAX_MOVERS))
            return [
                dict(row)
                for row in cur.fetchall()
                if _base_asset(row["symbol"]) not in EXCLUDED_BASE_ASSETS
            ]


def _rank_big_movers_from_marks(order: str) -> list[dict]:
    with get_db() as conn:
        with conn.cursor() as cur:
            for hours in LOOKBACK_WINDOWS_HOURS:
                lookback_interval = f"{hours} hours"
                latest_max_age = f"{LATEST_MAX_AGE_MINUTES} minutes"
                past_max_age = f"{hours * PAST_PRICE_MAX_AGE_MULTIPLIER} hours"
                query = sql.SQL("""
                    WITH latest AS (
                        SELECT DISTINCT ON (symbol) symbol, mark_price, ts
                        FROM market_marks
                        WHERE season_id = %s
                        ORDER BY symbol, ts DESC
                    ),
                    past AS (
                        SELECT DISTINCT ON (symbol) symbol, mark_price AS past_price, ts AS past_ts
                        FROM market_marks
                        WHERE season_id = %s AND ts <= now() - %s::interval
                        ORDER BY symbol, ts DESC
                    )
                    SELECT l.symbol,
                           l.mark_price,
                           ((l.mark_price - p.past_price) / NULLIF(p.past_price, 0)) * 100 AS change_pct,
                           p.past_price,
                           l.ts AS latest_ts,
                           p.past_ts
                    FROM latest l
                    JOIN past p ON l.symbol = p.symbol
                    WHERE l.ts >= now() - %s::interval
                      AND p.past_ts >= now() - %s::interval
                    ORDER BY change_pct {order}
                    LIMIT %s
                """).format(order=sql.SQL(order))
                cur.execute(
                    query,
                    (SEASON_ID, SEASON_ID, lookback_interval, latest_max_age, past_max_age, MAX_MOVERS * 4),
                )
                rows = cur.fetchall()
                if not rows:
                    continue
                filtered = []
                for row in rows:
                    if _base_asset(row["symbol"]) in EXCLUDED_BASE_ASSETS:
                        continue
                    row_dict = dict(row)
                    row_dict["change_24h_pct"] = row_dict.pop("change_pct")
                    row_dict["window_hours"] = hours
                    filtered.append(row_dict)
                filtered.sort(key=lambda item: item["change_24h_pct"], reverse=(order == "DESC"))
                if len(filtered) >= MIN_MOVERS_FOR_WINDOW or hours == LOOKBACK_WINDOWS_HOURS[-1]:
                    return filtered[:MAX_MOVERS]
    return []


def get_big_losers() -> list[dict]:
    return _fetch_coinbase_big_movers("coinbase_big_losers", "ASC") or _rank_big_movers_from_marks("ASC")


def get_big_gainers() -> list[dict]:
    return _fetch_coinbase_big_movers("coinbase_big_gainers", "DESC") or _rank_big_movers_from_marks("DESC")


def get_latest_marks() -> dict[str, Decimal]:
    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT DISTINCT ON (symbol) symbol, mark_price
                FROM market_marks
                WHERE season_id = %s
                ORDER BY symbol, ts DESC
            """, (SEASON_ID,))
            return {row["symbol"]: Decimal(str(row["mark_price"])) for row in cur.fetchall()}


def get_bot_balances() -> dict[str, dict[str, Decimal]]:
    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT DISTINCT ON (bot_id, asset) bot_id, asset, free
                FROM bot_balances
                WHERE season_id = %s AND bot_id = ANY(%s)
                ORDER BY bot_id, asset, ts DESC
            """, (SEASON_ID, ACTIVE_BOT_IDS))
            balances: dict[str, dict[str, Decimal]] = {bot_id: {} for bot_id in ACTIVE_BOT_IDS}
            for row in cur.fetchall():
                balances.setdefault(row["bot_id"], {})[row["asset"]] = Decimal(str(row["free"]))
            return balances


def get_last_fill_state(bot_id: str) -> dict[str, dict[str, Decimal | datetime]]:
    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT DISTINCT ON (symbol) symbol, side, executed_price, ts
                FROM bot_orders
                WHERE season_id = %s AND bot_id = %s AND status = 'filled'
                ORDER BY symbol, ts DESC
            """, (SEASON_ID, bot_id))
            state: dict[str, dict[str, Decimal | datetime]] = {}
            for row in cur.fetchall():
                state[row["symbol"]] = {
                    "side": row["side"],
                    "price": Decimal(str(row["executed_price"] or 0)),
                    "ts": row["ts"],
                }
            return state


def min_order_qty(price: Decimal) -> Decimal:
    if price <= 0:
        return Decimal("0.0001")
    if price >= Decimal("1000"):
        return Decimal("0.001")
    if price >= Decimal("100"):
        return Decimal("0.01")
    return Decimal("0.0001")


def build_positions(bot_id: str, balances: dict[str, dict[str, Decimal]], marks: dict[str, Decimal]) -> list[dict]:
    bot_balances = balances.get(bot_id, {})
    last_fill = get_last_fill_state(bot_id)
    positions = []
    for asset, qty in bot_balances.items():
        if asset in {"BTC", "USDT", "USDC"} or qty <= 0:
            continue
        symbol = f"{asset}USDT"
        price = marks.get(symbol, Decimal("0"))
        if price <= 0:
            continue
        notional = qty * price
        fill = last_fill.get(symbol)
        entry_price = Decimal(str(fill["price"])) if fill and fill["side"] == "BUY" else price
        entry_ts = fill["ts"] if fill and fill["side"] == "BUY" else None
        positions.append({
            "symbol": symbol,
            "qty": qty,
            "price": price,
            "notional": notional,
            "entry_price": entry_price if entry_price > 0 else price,
            "entry_ts": entry_ts,
        })
    return positions


class BotExecutor:
    def __init__(self, bot_id: str):
        self.bot_id = bot_id
        self.strategy = BOT_STRATEGIES[bot_id]
        self.last_funding_ts: datetime | None = None
        self.last_trade_ts: datetime | None = None
        self.symbol_cooldowns: dict[str, datetime] = {}

    async def execute(self):
        marks = get_latest_marks()
        balances = get_bot_balances()
        positions = build_positions(self.bot_id, balances, marks)
        if await self.ensure_usdt_liquidity(balances, marks):
            await asyncio.sleep(REFRESH_INTERVAL_SECONDS)
            return
        await self.manage_positions(positions, marks)
        balances = get_bot_balances()
        positions = build_positions(self.bot_id, balances, marks)
        await self.open_new_position(balances.get(self.bot_id, {}), positions, marks)
        await asyncio.sleep(REFRESH_INTERVAL_SECONDS)

    async def ensure_usdt_liquidity(self, balances, marks) -> bool:
        bot_balance = balances.get(self.bot_id, {})
        btc_balance = bot_balance.get("BTC", Decimal("0"))
        usdt_balance = bot_balance.get("USDT", Decimal("0"))
        if btc_balance <= 0:
            return False
        if self.last_funding_ts and datetime.utcnow() - self.last_funding_ts < timedelta(seconds=FUNDING_COOLDOWN_SECONDS):
            return False
        btc_usdt = marks.get("BTCUSDT")
        if not btc_usdt or btc_usdt <= 0:
            return False
        target_usdt = btc_balance * btc_usdt * FUNDING_TARGET_PCT
        if usdt_balance >= target_usdt:
            return False
        needed_usdt = target_usdt - usdt_balance
        btc_to_sell = min(needed_usdt / btc_usdt, btc_balance * FUNDING_MAX_SELL_PCT)
        if btc_to_sell <= MIN_FUNDING_BTC or btc_to_sell * btc_usdt < MIN_ORDER_NOTIONAL_USDT:
            return False
        ok = await self.submit_order("BTCUSDT", "SELL", btc_to_sell, {"strategy": "funding", "note": "convert BTC to USDT"})
        if ok:
            self.last_funding_ts = datetime.utcnow()
        return ok

    async def manage_positions(self, positions: list[dict], marks: dict[str, Decimal]) -> None:
        mover_feed = {item["symbol"]: item for item in (get_big_losers() if self.bot_id == "loser_reversal_hunter" else get_big_gainers())}
        config = self.strategy["position_management"]
        for position in positions:
            symbol = position["symbol"]
            notional = position["notional"]
            if notional < DUST_EXIT_NOTIONAL_USDT:
                continue
            entry_price = position["entry_price"]
            current_price = marks.get(symbol, position["price"])
            pnl = (current_price - entry_price) / entry_price if entry_price > 0 else Decimal("0")
            age_hours = 0.0
            if position["entry_ts"]:
                age_hours = (datetime.utcnow() - position["entry_ts"]).total_seconds() / 3600
            feed_row = mover_feed.get(symbol)
            change = Decimal(str(feed_row["change_24h_pct"])) if feed_row else Decimal("0")
            exit_reason = None
            if pnl >= Decimal(str(config["take_profit_low"])):
                exit_reason = "take_profit"
            elif pnl <= Decimal(str(config["hard_stop"])):
                exit_reason = "hard_stop"
            elif age_hours >= float(config["time_stop_hours"]):
                exit_reason = "time_stop"
            elif self.bot_id == "gainer_momentum_catcher" and (not feed_row or change < Decimal("8")):
                exit_reason = "momentum_faded"
            elif self.bot_id == "loser_reversal_hunter" and (not feed_row or change > Decimal("-2")):
                exit_reason = "reversion_captured"
            if exit_reason:
                await self.submit_order(symbol, "SELL", position["qty"], {
                    "strategy": self.strategy["type"],
                    "exit_reason": exit_reason,
                    "pnl_pct": float(round(pnl, 6)),
                })

    async def open_new_position(self, balances: dict[str, Decimal], positions: list[dict], marks: dict[str, Decimal]) -> None:
        open_symbols = {p["symbol"] for p in positions if p["notional"] >= MIN_POSITION_NOTIONAL_USDT}
        max_positions = int(self.strategy["position_management"]["max_concurrent"])
        if len(open_symbols) >= max_positions:
            return
        if self.last_trade_ts and datetime.utcnow() - self.last_trade_ts < timedelta(seconds=BOT_COOLDOWN_SECONDS):
            return
        available_usdt = balances.get("USDT", Decimal("0"))
        if available_usdt < MIN_ORDER_NOTIONAL_USDT:
            return
        movers = get_big_losers() if self.bot_id == "loser_reversal_hunter" else get_big_gainers()
        candidates = []
        for mover in movers:
            symbol = mover["symbol"]
            price = Decimal(str(mover["mark_price"]))
            if symbol in open_symbols or price <= 0:
                continue
            if self._symbol_on_cooldown(symbol):
                continue
            change = Decimal(str(mover["change_24h_pct"]))
            window_hours = Decimal(str(mover.get("window_hours", 24)))
            if self.bot_id == "loser_reversal_hunter":
                threshold = Decimal(str(self.strategy["entry_signals"]["daily_change_threshold"])) * window_hours / Decimal("24")
                if change > threshold:
                    continue
                score = abs(change)
            else:
                threshold = Decimal(str(self.strategy["entry_signals"]["daily_change_threshold"])) * window_hours / Decimal("24")
                if change < threshold:
                    continue
                score = change
            candidates.append((score, symbol, price, change))
        if not candidates:
            return
        candidates.sort(reverse=True)
        _, symbol, price, change = candidates[0]
        slots_left = max_positions - len(open_symbols)
        per_trade_budget = min(
            available_usdt * Decimal(str(self.strategy["position_management"]["position_size_pct"])) / Decimal("100"),
            available_usdt / Decimal(str(max(slots_left, 1))),
        )
        if per_trade_budget < MIN_ORDER_NOTIONAL_USDT:
            return
        qty = per_trade_budget / price
        if qty < min_order_qty(price):
            return
        ok = await self.submit_order(symbol, "BUY", qty, {
            "strategy": self.strategy["type"],
            "change_24h": float(change),
            "mode": "long_only",
        })
        if ok:
            now = datetime.utcnow()
            self.last_trade_ts = now
            self.symbol_cooldowns[symbol] = now

    def _symbol_on_cooldown(self, symbol: str) -> bool:
        last = self.symbol_cooldowns.get(symbol)
        return bool(last and datetime.utcnow() - last < timedelta(seconds=SYMBOL_COOLDOWN_SECONDS))

    async def submit_order(self, symbol: str, side: str, quantity: Decimal, rationale: dict) -> bool:
        quantity = Decimal(str(quantity))
        price = get_latest_marks().get(symbol, Decimal("0"))
        if quantity <= 0 or price <= 0:
            return False
        if quantity < min_order_qty(price):
            return False
        if quantity * price < MIN_ORDER_NOTIONAL_USDT:
            return False
        payload = {
            "season_id": SEASON_ID,
            "bot_id": self.bot_id,
            "symbol": symbol,
            "side": side,
            "order_type": "market",
            "quantity": float(quantity),
            "rationale": rationale,
            "metadata": {
                "timestamp": datetime.utcnow().isoformat(),
                "runtime": "season4_executor_v2",
            },
        }
        try:
            response = requests.post(f"{TRADE_ENGINE_URL}/orders", json=payload, timeout=5)
        except Exception as exc:
            print(f"[{self.bot_id}] order error {symbol} {side}: {exc}")
            return False
        if response.status_code == 200:
            print(f"[{self.bot_id}] {side} {symbol} qty={float(quantity):.8f}")
            return True
        print(f"[{self.bot_id}] order failed {symbol} {side}: {response.text}")
        return False


async def run_competition():
    print("=" * 70)
    print(f"SEASON 4 2-BOT COMPETITION STARTED season={SEASON_ID}")
    print("=" * 70)
    executors = [BotExecutor(bot_id) for bot_id in ACTIVE_BOT_IDS]
    start_time = datetime.utcnow()
    end_time = start_time + timedelta(hours=COMPETITION_DURATION_HOURS)
    while datetime.utcnow() < end_time:
        try:
            await asyncio.gather(*(executor.execute() for executor in executors))
            elapsed = int((datetime.utcnow() - start_time).total_seconds())
            if elapsed and elapsed % 60 == 0:
                print(f"[{elapsed // 60}m] season4 executors active")
        except Exception as exc:
            print(f"main loop error: {exc}")
            await asyncio.sleep(10)


def main():
    print(f"Starting Bot Executor for {SEASON_ID}...")
    asyncio.run(run_competition())


if __name__ == "__main__":
    main()
