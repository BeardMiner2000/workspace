from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
import json
import math
import os
import random
import time
from typing import Any, Iterable

import psycopg2
import requests
from psycopg2.extras import RealDictCursor

try:
    from .market_feed import (
        SYMBOL_MAP,
        fetch_coinbase_best_bid_ask,
        fetch_coinbase_candles,
        fetch_coinbase_orderbook,
        fetch_coinbase_prices_safe,
    )
    from .dexscreener import fetch_top_solana_tokens
except ImportError:  # pragma: no cover
    import importlib.util
    import pathlib

    _spec = importlib.util.spec_from_file_location(
        "market_feed",
        pathlib.Path(__file__).with_name("market_feed.py"),
    )
    _mod = importlib.util.module_from_spec(_spec)
    _spec.loader.exec_module(_mod)
    SYMBOL_MAP = _mod.SYMBOL_MAP
    fetch_coinbase_best_bid_ask = _mod.fetch_coinbase_best_bid_ask
    fetch_coinbase_candles = _mod.fetch_coinbase_candles
    fetch_coinbase_orderbook = _mod.fetch_coinbase_orderbook
    fetch_coinbase_prices_safe = _mod.fetch_coinbase_prices_safe

    _dex_spec = importlib.util.spec_from_file_location(
        "dexscreener",
        pathlib.Path(__file__).with_name("dexscreener.py"),
    )
    _dex_mod = importlib.util.module_from_spec(_dex_spec)
    _dex_spec.loader.exec_module(_dex_mod)
    fetch_top_solana_tokens = _dex_mod.fetch_top_solana_tokens

ZERO = Decimal("0")
SAT = Decimal("0.00000001")
MIN_ORDER_NOTIONAL_USDT = Decimal("15")
MIN_POSITION_NOTIONAL_USDT = Decimal("10")

CORE_SYMBOL_DEFAULTS = {
    "BTCUSDT":   {"price": 65000.0,   "drift": 0.0004, "amp": 0.006},
    "ETHUSDT":   {"price": 3400.0,    "drift": 0.0008, "amp": 0.011},
    "SOLUSDT":   {"price": 140.0,     "drift": 0.0012, "amp": 0.02},
    "DOGEUSDT":  {"price": 0.15,      "drift": 0.0015, "amp": 0.03},
    "SHIBUSDT":  {"price": 0.00002,   "drift": 0.001,  "amp": 0.04},
    "PEPEUSDT":  {"price": 0.0000015, "drift": 0.001,  "amp": 0.05},
    "WIFUSDT":   {"price": 2.5,       "drift": 0.001,  "amp": 0.04},
    "BONKUSDT":  {"price": 0.00003,   "drift": 0.001,  "amp": 0.05},
    "FLOKIUSDT": {"price": 0.00018,   "drift": 0.001,  "amp": 0.04},
}
GENERIC_SYMBOL_TEMPLATE = {"price": 1.0, "drift": 0.0008, "amp": 0.015}
DEFAULT_BEST_QUOTE_SYMBOLS = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "DOGEUSDT"]

# Season-003 extra memecoin symbols always included (merged with dynamic SYMBOL_MAP)
S3_EXTRA_SYMBOLS = [
    "SHIBUSDT", "PEPEUSDT", "WIFUSDT", "BONKUSDT", "FLOKIUSDT",
]


@dataclass
class BotState:
    bot_id: str
    marks: dict[str, Decimal]
    history: dict[str, list[Decimal]]
    balances: dict[str, Decimal]
    tick: int
    timestamp: float
    best_quotes: dict[str, dict[str, float]]


class LeagueRuntime:
    def __init__(self) -> None:
        self.season_id = os.getenv("DEFAULT_SEASON_ID", "season-003")
        self.trade_engine_url = os.getenv("TRADE_ENGINE_URL", "http://trade_engine:8088")
        self.loop_seconds = float(os.getenv("INGEST_LOOP_SECONDS", "5"))
        self.bootstrap = os.getenv("AUTO_BOOTSTRAP_SEASON", "true").lower() in {"1", "true", "yes"}
        self.starting_btc = float(os.getenv("DEFAULT_STARTING_BTC", "0.05"))
        self.source = os.getenv("MARKET_DATA_SOURCE", "coinbase").lower()
        self.seed = int(os.getenv("SYNTHETIC_SEED", "42"))
        self.max_history = int(os.getenv("SYNTHETIC_HISTORY_SIZE", "720"))
        self.rand = random.Random(self.seed)
        self.tick = 0
        self.loop_start_ts = time.time()
        core_symbols = list(CORE_SYMBOL_DEFAULTS.keys())
        if self.source == "coinbase":
            dynamic_symbols = sorted(SYMBOL_MAP.keys())
            # Merge dynamic + S3 extras, deduplicate, preserve order
            merged: list[str] = list(dynamic_symbols)
            seen_set: set[str] = set(merged)
            for sym in S3_EXTRA_SYMBOLS:
                if sym not in seen_set:
                    merged.append(sym)
                    seen_set.add(sym)
            symbols = merged or core_symbols
        else:
            symbols = core_symbols
        self.symbols = list(symbols)
        self.best_quote_symbols = self._resolve_best_quote_symbols(self.symbols)
        self.state = {symbol: self._initial_symbol_meta(symbol) for symbol in self.symbols}
        self.history = {symbol: deque(maxlen=self.max_history) for symbol in self.symbols}
        self.best_quotes: dict[str, dict[str, float]] = {}
        self.candle_cache: dict[tuple[str, str], dict[str, Any]] = {}
        self.spread_history = {symbol: deque(maxlen=240) for symbol in self.symbols}
        self.obi_history = {symbol: deque(maxlen=6) for symbol in self.symbols}
        self.bot_positions: dict[str, dict[str, dict[str, Any]]] = {}
        self.bot_cooldowns: dict[str, float] = {}
        self.symbol_cooldowns: dict[str, float] = {}
        self.short_positions: dict[str, dict[str, dict[str, Any]]] = {}
        self.latest_mark_cache: dict[str, tuple[float, Decimal]] = {}

        # Season-003 pump data
        self.pump_tokens: list[dict] = []
        self.pump_prices: dict[str, float] = {}
        self.last_pump_refresh: float = 0.0

        # Bot-specific state
        self.pump_positions: dict[str, dict] = {}   # pump_surfer positions
        self.chaos_positions: dict[str, dict] = {}  # chaos_prophet long positions
        self.chaos_shorts: dict[str, dict] = {}     # chaos_prophet synthetic shorts

        self._initial_seed_done = False

    # ── infra helpers ──────────────────────────────────────────────────────
    def log(self, message: str) -> None:
        print(f"[data_ingest_s3] {datetime.now(timezone.utc).isoformat()} {message}", flush=True)

    def get_dsn(self) -> str:
        host = os.getenv("POSTGRES_HOST", "timescaledb")
        port = os.getenv("POSTGRES_PORT", "5432")
        user = os.getenv("POSTGRES_USER", "paperbot")
        password = os.getenv("POSTGRES_PASSWORD", "paperbot")
        database = os.getenv("POSTGRES_DB", "paperbot")
        return f"dbname={database} user={user} password={password} host={host} port={port}"

    def get_conn(self):
        return psycopg2.connect(self.get_dsn(), cursor_factory=RealDictCursor)

    def quant(self, value: Decimal) -> Decimal:
        return value.quantize(SAT)

    def min_order_qty(self, price: Decimal) -> Decimal:
        if price <= ZERO:
            return Decimal("0.0001")
        if price >= Decimal("1000"):
            return Decimal("0.001")
        if price >= Decimal("100"):
            return Decimal("0.01")
        return Decimal("0.0001")

    def wait_for_dependencies(self) -> None:
        while True:
            try:
                with self.get_conn() as conn:
                    with conn.cursor() as cur:
                        cur.execute("SELECT 1")
                        cur.fetchone()
                requests.get(f"{self.trade_engine_url}/health", timeout=3).raise_for_status()
                return
            except Exception as exc:  # pragma: no cover - startup retry loop
                self.log(f"waiting for dependencies: {exc}")
                time.sleep(3)

    def season_exists(self) -> bool:
        with self.get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT EXISTS(SELECT 1 FROM seasons WHERE season_id = %s) AS season_exists",
                    (self.season_id,),
                )
                row = cur.fetchone()
                return bool(row["season_exists"])

    def _initial_symbol_meta(self, symbol: str) -> dict[str, float]:
        template = CORE_SYMBOL_DEFAULTS.get(symbol, GENERIC_SYMBOL_TEMPLATE)
        return {"price": template["price"], "drift": template["drift"], "amp": template["amp"]}

    def _resolve_best_quote_symbols(self, available: list[str]) -> list[str]:
        if not available:
            return []
        raw = os.getenv("BEST_QUOTE_SYMBOLS")
        if raw:
            requested = [symbol.strip().upper() for symbol in raw.split(",") if symbol.strip()]
        else:
            requested = DEFAULT_BEST_QUOTE_SYMBOLS
        filtered = [symbol for symbol in requested if symbol in available]
        if filtered:
            return filtered
        fallback = [symbol for symbol in DEFAULT_BEST_QUOTE_SYMBOLS if symbol in available]
        if fallback:
            return fallback
        limit = min(len(available), 10)
        return available[:limit]

    def _seed_initial_coinbase_prices(self) -> None:
        prices = fetch_coinbase_prices_safe(self.symbols, log_fn=self.log)
        if not prices:
            self.log("initial Coinbase price seed failed; continuing with defaults")
            return
        seeded = 0
        for symbol in self.symbols:
            price = prices.get(symbol)
            if price is None:
                continue
            self.state[symbol]["price"] = price
            self.history[symbol].append(Decimal(str(price)))
            seeded += 1
        if seeded:
            self.log(f"seeded initial Coinbase prices for {seeded} symbols")

    def maybe_bootstrap(self) -> None:
        if not self.bootstrap:
            return
        if self.season_exists():
            self.log(
                f"season {self.season_id} already exists; skipping bootstrap to preserve prior state"
            )
            return
        payload = {"season_id": self.season_id, "starting_btc": self.starting_btc}
        response = requests.post(f"{self.trade_engine_url}/season/bootstrap", json=payload, timeout=10)
        response.raise_for_status()
        self.log(f"bootstrapped season {self.season_id}")

    # ── market + math helpers ─────────────────────────────────────────────
    def current_marks(self) -> dict[str, Decimal]:
        marks = {symbol: Decimal(str(meta["price"])) for symbol, meta in self.state.items()}
        # Also inject pump token prices
        for sym, price in self.pump_prices.items():
            if price > 0:
                marks[sym] = Decimal(str(price))
        return marks

    def update_synthetic_market(self) -> dict[str, float]:
        self.tick += 1
        for symbol, meta in self.state.items():
            drift = meta.get("drift", 0.0004)
            amp = meta.get("amp", 0.01)
            shock = self.rand.uniform(-amp, amp)
            meta["price"] = max(meta["price"] * (1 + drift + shock), 0.0001)
            self.history[symbol].append(Decimal(str(meta["price"])))
        return {symbol: round(meta["price"], 8) for symbol, meta in self.state.items()}

    def publish_marks(self, marks: dict[str, float]) -> dict[str, Any]:
        response = requests.post(
            f"{self.trade_engine_url}/marks",
            json={"season_id": self.season_id, "marks": marks},
            timeout=10,
        )
        response.raise_for_status()
        return response.json()

    def get_balances(self, bot_id: str) -> dict[str, Decimal]:
        with self.get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT DISTINCT ON (asset) asset, free
                    FROM bot_balances
                    WHERE season_id = %s AND bot_id = %s
                    ORDER BY asset, ts DESC
                    """,
                    (self.season_id, bot_id),
                )
                return {row["asset"]: Decimal(str(row["free"])) for row in cur.fetchall()}

    def pct_change(self, series: list[Decimal], lookback: int) -> float:
        if len(series) <= lookback:
            return 0.0
        old = series[-lookback - 1]
        new = series[-1]
        if old == ZERO:
            return 0.0
        return float((new - old) / old)

    def stdev_returns(self, series: list[Decimal], window: int) -> float:
        if len(series) <= window:
            return 0.0
        values = [float(x) for x in series[-window:]]
        rets = []
        for left, right in zip(values, values[1:]):
            if left:
                rets.append((right - left) / left)
        if len(rets) < 2:
            return 0.0
        mean = sum(rets) / len(rets)
        var = sum((x - mean) ** 2 for x in rets) / (len(rets) - 1)
        return math.sqrt(var)

    def compute_rsi(self, series: list[Decimal], period: int = 14) -> float:
        if len(series) <= period:
            return 50.0
        values = [float(x) for x in series[-(period + 1) :]]
        gains: list[float] = []
        losses: list[float] = []
        for left, right in zip(values, values[1:]):
            delta = right - left
            if delta >= 0:
                gains.append(delta)
                losses.append(0.0)
            else:
                gains.append(0.0)
                losses.append(-delta)
        avg_gain = sum(gains[-period:]) / period
        avg_loss = sum(losses[-period:]) / period
        if avg_loss == 0:
            return 100.0
        rs = avg_gain / avg_loss
        return 100.0 - (100.0 / (1.0 + rs))

    def update_best_quotes(self) -> None:
        target_symbols = self.best_quote_symbols or self.symbols
        cb_ids = [SYMBOL_MAP[symbol] for symbol in target_symbols if symbol in SYMBOL_MAP]
        if not cb_ids:
            return
        try:
            data = fetch_coinbase_best_bid_ask(cb_ids)
        except Exception as exc:
            self.log(f"best bid/ask fetch failed: {exc}")
            return
        inverse = {SYMBOL_MAP[symbol]: symbol for symbol in target_symbols if symbol in SYMBOL_MAP}
        allowed = set(target_symbols)
        for product_id, quote in data.items():
            symbol = inverse.get(product_id)
            if not symbol:
                continue
            bid = quote.get("best_bid")
            ask = quote.get("best_ask")
            if not bid or not ask:
                continue
            spread_bps = ((ask - bid) / bid) * 10000
            self.spread_history.setdefault(symbol, deque(maxlen=240)).append(spread_bps)
            self.best_quotes[symbol] = quote
        for symbol in list(self.best_quotes.keys()):
            if symbol not in allowed:
                self.best_quotes.pop(symbol, None)

    def get_spread_zscore(self, symbol: str) -> float:
        history = self.spread_history.get(symbol)
        if not history or len(history) < 10:
            return 0.0
        values = list(history)
        mean = sum(values) / len(values)
        var = sum((x - mean) ** 2 for x in values) / len(values)
        std = math.sqrt(var) if var > 0 else 1e-9
        return (values[-1] - mean) / std

    def get_order_book_imbalance(self, symbol: str, depth: int = 5) -> float | None:
        product_id = SYMBOL_MAP.get(symbol)
        if not product_id:
            return None
        try:
            book = fetch_coinbase_orderbook(product_id, depth=depth)
        except Exception as exc:
            self.log(f"order book fetch failed for {symbol}: {exc}")
            return None
        bids = sum(level.get("size", 0.0) for level in book.get("bids", [])[:depth])
        asks = sum(level.get("size", 0.0) for level in book.get("asks", [])[:depth])
        total = bids + asks
        if total <= 0:
            imbalance = 0.0
        else:
            imbalance = (bids - asks) / total
        self.obi_history.setdefault(symbol, deque(maxlen=6)).append(imbalance)
        return imbalance

    def obi_sustained(self, symbol: str, threshold: float, length: int) -> bool:
        history = self.obi_history.get(symbol)
        if not history or len(history) < length:
            return False
        tail = list(history)[-length:]
        if threshold > 0:
            return all(value > threshold for value in tail)
        return all(value < threshold for value in tail)

    def get_candles(self, symbol: str, granularity: str, ttl: float = 45.0) -> list[dict[str, float]]:
        product_id = SYMBOL_MAP.get(symbol)
        if not product_id:
            return []
        key = (symbol, granularity)
        cached = self.candle_cache.get(key)
        now = time.time()
        if cached and now - cached["ts"] < ttl:
            return cached["data"]
        try:
            candles = fetch_coinbase_candles(product_id, granularity)
        except Exception as exc:
            self.log(f"candle fetch failed for {symbol} ({granularity}): {exc}")
            return []
        candles = sorted(candles, key=lambda c: c["start"])
        self.candle_cache[key] = {"ts": now, "data": candles}
        return candles

    def compute_vcm(self, symbol: str) -> tuple[float, float, float]:
        candles = self.get_candles(symbol, "ONE_MINUTE")
        if len(candles) < 6:
            return 0.0, 0.0, 0.0
        closes = [c["close"] for c in candles[-6:]]
        price_change = 0.0
        if closes[0] > 0:
            price_change = (closes[-1] - closes[0]) / closes[0]
        current_vol = candles[-1]["volume"]
        history = candles[-21:-1] if len(candles) > 21 else candles[:-1]
        avg_vol = (sum(c["volume"] for c in history) / len(history)) if history else current_vol
        volume_ratio = current_vol / avg_vol if avg_vol else 1.0
        return price_change * volume_ratio, price_change, volume_ratio

    def compute_candle_context(self, symbol: str) -> tuple[float, float] | None:
        candles = self.get_candles(symbol, "FIVE_MINUTE", ttl=120)
        if len(candles) < 24:
            return None
        closes = [c["close"] for c in candles[-24:]]
        mean = sum(closes) / len(closes)
        deviation = (closes[-1] - mean) / mean if mean else 0.0
        x = list(range(len(closes)))
        mean_x = sum(x) / len(x)
        mean_y = mean
        cov = sum((xi - mean_x) * (yi - mean_y) for xi, yi in zip(x, closes)) / len(closes)
        var_x = sum((xi - mean_x) ** 2 for xi in x) / len(closes)
        slope = cov / var_x if var_x else 0.0
        trend_pct_hr = (slope * 12) / closes[-1] if closes[-1] else 0.0
        return deviation, trend_pct_hr

    def ratio_zscore(self, alt_symbol: str, lookback: int = 120) -> tuple[float, float, float] | None:
        btc_hist = self.history.get("BTCUSDT", [])
        alt_hist = self.history.get(alt_symbol, [])
        if len(btc_hist) < lookback or len(alt_hist) < lookback:
            return None
        btc_vals = [float(x) for x in btc_hist[-lookback:]]
        alt_vals = [float(x) for x in alt_hist[-lookback:]]
        ratios = [a / b for a, b in zip(alt_vals, btc_vals) if b > 0]
        if len(ratios) < 20:
            return None
        mean_r = sum(ratios) / len(ratios)
        var_r = sum((r - mean_r) ** 2 for r in ratios) / len(ratios)
        std_r = math.sqrt(var_r)
        if std_r < 1e-12:
            return None
        return (ratios[-1] - mean_r) / std_r, ratios[-1], mean_r

    def holdings_qty(self, balances: dict[str, Decimal], symbol: str) -> Decimal:
        base, _ = split_symbol(symbol)
        qty = balances.get(base, ZERO)
        return qty if qty > ZERO else ZERO

    def holdings_short_qty(self, balances: dict[str, Decimal], symbol: str) -> Decimal:
        base, _ = split_symbol(symbol)
        qty = balances.get(base, ZERO)
        return abs(qty) if qty < ZERO else ZERO

    def usdt_balance(self, balances: dict[str, Decimal]) -> Decimal:
        return balances.get("USDT", ZERO)

    def estimate_portfolio_value(self, state: BotState) -> Decimal:
        total = self.usdt_balance(state.balances)
        for asset, qty in state.balances.items():
            if asset in {"USDT", "USDC"}:
                continue
            symbol = f"{asset}USDT"
            price = state.marks.get(symbol, ZERO)
            if price <= ZERO:
                price = self.lookup_latest_mark(symbol)
            total += qty * price
        return total

    def position_notional(self, balances: dict[str, Decimal], symbol: str, marks: dict[str, Decimal]) -> Decimal:
        qty = self.holdings_qty(balances, symbol)
        if qty <= ZERO:
            return ZERO
        price = marks.get(symbol, ZERO)
        if price <= ZERO:
            price = self.lookup_latest_mark(symbol)
        if price <= ZERO:
            return ZERO
        return qty * price

    def lookup_latest_mark(self, symbol: str, ttl: float = 60.0) -> Decimal:
        now = time.time()
        cached = self.latest_mark_cache.get(symbol)
        if cached and now - cached[0] < ttl:
            return cached[1]
        try:
            with self.get_conn() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        SELECT mark_price
                        FROM market_marks
                        WHERE season_id = %s AND symbol = %s
                        ORDER BY ts DESC
                        LIMIT 1
                        """,
                        (self.season_id, symbol),
                    )
                    row = cur.fetchone()
        except Exception:
            row = None
        price = Decimal(str(row["mark_price"])) if row and row["mark_price"] is not None else ZERO
        self.latest_mark_cache[symbol] = (now, price)
        return price

    def can_trade(self, bot_id: str, symbol: str, cooldown_seconds: float, now: float) -> bool:
        key = f"{bot_id}:{symbol}"
        last = self.symbol_cooldowns.get(key, 0.0)
        return now - last >= cooldown_seconds

    def mark_trade(self, bot_id: str, symbol: str, now: float) -> None:
        key = f"{bot_id}:{symbol}"
        self.symbol_cooldowns[key] = now
        self.bot_cooldowns[bot_id] = now

    def set_position(self, bot_id: str, symbol: str, price: float, side: str) -> None:
        position = {
            "entry_price": price,
            "entry_time": time.time(),
            "side": side,
            "last_update": self.tick,
        }
        self.bot_positions.setdefault(bot_id, {})[symbol] = position

    def get_position(self, bot_id: str, symbol: str) -> dict[str, Any] | None:
        return self.bot_positions.get(bot_id, {}).get(symbol)

    def clear_position(self, bot_id: str, symbol: str) -> None:
        self.bot_positions.get(bot_id, {}).pop(symbol, None)
        self.short_positions.get(bot_id, {}).pop(symbol, None)

    def maybe_refill_quote_liquidity(self, state: BotState) -> None:
        usdt = self.usdt_balance(state.balances)
        btc = state.balances.get("BTC", ZERO)
        if usdt >= Decimal("200") or btc <= Decimal("0.01"):
            return
        btc_momentum = self.pct_change(list(state.history["BTCUSDT"]), 30)
        if btc_momentum > 0.015:
            return
        sell_qty = btc * Decimal("0.10")
        if sell_qty <= ZERO:
            return
        self.place_order(
            state.bot_id,
            "BTCUSDT",
            "SELL",
            sell_qty,
            {
                "strategy": "btc_reserve_refill_v1",
                "btc_momentum": round(btc_momentum, 6),
                "note": "refill_usdt_liquidity",
            },
        )

    # ── order plumbing ────────────────────────────────────────────────────
    def place_order(
        self,
        bot_id: str,
        symbol: str,
        side: str,
        quantity: Decimal,
        rationale: dict[str, Any],
        metadata: dict[str, Any] | None = None,
    ) -> None:
        quantity = self.quant(quantity)
        if quantity <= ZERO:
            return
        reference_price = self.current_marks().get(symbol, ZERO)
        if reference_price <= ZERO:
            reference_price = self.lookup_latest_mark(symbol)
        min_qty = self.min_order_qty(reference_price)
        if quantity < min_qty:
            self.log(
                f"skip order {bot_id} {side} {symbol}: qty={quantity} below minimum {min_qty}"
            )
            return
        if reference_price > ZERO:
            notional = quantity * reference_price
            if notional < MIN_ORDER_NOTIONAL_USDT:
                self.log(
                    f"skip order {bot_id} {side} {symbol}: notional={notional:.8f} below minimum {MIN_ORDER_NOTIONAL_USDT}"
                )
                return
        payload = {
            "season_id": self.season_id,
            "bot_id": bot_id,
            "symbol": symbol,
            "side": side,
            "order_type": "market",
            "quantity": float(quantity),
            "rationale": rationale,
            "metadata": {
                "runtime": "season_003",
                "tick": self.tick,
                **(metadata or {}),
            },
        }
        response = requests.post(f"{self.trade_engine_url}/orders", json=payload, timeout=10)
        if response.ok:
            body = response.json()
            self.log(
                f"order {bot_id} {side} {symbol} qty={quantity} fill={body.get('fill_price', 'na')}"
            )
        else:
            self.log(f"order rejected for {bot_id}: {response.status_code} {response.text}")

    # ── pump token refresh ────────────────────────────────────────────────
    def refresh_pump_tokens(self) -> None:
        now = time.time()
        if now - self.last_pump_refresh < 60.0:
            return
        try:
            tokens = fetch_top_solana_tokens()
            self.pump_tokens = tokens
            self.pump_prices = {}
            for t in tokens:
                sym = t.get("symbol", "")
                price = t.get("price_usd", 0.0)
                if sym and price > 0:
                    self.pump_prices[sym] = price
            self.last_pump_refresh = now
            self.log(f"refreshed pump tokens: {len(tokens)} tokens")
        except Exception as exc:
            self.log(f"pump token refresh failed: {exc}")

    # ── BOT 1: degen_ape_9000 ────────────────────────────────────────────
    def degen_ape_9000_logic(self, state: BotState) -> None:
        bot_id = state.bot_id
        now = state.timestamp
        memecoin_symbols = ["SHIBUSDT", "PEPEUSDT", "WIFUSDT", "BONKUSDT", "FLOKIUSDT", "DOGEUSDT"]
        usdt = self.usdt_balance(state.balances)

        # Check cooldown (10 min per bot for scanning/buying)
        last_bot_trade = self.bot_cooldowns.get(bot_id, 0.0)
        scan_ok = (now - last_bot_trade) >= 600.0

        # Score each memecoin (short + medium lookback windows)
        fast_lb = 24   # ~2 minutes at 5s loops
        slow_lb = 120  # ~10 minutes at 5s loops
        scores: dict[str, float] = {}
        for sym in memecoin_symbols:
            series = list(state.history.get(sym, []))
            mom_fast = self.pct_change(series, fast_lb)
            mom_slow = self.pct_change(series, slow_lb) if len(series) > slow_lb else 0.0
            score = (mom_fast * 1.5) + (mom_slow * 0.5)
            scores[sym] = score

        # Position management: check existing positions every loop
        for sym in list(self.bot_positions.get(bot_id, {}).keys()):
            pos = self.get_position(bot_id, sym)
            if not pos:
                continue
            held_qty = self.holdings_qty(state.balances, sym)
            if held_qty <= ZERO:
                self.clear_position(bot_id, sym)
                continue
            price = state.marks.get(sym)
            if not price:
                continue
            entry_price = pos["entry_price"]
            pnl = (float(price) - entry_price) / entry_price if entry_price > 0 else 0.0
            age = now - pos["entry_time"]
            current_score = scores.get(sym, 0.0)
            exit_reason = None
            if pnl >= 0.40:
                exit_reason = "take_profit_40pct"
            elif pnl <= -0.20:
                exit_reason = "stop_loss_20pct"
            elif age >= 6 * 3600:
                exit_reason = "max_hold_6h"
            elif current_score < 0.0:
                exit_reason = "score_gone_negative"
            # Rotation: find if another coin scores 2x better
            if not exit_reason and current_score > 0:
                best_other_score = max(
                    (s for k, s in scores.items() if k != sym),
                    default=0.0,
                )
                if best_other_score >= current_score * 2:
                    exit_reason = "rotation_better_signal"
            if exit_reason:
                self.place_order(
                    bot_id, sym, "SELL", held_qty,
                    {"strategy": "degen_ape_momentum_v1", "exit_reason": exit_reason, "pnl_pct": round(pnl, 5)},
                )
                self.clear_position(bot_id, sym)
                self.mark_trade(bot_id, sym, now)

        # Entry logic: only when cooldown allows
        if not scan_ok:
            return
        if usdt < Decimal("10"):
            return

        # Find top scorer
        already_held = {
            sym for sym in memecoin_symbols
            if self.holdings_qty(state.balances, sym) > ZERO
        }
        eligible = {sym: sc for sym, sc in scores.items() if sym not in already_held}
        if not eligible:
            return
        best_sym = max(eligible, key=lambda k: eligible[k])
        best_score = eligible[best_sym]
        if best_score <= 0.01:
            return

        price = state.marks.get(best_sym)
        if not price or price <= ZERO:
            return

        alloc = min(usdt * Decimal("0.70"), usdt)
        qty = alloc / price
        self.place_order(
            bot_id, best_sym, "BUY", qty,
            {
                "strategy": "degen_ape_momentum_v1",
                "score": round(best_score, 6),
                "scores": {k: round(v, 6) for k, v in scores.items()},
            },
        )
        self.set_position(bot_id, best_sym, float(price), "long")
        self.mark_trade(bot_id, best_sym, now)

    # ── BOT 2: pump_surfer ────────────────────────────────────────────────
    def pump_surfer_logic(self, state: BotState) -> None:
        bot_id = state.bot_id
        now = state.timestamp
        usdt = self.usdt_balance(state.balances)

        # Publish pump token prices to trade engine for MTM
        if self.pump_prices:
            pump_marks_float = {sym: price for sym, price in self.pump_prices.items() if price > 0}
            if pump_marks_float:
                try:
                    self.publish_marks(pump_marks_float)
                except Exception as exc:
                    self.log(f"pump marks publish failed: {exc}")

        # BTC hedge: if mostly cash and no BTC, buy small hedge
        btc_qty = state.balances.get("BTC", ZERO)
        if usdt > Decimal("80") and btc_qty <= ZERO:
            total_val = self.estimate_portfolio_value(state)
            if total_val > ZERO:
                usdt_pct = usdt / total_val
                if usdt_pct > Decimal("0.80"):
                    btc_price = state.marks.get("BTCUSDT", ZERO)
                    if btc_price > ZERO:
                        hedge_alloc = usdt * Decimal("0.10")
                        hedge_qty = hedge_alloc / btc_price
                        self.place_order(
                            bot_id, "BTCUSDT", "BUY", hedge_qty,
                            {"strategy": "pump_surfer_btc_hedge_v1", "note": "usdt_heavy_hedge"},
                        )

        # Position management: check existing pump positions
        for sym in list(self.pump_positions.keys()):
            pos = self.pump_positions[sym]
            entry_price = pos.get("entry_price", 0.0)
            entry_time = pos.get("entry_time", now)
            age = now - entry_time

            # Get current price from pump tokens
            current_price = self.pump_prices.get(sym, 0.0)
            if current_price > 0 and entry_price > 0:
                pnl = (current_price - entry_price) / entry_price
            else:
                pnl = 0.0

            # Check if token still in top 10
            top_symbols = {t["symbol"] for t in self.pump_tokens}
            token_gone = sym not in top_symbols

            exit_reason = None
            if pnl >= 1.0:
                exit_reason = "take_profit_2x"
            elif pnl <= -0.40:
                exit_reason = "stop_loss_40pct"
            elif age >= 2 * 3600:
                exit_reason = "max_hold_2h"
            elif token_gone:
                exit_reason = "token_left_top10"

            if exit_reason:
                # Submit SELL order for this pump token
                # Use held qty from balances
                try:
                    base, _ = split_symbol(sym)
                    held_qty = state.balances.get(base, ZERO)
                    if held_qty > ZERO:
                        self.place_order(
                            bot_id, sym, "SELL", held_qty,
                            {"strategy": "pump_surfer_dex_v1", "exit_reason": exit_reason, "pnl_pct": round(pnl, 5)},
                        )
                except ValueError:
                    pass
                del self.pump_positions[sym]

        # Entry logic: every 5 minutes (cooldown)
        last_surf_trade = self.bot_cooldowns.get(bot_id, 0.0)
        if now - last_surf_trade < 300.0:
            return
        if not self.pump_tokens:
            return

        # Pick top 3 by price_change_24h where change > 20%
        eligible = [t for t in self.pump_tokens if t.get("price_change_24h", 0) > 5]
        eligible.sort(key=lambda t: t.get("price_change_24h", 0), reverse=True)
        top3 = eligible[:3]

        if not top3:
            return

        usdt = self.usdt_balance(state.balances)
        for token in top3:
            sym = token["symbol"]
            if sym in self.pump_positions:
                continue  # already holding
            price = token.get("price_usd", 0.0)
            if price <= 0:
                continue
            alloc = usdt * Decimal("0.25")
            if alloc < Decimal("5"):
                continue
            qty = alloc / Decimal(str(price))
            self.place_order(
                bot_id, sym, "BUY", qty,
                {
                    "strategy": "pump_surfer_dex_v1",
                    "price_change_24h": token.get("price_change_24h"),
                    "volume_24h": token.get("volume_24h"),
                    "name": token.get("name"),
                },
                metadata={"price_override": price},
            )
            self.pump_positions[sym] = {
                "entry_price": price,
                "entry_time": now,
                "token_info": token,
            }
            usdt -= alloc

        self.bot_cooldowns[bot_id] = now

    # ── BOT 3: chaos_prophet ──────────────────────────────────────────────
    def chaos_prophet_logic(self, state: BotState) -> None:
        bot_id = state.bot_id
        now = state.timestamp
        usdt = self.usdt_balance(state.balances)

        # Emergency exit: if portfolio < 65% of starting value
        starting_value = Decimal(str(self.starting_btc)) * state.marks.get("BTCUSDT", Decimal("65000"))
        current_value = self.estimate_portfolio_value(state)
        non_cash_assets = [
            asset for asset, qty in state.balances.items()
            if asset not in {"USDT", "USDC"} and qty > ZERO
        ]
        if current_value <= ZERO and not non_cash_assets and self.usdt_balance(state.balances) <= ZERO:
            self.log("[chaos_prophet] no funded balances for current season; skipping emergency exit check")
            return
        if current_value < starting_value * Decimal("0.65"):
            self.log(f"[chaos_prophet] EMERGENCY EXIT: portfolio at {float(current_value):.2f} vs starting {float(starting_value):.2f}")
            for asset, qty in state.balances.items():
                if asset in {"USDT", "USDC"} or qty <= ZERO:
                    continue
                sym = f"{asset}USDT"
                self.place_order(bot_id, sym, "SELL", qty, {"strategy": "chaos_prophet_emergency_exit"})
            self.chaos_positions.clear()
            self.chaos_shorts.clear()
            return

        # Manage existing chaos long positions
        for sym in list(self.chaos_positions.keys()):
            pos = self.chaos_positions[sym]
            held_qty = self.holdings_qty(state.balances, sym)
            if held_qty <= ZERO:
                del self.chaos_positions[sym]
                continue
            if self.position_notional(state.balances, sym, state.marks) < MIN_POSITION_NOTIONAL_USDT:
                del self.chaos_positions[sym]
                continue
            price = state.marks.get(sym)
            if not price:
                continue
            entry_price = pos.get("entry_price", float(price))
            pnl = (float(price) - entry_price) / entry_price if entry_price > 0 else 0.0
            age = now - pos.get("entry_time", now)
            strategy = pos.get("strategy", "fallen_angel_v1")
            exit_reason = None
            if strategy == "fallen_angel_v1":
                if pnl >= 0.15:
                    exit_reason = "take_profit_15pct"
                elif pnl <= -0.12:
                    exit_reason = "stop_loss_12pct"
                elif age >= 3 * 3600:
                    exit_reason = "max_hold_3h"
            if exit_reason:
                self.place_order(
                    bot_id, sym, "SELL", held_qty,
                    {"strategy": strategy, "exit_reason": exit_reason, "pnl_pct": round(pnl, 5)},
                )
                del self.chaos_positions[sym]
                self.mark_trade(bot_id, sym, now)

        # Manage chaos short positions
        for sym in list(self.chaos_shorts.keys()):
            pos = self.chaos_shorts[sym]
            entry_price = pos.get("entry_price", 0.0)
            entry_time = pos.get("entry_time", now)
            age = now - entry_time
            # Get current price
            current_price = self.pump_prices.get(sym, 0.0) or float(state.marks.get(sym, ZERO))
            if entry_price > 0 and current_price > 0:
                # For SHORT: profit when price goes down
                pnl = (entry_price - current_price) / entry_price
            else:
                pnl = 0.0
            exit_reason = None
            if pnl >= 0.25:
                exit_reason = "take_profit_25pct"
            elif pnl <= -0.20:
                exit_reason = "stop_loss_20pct"
            elif age >= 4 * 3600:
                exit_reason = "max_hold_4h"
            if exit_reason:
                # Synthetic exit via SOLUSDT proxy (small qty)
                sol_price = state.marks.get("SOLUSDT", Decimal("140"))
                proxy_qty = Decimal("0.1")  # nominal proxy trade
                self.place_order(
                    bot_id, "SOLUSDT", "BUY", proxy_qty,
                    {"strategy": "chaos_gambit_fade_pump_v1", "exit_reason": exit_reason,
                     "synthetic_short_exit": sym, "pnl_pct": round(pnl, 5)},
                )
                del self.chaos_shorts[sym]

        # Determine current strategy phase based on tick
        phase = self.tick % 480
        last_trade = self.bot_cooldowns.get(bot_id, 0.0)
        coinbase_memecoins = ["SHIBUSDT", "PEPEUSDT", "WIFUSDT", "BONKUSDT", "FLOKIUSDT", "DOGEUSDT"]

        if phase < 240:
            # Strategy A: Fallen Angel — find biggest loser
            if now - last_trade < 180.0:  # 5 min cooldown for this strategy
                return
            if usdt < Decimal("20"):
                return

            # Find biggest loser in last 4h (48 ticks)
            losers = []
            for sym in self.symbols:
                series = list(state.history.get(sym, []))
                change_4h = self.pct_change(series, 240)
                rsi = self.compute_rsi(series, 14)
                losers.append({"symbol": sym, "change_4h": change_4h, "rsi": rsi})

            losers.sort(key=lambda x: x["change_4h"])
            if not losers:
                return
            worst = losers[0]

            if worst["change_4h"] < -0.03 and worst["rsi"] < 40:
                sym = worst["symbol"]
                if sym in self.chaos_positions:
                    return  # already holding
                price = state.marks.get(sym)
                if not price or price <= ZERO:
                    return
                alloc = usdt * Decimal("0.35")
                qty = alloc / price
                self.place_order(
                    bot_id, sym, "BUY", qty,
                    {
                        "strategy": "fallen_angel_v1",
                        "change_4h": round(worst["change_4h"], 5),
                        "rsi": round(worst["rsi"], 2),
                    },
                )
                self.chaos_positions[sym] = {
                    "entry_price": float(price),
                    "entry_time": now,
                    "strategy": "fallen_angel_v1",
                }
                self.mark_trade(bot_id, sym, now)

        else:
            # Strategy B: Chaos Gambit — fade pumps / short
            if now - last_trade < 300.0:
                return
            if usdt < Decimal("20"):
                return

            short_target_sym = None
            short_price = 0.0
            short_source = None

            # Look for pump tokens up >80% with volume > 100k
            for token in self.pump_tokens:
                if (token.get("price_change_24h", 0) > 80
                        and token.get("volume_24h", 0) > 100000
                        and token.get("price_usd", 0) > 0):
                    short_target_sym = token["symbol"]
                    short_price = token["price_usd"]
                    short_source = "dex_pump_token"
                    break

            # Fallback: find Coinbase memecoin up >15% in last 2h (24 ticks)
            if not short_target_sym:
                for sym in coinbase_memecoins:
                    series = list(state.history.get(sym, []))
                    change_2h = self.pct_change(series, 120)
                    if change_2h > 0.05:
                        price = state.marks.get(sym)
                        if price and price > ZERO:
                            short_target_sym = sym
                            short_price = float(price)
                            short_source = "coinbase_memecoin"
                            break

            if not short_target_sym:
                return
            if short_target_sym in self.chaos_shorts:
                return  # already short

            # For DexScreener tokens (no Coinbase pair): synthetic short via local tracking
            if short_source == "dex_pump_token":
                alloc = usdt * Decimal("0.20")
                # Track synthetic short locally, submit proxy trade on SOLUSDT
                sol_price = state.marks.get("SOLUSDT", Decimal("140"))
                proxy_qty = alloc / sol_price
                self.place_order(
                    bot_id, "SOLUSDT", "SELL", proxy_qty,
                    {
                        "strategy": "chaos_gambit_fade_pump_v1",
                        "short_target": short_target_sym,
                        "short_price": short_price,
                        "short_source": short_source,
                        "note": "synthetic_short_via_sol_proxy",
                    },
                )
                self.chaos_shorts[short_target_sym] = {
                    "entry_price": short_price,
                    "entry_time": now,
                    "synthetic": True,
                }
            else:
                # Real Coinbase memecoin: submit actual SHORT order
                price_dec = state.marks.get(short_target_sym, ZERO)
                if price_dec <= ZERO:
                    return
                alloc = usdt * Decimal("0.20")
                qty = alloc / price_dec
                self.place_order(
                    bot_id, short_target_sym, "SHORT", qty,
                    {
                        "strategy": "chaos_gambit_fade_pump_v1",
                        "short_source": short_source,
                    },
                )
                self.short_positions.setdefault(bot_id, {})[short_target_sym] = {
                    "entry_price": float(price_dec),
                    "entry_time": now,
                }
                self.chaos_shorts[short_target_sym] = {
                    "entry_price": float(price_dec),
                    "entry_time": now,
                    "synthetic": False,
                }

            self.mark_trade(bot_id, short_target_sym, now)

    # ── runtime orchestration ────────────────────────────────────────────
    def run_bots(self) -> None:
        marks = self.current_marks()
        history = {symbol: list(self.history[symbol]) for symbol in self.symbols}
        timestamp = time.time()
        bot_ids = [
            "degen_ape_9000",
            "pump_surfer",
            "chaos_prophet",
        ]
        for bot_id in bot_ids:
            state = BotState(
                bot_id=bot_id,
                marks=marks,
                history=history,
                balances=self.get_balances(bot_id),
                tick=self.tick,
                timestamp=timestamp,
                best_quotes=self.best_quotes,
            )
            self.maybe_refill_quote_liquidity(state)
            if bot_id == "degen_ape_9000":
                self.degen_ape_9000_logic(state)
            elif bot_id == "pump_surfer":
                self.pump_surfer_logic(state)
            elif bot_id == "chaos_prophet":
                self.chaos_prophet_logic(state)

    def fetch_live_marks(self) -> dict[str, float] | None:
        prices = fetch_coinbase_prices_safe(self.symbols, log_fn=self.log)
        if prices is None:
            return None
        self.tick += 1
        marks: dict[str, float] = {}
        for symbol in self.symbols:
            price = prices.get(symbol) if prices else None
            if price is not None:
                self.state[symbol]["price"] = price
            current_price = self.state[symbol]["price"]
            self.history[symbol].append(Decimal(str(current_price)))
            marks[symbol] = round(current_price, 8)
        self.update_best_quotes()
        return marks

    def run(self) -> None:
        self.log(
            f"starting runtime source={self.source} season={self.season_id} loop={self.loop_seconds}s"
        )
        self.wait_for_dependencies()
        self.maybe_bootstrap()
        if self.source == "coinbase" and not self._initial_seed_done:
            try:
                self._seed_initial_coinbase_prices()
            except Exception as exc:
                self.log(f"initial Coinbase price seed failed during startup: {exc}")
            self._initial_seed_done = True
        consecutive_failures = 0
        while True:
            try:
                # Refresh pump tokens every ~60s
                self.refresh_pump_tokens()

                if self.source == "coinbase":
                    marks = self.fetch_live_marks()
                    if marks is None:
                        consecutive_failures += 1
                        self.log(f"live feed failure #{consecutive_failures}; skipping tick")
                        time.sleep(min(self.loop_seconds * consecutive_failures, 30))
                        continue
                    consecutive_failures = 0
                else:
                    marks = self.update_synthetic_market()

                # Merge pump prices into marks for publishing
                full_marks = dict(marks)
                for sym, price in self.pump_prices.items():
                    if price > 0:
                        full_marks[sym] = price

                self.publish_marks(full_marks)
                self.run_bots()
                self.log(
                    "published marks "
                    + json.dumps({k: round(v, 8) for k, v in list(marks.items())[:4]})
                    + f" (+{len(self.pump_prices)} pump tokens)"
                    + (" source=coinbase" if self.source == "coinbase" else " synthetic")
                )
                time.sleep(self.loop_seconds)
            except Exception as exc:
                consecutive_failures += 1
                self.log(f"main loop failure #{consecutive_failures}: {exc}")
                time.sleep(min(self.loop_seconds * consecutive_failures, 30))


def split_symbol(symbol: str) -> tuple[str, str]:
    symbol = symbol.upper()
    for quote in ("USDT", "BTC", "USD"):
        if symbol.endswith(quote):
            return symbol[: -len(quote)], quote
    raise ValueError(f"Unsupported symbol: {symbol}")


def main() -> None:
    LeagueRuntime().run()


if __name__ == "__main__":
    main()
