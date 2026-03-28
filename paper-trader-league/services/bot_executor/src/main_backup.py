#!/usr/bin/env python3
"""Season 4 backup executor using mirrored live marks only."""

import asyncio
import os
from datetime import datetime, timedelta, timezone
from decimal import Decimal

import psycopg2
import requests
from psycopg2.extras import RealDictCursor

SEASON_ID = os.getenv("SEASON_ID", "season-004")
TRADE_ENGINE_URL = os.getenv("TRADE_ENGINE_URL", "http://localhost:8088")
DB_HOST = os.getenv("POSTGRES_HOST", "timescaledb")
DB_PORT = os.getenv("POSTGRES_PORT", "5432")
DB_USER = os.getenv("POSTGRES_USER", "paperbot")
DB_PASS = os.getenv("POSTGRES_PASSWORD", "paperbot")
DB_NAME = os.getenv("POSTGRES_DB", "paperbot")

MARKS_SOURCE_SEASON_ID = os.getenv("MARKS_SOURCE_SEASON_ID", "").strip()
REFRESH_INTERVAL_SECONDS = int(os.getenv("BACKUP_REFRESH_INTERVAL_SECONDS", "60"))
MARKS_FRESHNESS_SECONDS = int(os.getenv("BACKUP_MARKS_FRESHNESS_SECONDS", "240"))
BOT_COOLDOWN_SECONDS = int(os.getenv("BACKUP_BOT_COOLDOWN_SECONDS", "1200"))
SYMBOL_COOLDOWN_SECONDS = int(os.getenv("BACKUP_SYMBOL_COOLDOWN_SECONDS", "10800"))
FUNDING_COOLDOWN_SECONDS = int(os.getenv("BACKUP_FUNDING_COOLDOWN_SECONDS", "1800"))
DRY_RUN = os.getenv("DRY_RUN", "false").lower() in {"1", "true", "yes", "on"}

MIN_ORDER_NOTIONAL_USDT = Decimal("40")
MIN_POSITION_NOTIONAL_USDT = Decimal("25")
DUST_EXIT_NOTIONAL_USDT = Decimal("10")
FORCE_EXIT_NOTIONAL_USDT = Decimal("5")
FUNDING_TARGET_PCT = Decimal("0.90")
FUNDING_MAX_SELL_PCT = Decimal("0.90")
MIN_FUNDING_BTC = Decimal("0.00001")

ACTIVE_BOT_IDS = ["loser_reversal_hunter", "gainer_momentum_catcher"]
EXCLUDED_BASE_ASSETS = {
    "USDT", "USDC", "USD", "USD1", "USDS", "USDP", "USDX", "USDT0", "USDM",
    "USDB", "USDD", "USDE", "GUSD", "DAI", "FDUSD", "PAX", "PYUSD", "WBTC",
    "CBETH", "LSETH", "STETH", "WETH", "AUSD", "SUSD",
}

BACKUP_STRATEGIES = {
    "gainer_momentum_catcher": {
        "bank_pct": Decimal("0.75"),
        "max_positions": 1,
        "entry_15m": Decimal("0.015"),
        "entry_1h": Decimal("0.04"),
        "entry_4h": Decimal("0.12"),
        "take_profit": Decimal("0.18"),
        "hard_stop": Decimal("-0.15"),
        "time_stop_hours": Decimal("3"),
        "exit_15m": Decimal("-0.02"),
        "exit_1h": Decimal("0.00"),
    },
    "loser_reversal_hunter": {
        "bank_pct": Decimal("0.75"),
        "max_positions": 1,
        "entry_15m": Decimal("0.008"),
        "entry_1h_floor": Decimal("-0.02"),
        "entry_4h": Decimal("-0.01"),
        "entry_24h": Decimal("-0.03"),
        "take_profit": Decimal("0.16"),
        "hard_stop": Decimal("-0.18"),
        "time_stop_hours": Decimal("4"),
        "exit_15m": Decimal("-0.01"),
        "exit_1h_repair": Decimal("0.03"),
    },
}


def get_db():
    return psycopg2.connect(
        host=DB_HOST,
        port=DB_PORT,
        user=DB_USER,
        password=DB_PASS,
        database=DB_NAME,
        cursor_factory=RealDictCursor,
    )


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def ensure_aware_utc(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _base_asset(symbol: str) -> str:
    for suffix in ("USDT", "USD"):
        if symbol.endswith(suffix):
            return symbol[: -len(suffix)]
    return symbol


def _to_decimal(value) -> Decimal | None:
    if value is None:
        return None
    return Decimal(str(value))


def pick_marks_source_season() -> str | None:
    if MARKS_SOURCE_SEASON_ID:
        return MARKS_SOURCE_SEASON_ID
    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                WITH freshness AS (
                    SELECT season_id, MAX(ts) AS latest_ts, COUNT(DISTINCT symbol) AS symbol_count
                    FROM market_marks
                    WHERE season_id <> %s
                    GROUP BY season_id
                ),
                btc_marked AS (
                    SELECT DISTINCT season_id
                    FROM market_marks
                    WHERE symbol = 'BTCUSDT'
                )
                SELECT f.season_id
                FROM freshness f
                JOIN btc_marked b ON b.season_id = f.season_id
                WHERE f.latest_ts >= now() - (%s || ' seconds')::interval
                ORDER BY f.latest_ts DESC, f.symbol_count DESC
                LIMIT 1
                """,
                (SEASON_ID, MARKS_FRESHNESS_SECONDS),
            )
            row = cur.fetchone()
            return row["season_id"] if row else None


def get_latest_marks(season_id: str) -> dict[str, Decimal]:
    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT DISTINCT ON (symbol) symbol, mark_price
                FROM market_marks
                WHERE season_id = %s
                ORDER BY symbol, ts DESC
                """,
                (season_id,),
            )
            return {row["symbol"]: Decimal(str(row["mark_price"])) for row in cur.fetchall()}


def mirror_live_marks(source_season_id: str) -> dict[str, Decimal]:
    marks = get_latest_marks(source_season_id)
    if not marks:
        return {}
    payload = {
        "season_id": SEASON_ID,
        "marks": {symbol: float(price) for symbol, price in marks.items()},
    }
    response = requests.post(f"{TRADE_ENGINE_URL}/marks", json=payload, timeout=15)
    response.raise_for_status()
    return marks


def get_bot_balances() -> dict[str, dict[str, Decimal]]:
    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT DISTINCT ON (bot_id, asset) bot_id, asset, free
                FROM bot_balances
                WHERE season_id = %s AND bot_id = ANY(%s)
                ORDER BY bot_id, asset, ts DESC
                """,
                (SEASON_ID, ACTIVE_BOT_IDS),
            )
            balances: dict[str, dict[str, Decimal]] = {bot_id: {} for bot_id in ACTIVE_BOT_IDS}
            for row in cur.fetchall():
                balances.setdefault(row["bot_id"], {})[row["asset"]] = Decimal(str(row["free"]))
            return balances


def get_last_fill_state(bot_id: str) -> dict[str, dict]:
    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT DISTINCT ON (symbol) symbol, side, executed_price, ts
                FROM bot_orders
                WHERE season_id = %s AND bot_id = %s AND status = 'filled'
                ORDER BY symbol, ts DESC
                """,
                (SEASON_ID, bot_id),
            )
            state = {}
            for row in cur.fetchall():
                state[row["symbol"]] = {
                    "side": row["side"],
                    "price": Decimal(str(row["executed_price"] or 0)),
                    "ts": ensure_aware_utc(row["ts"]),
                }
            return state


def get_last_trade_ts(bot_id: str) -> datetime | None:
    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT MAX(ts) AS ts
                FROM bot_orders
                WHERE season_id = %s AND bot_id = %s AND status = 'filled'
                """,
                (SEASON_ID, bot_id),
            )
            row = cur.fetchone()
            return ensure_aware_utc(row["ts"]) if row else None


def get_signal_snapshots(source_season_id: str) -> list[dict]:
    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                WITH latest AS (
                    SELECT DISTINCT ON (symbol) symbol, mark_price, ts
                    FROM market_marks
                    WHERE season_id = %s
                    ORDER BY symbol, ts DESC
                ),
                p15 AS (
                    SELECT DISTINCT ON (symbol) symbol, mark_price
                    FROM market_marks
                    WHERE season_id = %s AND ts <= now() - interval '15 minutes'
                    ORDER BY symbol, ts DESC
                ),
                p60 AS (
                    SELECT DISTINCT ON (symbol) symbol, mark_price
                    FROM market_marks
                    WHERE season_id = %s AND ts <= now() - interval '1 hour'
                    ORDER BY symbol, ts DESC
                ),
                p240 AS (
                    SELECT DISTINCT ON (symbol) symbol, mark_price
                    FROM market_marks
                    WHERE season_id = %s AND ts <= now() - interval '4 hours'
                    ORDER BY symbol, ts DESC
                ),
                p1440 AS (
                    SELECT DISTINCT ON (symbol) symbol, mark_price
                    FROM market_marks
                    WHERE season_id = %s AND ts <= now() - interval '24 hours'
                    ORDER BY symbol, ts DESC
                )
                SELECT
                    l.symbol,
                    l.mark_price,
                    l.ts,
                    ((l.mark_price - p15.mark_price) / NULLIF(p15.mark_price, 0)) AS ret_15m,
                    ((l.mark_price - p60.mark_price) / NULLIF(p60.mark_price, 0)) AS ret_1h,
                    ((l.mark_price - p240.mark_price) / NULLIF(p240.mark_price, 0)) AS ret_4h,
                    ((l.mark_price - p1440.mark_price) / NULLIF(p1440.mark_price, 0)) AS ret_24h
                FROM latest l
                LEFT JOIN p15 ON p15.symbol = l.symbol
                LEFT JOIN p60 ON p60.symbol = l.symbol
                LEFT JOIN p240 ON p240.symbol = l.symbol
                LEFT JOIN p1440 ON p1440.symbol = l.symbol
                WHERE l.ts >= now() - (%s || ' seconds')::interval
                ORDER BY l.symbol
                """,
                (
                    source_season_id,
                    source_season_id,
                    source_season_id,
                    source_season_id,
                    source_season_id,
                    MARKS_FRESHNESS_SECONDS,
                ),
            )
            snapshots = []
            for row in cur.fetchall():
                symbol = row["symbol"]
                if _base_asset(symbol) in EXCLUDED_BASE_ASSETS:
                    continue
                snapshots.append(
                    {
                        "symbol": symbol,
                        "mark_price": Decimal(str(row["mark_price"])),
                        "ts": ensure_aware_utc(row["ts"]),
                        "ret_15m": _to_decimal(row["ret_15m"]),
                        "ret_1h": _to_decimal(row["ret_1h"]),
                        "ret_4h": _to_decimal(row["ret_4h"]),
                        "ret_24h": _to_decimal(row["ret_24h"]),
                    }
                )
            return snapshots


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
        fill = last_fill.get(symbol)
        entry_price = fill["price"] if fill and fill["side"] == "BUY" and fill["price"] > 0 else price
        positions.append(
            {
                "symbol": symbol,
                "qty": qty,
                "price": price,
                "notional": qty * price,
                "entry_price": entry_price,
                "entry_ts": fill["ts"] if fill and fill["side"] == "BUY" else None,
            }
        )
    return positions


def get_position_map(positions: list[dict]) -> dict[str, dict]:
    return {position["symbol"]: position for position in positions}


class BackupBotExecutor:
    def __init__(self, bot_id: str):
        self.bot_id = bot_id
        self.config = BACKUP_STRATEGIES[bot_id]
        self.last_funding_ts: datetime | None = None

    async def execute(self, marks: dict[str, Decimal], snapshots: list[dict]) -> None:
        balances = get_bot_balances()
        positions = build_positions(self.bot_id, balances, marks)
        if await self.ensure_usdt_liquidity(balances.get(self.bot_id, {}), marks):
            return
        await self.manage_positions(positions, marks, snapshots)
        balances = get_bot_balances()
        positions = build_positions(self.bot_id, balances, marks)
        await self.open_new_position(balances.get(self.bot_id, {}), positions, marks, snapshots)

    async def ensure_usdt_liquidity(self, balances: dict[str, Decimal], marks: dict[str, Decimal]) -> bool:
        btc_balance = balances.get("BTC", Decimal("0"))
        usdt_balance = balances.get("USDT", Decimal("0"))
        btc_usdt = marks.get("BTCUSDT")
        if btc_balance <= 0 or not btc_usdt or btc_usdt <= 0:
            return False
        if self.last_funding_ts and utc_now() - self.last_funding_ts < timedelta(seconds=FUNDING_COOLDOWN_SECONDS):
            return False
        target_usdt = (btc_balance * btc_usdt + usdt_balance) * FUNDING_TARGET_PCT
        if usdt_balance >= target_usdt:
            return False
        needed_usdt = target_usdt - usdt_balance
        btc_to_sell = min(needed_usdt / btc_usdt, btc_balance * FUNDING_MAX_SELL_PCT)
        if btc_to_sell <= MIN_FUNDING_BTC or btc_to_sell * btc_usdt < MIN_ORDER_NOTIONAL_USDT:
            return False
        ok = await self.submit_order(
            "BTCUSDT",
            "SELL",
            btc_to_sell,
            {"strategy": "backup_funding", "target_usdt_pct": float(FUNDING_TARGET_PCT)},
        )
        if ok:
            self.last_funding_ts = utc_now()
        return ok

    async def manage_positions(self, positions: list[dict], marks: dict[str, Decimal], snapshots: list[dict]) -> None:
        snapshot_map = {row["symbol"]: row for row in snapshots}
        for position in positions:
            symbol = position["symbol"]
            notional = position["notional"]
            if notional < FORCE_EXIT_NOTIONAL_USDT:
                continue
            current_price = marks.get(symbol, position["price"])
            entry_price = position["entry_price"]
            pnl = (current_price - entry_price) / entry_price if entry_price > 0 else Decimal("0")
            age_hours = Decimal("0")
            if position["entry_ts"]:
                age_hours = Decimal(str((utc_now() - position["entry_ts"]).total_seconds() / 3600))
            snap = snapshot_map.get(symbol)
            exit_reason = None
            if notional < DUST_EXIT_NOTIONAL_USDT:
                exit_reason = "dust_cleanup"
            elif pnl >= self.config["take_profit"]:
                exit_reason = "take_profit"
            elif pnl <= self.config["hard_stop"]:
                exit_reason = "hard_stop"
            elif age_hours >= self.config["time_stop_hours"]:
                exit_reason = "time_stop"
            elif self.bot_id == "gainer_momentum_catcher" and snap:
                if snap["ret_15m"] is not None and snap["ret_15m"] <= self.config["exit_15m"]:
                    exit_reason = "momentum_reversal"
                elif snap["ret_1h"] is not None and snap["ret_1h"] <= self.config["exit_1h"]:
                    exit_reason = "hourly_momentum_lost"
            elif self.bot_id == "loser_reversal_hunter" and snap:
                if snap["ret_15m"] is not None and snap["ret_15m"] <= self.config["exit_15m"]:
                    exit_reason = "bounce_failed"
                elif snap["ret_1h"] is not None and snap["ret_1h"] >= self.config["exit_1h_repair"]:
                    exit_reason = "rebound_mature"
            if exit_reason:
                await self.submit_order(
                    symbol,
                    "SELL",
                    position["qty"],
                    {
                        "strategy": "backup_marks_only",
                        "bot_mode": self.bot_id,
                        "exit_reason": exit_reason,
                        "pnl_pct": float(round(pnl, 6)),
                    },
                )

    async def open_new_position(
        self,
        balances: dict[str, Decimal],
        positions: list[dict],
        marks: dict[str, Decimal],
        snapshots: list[dict],
    ) -> None:
        open_positions = [position for position in positions if position["notional"] >= MIN_POSITION_NOTIONAL_USDT]
        if len(open_positions) >= self.config["max_positions"]:
            return
        last_trade_ts = get_last_trade_ts(self.bot_id)
        if last_trade_ts and utc_now() - last_trade_ts < timedelta(seconds=BOT_COOLDOWN_SECONDS):
            return
        available_usdt = balances.get("USDT", Decimal("0"))
        btc_balance = balances.get("BTC", Decimal("0"))
        btc_usdt = marks.get("BTCUSDT", Decimal("0"))
        portfolio_usdt = available_usdt + btc_balance * btc_usdt
        budget = min(available_usdt, portfolio_usdt * self.config["bank_pct"])
        if budget < MIN_ORDER_NOTIONAL_USDT:
            return
        position_map = get_position_map(positions)
        candidates = self.rank_candidates(snapshots, position_map)
        if not candidates:
            return
        score, snapshot = candidates[0]
        price = snapshot["mark_price"]
        qty = budget / price
        if qty < min_order_qty(price):
            return
        await self.submit_order(
            snapshot["symbol"],
            "BUY",
            qty,
            {
                "strategy": "backup_marks_only",
                "bot_mode": self.bot_id,
                "score": float(score),
                "ret_15m": float(snapshot["ret_15m"]),
                "ret_1h": float(snapshot["ret_1h"]),
                "ret_4h": float(snapshot["ret_4h"]),
                "ret_24h": float(snapshot["ret_24h"]) if snapshot["ret_24h"] is not None else None,
                "bank_pct": float(self.config["bank_pct"]),
            },
        )

    def rank_candidates(self, snapshots: list[dict], position_map: dict[str, dict]) -> list[tuple[Decimal, dict]]:
        last_fill = get_last_fill_state(self.bot_id)
        ranked: list[tuple[Decimal, dict]] = []
        for snapshot in snapshots:
            symbol = snapshot["symbol"]
            if symbol in position_map:
                continue
            if self._symbol_on_cooldown(symbol, last_fill):
                continue
            if snapshot["ret_15m"] is None or snapshot["ret_1h"] is None or snapshot["ret_4h"] is None:
                continue
            if self.bot_id == "gainer_momentum_catcher":
                if snapshot["ret_15m"] < self.config["entry_15m"]:
                    continue
                if snapshot["ret_1h"] < self.config["entry_1h"]:
                    continue
                if snapshot["ret_4h"] < self.config["entry_4h"]:
                    continue
                score = snapshot["ret_4h"] * Decimal("0.50") + snapshot["ret_1h"] * Decimal("0.35") + snapshot["ret_15m"] * Decimal("0.15")
            else:
                if snapshot["ret_15m"] < self.config["entry_15m"]:
                    continue
                if snapshot["ret_1h"] < self.config["entry_1h_floor"]:
                    continue
                if snapshot["ret_4h"] > self.config["entry_4h"]:
                    continue
                if snapshot["ret_24h"] is None or snapshot["ret_24h"] > self.config["entry_24h"]:
                    continue
                score = abs(snapshot["ret_24h"]) * Decimal("0.55") + abs(snapshot["ret_4h"]) * Decimal("0.30") + snapshot["ret_15m"] * Decimal("0.15")
            ranked.append((score, snapshot))
        ranked.sort(key=lambda item: item[0], reverse=True)
        return ranked

    def _symbol_on_cooldown(self, symbol: str, last_fill: dict[str, dict]) -> bool:
        fill = last_fill.get(symbol)
        return bool(fill and fill["ts"] and utc_now() - fill["ts"] < timedelta(seconds=SYMBOL_COOLDOWN_SECONDS))

    async def submit_order(self, symbol: str, side: str, quantity: Decimal, rationale: dict) -> bool:
        price = get_latest_marks(SEASON_ID).get(symbol, Decimal("0"))
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
                "timestamp": utc_now().isoformat(),
                "runtime": "season4_backup_executor_v1",
            },
        }
        if DRY_RUN:
            print(f"[DRY_RUN][{self.bot_id}] {side} {symbol} qty={float(quantity):.8f} rationale={rationale}")
            return True
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


async def run_competition() -> None:
    print("=" * 70)
    print(f"SEASON 4 BACKUP EXECUTOR STARTED season={SEASON_ID}")
    print("=" * 70)
    executors = [BackupBotExecutor(bot_id) for bot_id in ACTIVE_BOT_IDS]
    while True:
        try:
            source_season_id = pick_marks_source_season()
            if not source_season_id:
                print("no live marks source season available")
                await asyncio.sleep(REFRESH_INTERVAL_SECONDS)
                continue
            marks = mirror_live_marks(source_season_id)
            snapshots = get_signal_snapshots(source_season_id)
            if not marks or not snapshots:
                print(f"no usable marks from source season={source_season_id}")
                await asyncio.sleep(REFRESH_INTERVAL_SECONDS)
                continue
            await asyncio.gather(*(executor.execute(marks, snapshots) for executor in executors))
        except Exception as exc:
            print(f"backup executor loop error: {exc}")
        await asyncio.sleep(REFRESH_INTERVAL_SECONDS)


def main() -> None:
    print(f"Starting backup bot executor for {SEASON_ID}...")
    asyncio.run(run_competition())


if __name__ == "__main__":
    main()
