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

ZERO = Decimal("0")
SAT = Decimal("0.00000001")


CORE_SYMBOL_DEFAULTS = {
    "BTCUSDT": {"price": 65000.0, "drift": 0.0004, "amp": 0.006},
    "ETHUSDT": {"price": 3400.0, "drift": 0.0008, "amp": 0.011},
    "SOLUSDT": {"price": 140.0, "drift": 0.0012, "amp": 0.02},
    "DOGEUSDT": {"price": 0.15, "drift": 0.0015, "amp": 0.03},
}
GENERIC_SYMBOL_TEMPLATE = {"price": 1.0, "drift": 0.0008, "amp": 0.015}
DEFAULT_BEST_QUOTE_SYMBOLS = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "DOGEUSDT"]


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
        self.season_id = os.getenv("DEFAULT_SEASON_ID", "season-002")
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
            symbols = dynamic_symbols or core_symbols
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
        if self.source == "coinbase":
            self._seed_initial_coinbase_prices()
        self.bot_positions: dict[str, dict[str, dict[str, Any]]] = {}
        self.bot_cooldowns: dict[str, float] = {}
        self.symbol_cooldowns: dict[str, float] = {}
        self.short_positions: dict[str, dict[str, dict[str, Any]]] = {}

    # ── infra helpers ──────────────────────────────────────────────────────
    def log(self, message: str) -> None:
        print(f"[data_ingest] {datetime.now(timezone.utc).isoformat()} {message}", flush=True)

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
        response = requests.post(
            f"{self.trade_engine_url}/season/bootstrap", json=payload, timeout=10
        )
        response.raise_for_status()
        self.log(f"bootstrapped season {self.season_id}")


    # ── market + math helpers ─────────────────────────────────────────────
    def current_marks(self) -> dict[str, Decimal]:
        return {symbol: Decimal(str(meta["price"])) for symbol, meta in self.state.items()}

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
            total += qty * price
        return total

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
        btc_momentum = self.pct_change(state.history["BTCUSDT"], 30)
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
        payload = {
            "season_id": self.season_id,
            "bot_id": bot_id,
            "symbol": symbol,
            "side": side,
            "order_type": "market",
            "quantity": float(quantity),
            "rationale": rationale,
            "metadata": {
                "runtime": "experiment_2",
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

    # ── bot logic ─────────────────────────────────────────────────────────
    def solstice_drift_logic(self, state: BotState) -> None:
        now = state.timestamp
        btc_hist = state.history["BTCUSDT"]
        btc_trend = self.pct_change(btc_hist, 60)
        usdt = self.usdt_balance(state.balances)
        if usdt < Decimal("75"):
            return
        last_trade = self.bot_cooldowns.get(state.bot_id, 0)
        if now - last_trade < 1800:
            return
        candidates = []
        for symbol in ["ETHUSDT", "SOLUSDT"]:
            series = state.history.get(symbol, [])
            if len(series) < 60:
                continue
            rel = self.pct_change(series, 12) - self.pct_change(btc_hist, 12)
            trend = self.pct_change(series, 30)
            rsi = self.compute_rsi(series, 14)
            rsi_signal = (50.0 - rsi) / 50.0
            vol = self.stdev_returns(series, 24)
            conviction = (rel * 2.0) + (trend * 1.5) + (rsi_signal * 0.5) - (vol * 1.5) + (btc_trend * 0.3)
            candidates.append(
                {
                    "symbol": symbol,
                    "conviction": conviction,
                    "rsi": rsi,
                    "rel": rel,
                    "trend": trend,
                    "vol": vol,
                }
            )
        if not candidates:
            return
        best = max(candidates, key=lambda c: c["conviction"])
        symbol = best["symbol"]
        price = state.marks[symbol]
        held_qty = self.holdings_qty(state.balances, symbol)
        position = self.get_position(state.bot_id, symbol)
        conviction = best["conviction"]
        if (
            held_qty <= ZERO
            and conviction > 0.08
            and best["rsi"] < 60
            and btc_trend > -0.005
        ):
            scale = min(max(conviction / 0.20, 0.0), 1.0)
            alloc_pct = Decimal(str(0.15 + (scale * 0.15)))
            alloc = usdt * alloc_pct
            qty = alloc / price
            self.place_order(
                state.bot_id,
                symbol,
                "BUY",
                qty,
                {
                    "strategy": "solstice_drift_momentum_v1",
                    "conviction": round(conviction, 6),
                    "relative_strength": round(best["rel"], 6),
                    "trend_30": round(best["trend"], 6),
                    "rsi": round(best["rsi"], 2),
                    "volatility": round(best["vol"], 6),
                    "btc_trend": round(btc_trend, 6),
                },
            )
            self.set_position(state.bot_id, symbol, float(price), "long")
            self.mark_trade(state.bot_id, symbol, now)
            return

        if held_qty > ZERO:
            entry = position or {
                "entry_price": float(price),
                "entry_time": now,
                "side": "long",
            }
            pnl = (float(price) - entry["entry_price"]) / entry["entry_price"]
            age = now - entry["entry_time"]
            exit_reason = None
            if pnl <= -0.025:
                exit_reason = "stop_loss"
            elif pnl >= 0.04:
                exit_reason = "take_profit"
            elif conviction < -0.05 or best["rsi"] > 70:
                exit_reason = "signal_flip"
            elif age >= 4 * 3600:
                exit_reason = "max_hold"
            if exit_reason:
                self.place_order(
                    state.bot_id,
                    symbol,
                    "SELL",
                    held_qty,
                    {
                        "strategy": "solstice_drift_momentum_v1",
                        "exit_reason": exit_reason,
                        "conviction": round(conviction, 6),
                        "pnl_pct": round(pnl, 6),
                    },
                )
                self.clear_position(state.bot_id, symbol)
                self.mark_trade(state.bot_id, symbol, now)

    def obsidian_flux_logic(self, state: BotState) -> None:
        now = state.timestamp
        usdt = self.usdt_balance(state.balances)
        self.handle_obsidian_short_covers(state)
        if usdt < Decimal("100"):
            return
        for symbol in ["BTCUSDT", "ETHUSDT"]:
            price = state.marks[symbol]
            obi = self.get_order_book_imbalance(symbol, depth=5)
            if obi is None:
                continue
            vcm, price_change, volume_ratio = self.compute_vcm(symbol)
            spread_z = self.get_spread_zscore(symbol)
            held_qty = self.holdings_qty(state.balances, symbol)
            short_qty = self.holdings_short_qty(state.balances, symbol)
            portfolio = self.estimate_portfolio_value(state)
            max_position_value = portfolio * Decimal("0.25")
            position_value = held_qty * price
            cooldown_ok = self.can_trade(state.bot_id, symbol, 60, now)
            if (
                cooldown_ok
                and held_qty <= ZERO
                and obi is not None
                and self.obi_sustained(symbol, 0.25, 3)
                and vcm > 0.003
                and spread_z < -0.5
                and position_value < max_position_value
            ):
                alloc = min(usdt * Decimal("0.08"), max_position_value - position_value)
                if alloc > ZERO:
                    qty = alloc / price
                    self.place_order(
                        state.bot_id,
                        symbol,
                        "BUY",
                        qty,
                        {
                            "strategy": "obsidian_flux_orderflow_v1",
                            "obi": round(obi, 4),
                            "vcm": round(vcm, 6),
                            "price_change_5m": round(price_change, 6),
                            "volume_ratio": round(volume_ratio, 3),
                            "spread_z": round(spread_z, 3),
                        },
                    )
                    self.set_position(state.bot_id, symbol, float(price), "long")
                    self.mark_trade(state.bot_id, symbol, now)
                    return
            if (
                cooldown_ok
                and short_qty <= ZERO
                and obi is not None
                and self.obi_sustained(symbol, -0.25, 3)
                and vcm < -0.003
                and spread_z < 1.0
                and usdt >= Decimal("150")
            ):
                qty = (usdt * Decimal("0.08")) / price
                self.place_order(
                    state.bot_id,
                    symbol,
                    "SHORT",
                    qty,
                    {
                        "strategy": "obsidian_flux_orderflow_v1",
                        "obi": round(obi, 4),
                        "vcm": round(vcm, 6),
                        "price_change_5m": round(price_change, 6),
                        "volume_ratio": round(volume_ratio, 3),
                        "spread_z": round(spread_z, 3),
                        "signal": "bearish_breakout",
                    },
                )
                self.short_positions.setdefault(state.bot_id, {})[symbol] = {
                    "entry_price": float(price),
                    "entry_time": now,
                }
                self.mark_trade(state.bot_id, symbol, now)
                return
            if held_qty > ZERO and (obi < -0.15 or vcm < -0.001):
                self.place_order(
                    state.bot_id,
                    symbol,
                    "SELL",
                    held_qty,
                    {
                        "strategy": "obsidian_flux_orderflow_v1",
                        "obi": round(obi, 4),
                        "vcm": round(vcm, 6),
                        "exit_reason": "orderflow_reversal",
                    },
                )
                self.clear_position(state.bot_id, symbol)
                self.mark_trade(state.bot_id, symbol, now)

    def handle_obsidian_short_covers(self, state: BotState) -> None:
        now = state.timestamp
        for symbol in ["BTCUSDT", "ETHUSDT"]:
            short_qty = self.holdings_short_qty(state.balances, symbol)
            if short_qty <= ZERO:
                continue
            obi = self.get_order_book_imbalance(symbol, depth=5)
            vcm, _, _ = self.compute_vcm(symbol)
            entry = self.short_positions.get(state.bot_id, {}).get(symbol, {})
            age = now - entry.get("entry_time", now)
            if (obi and obi > 0.1) or vcm > 0.001 or age > 300:
                self.place_order(
                    state.bot_id,
                    symbol,
                    "COVER",
                    short_qty,
                    {
                        "strategy": "obsidian_flux_orderflow_v1",
                        "obi": round(obi or 0.0, 4),
                        "vcm": round(vcm, 6),
                        "exit_reason": "short_cover",
                    },
                )
                self.clear_position(state.bot_id, symbol)
                self.mark_trade(state.bot_id, symbol, now)

    def vega_pulse_logic(self, state: BotState) -> None:
        now = state.timestamp
        usdt = self.usdt_balance(state.balances)
        if usdt < Decimal("60"):
            return
        active_positions = self.bot_positions.get(state.bot_id, {})
        if len(active_positions) >= 3:
            return
        best_signal = None
        for symbol in ["ETHUSDT", "SOLUSDT", "DOGEUSDT"]:
            series = state.history.get(symbol, [])
            if len(series) < 10:
                continue
            tick_values = [float(x) for x in series[-6:]]
            tick_mean = sum(tick_values[:-1]) / len(tick_values[:-1]) if len(tick_values) > 1 else tick_values[-1]
            tick_dev = (tick_values[-1] - tick_mean) / tick_mean if tick_mean else 0.0
            bounce = self.pct_change(series, 1)
            context = self.compute_candle_context(symbol)
            if context is None:
                continue
            candle_dev, trend_hr = context
            quote = self.best_quotes.get(symbol)
            if not quote:
                continue
            spread = quote["best_ask"] - quote["best_bid"]
            spread_bps = (spread / quote["best_bid"]) * 10000 if quote["best_bid"] else 0.0
            obi = self.get_order_book_imbalance(symbol, depth=5)
            if obi is None:
                continue
            conditions = (
                (tick_dev < -0.0025 or bounce < -0.003)
                and candle_dev < -0.003
                and spread_bps < 20
                and obi > 0.0
                and trend_hr > -0.002
            )
            if not conditions:
                continue
            score = (-candle_dev * 2.0) + (-bounce * 0.8) + (obi * 1.5) - (spread_bps * 0.05)
            best_signal = {
                "symbol": symbol,
                "score": score,
                "tick_dev": tick_dev,
                "bounce": bounce,
                "candle_dev": candle_dev,
                "trend_hr": trend_hr,
                "obi": obi,
                "spread_bps": spread_bps,
            }
            break
        if best_signal:
            symbol = best_signal["symbol"]
            price = state.marks[symbol]
            qty = (usdt * Decimal("0.10")) / price
            self.place_order(
                state.bot_id,
                symbol,
                "BUY",
                qty,
                {
                    "strategy": "vega_pulse_microstructure_v1",
                    "score": round(best_signal["score"], 6),
                    "tick_dev": round(best_signal["tick_dev"], 6),
                    "candle_dev": round(best_signal["candle_dev"], 6),
                    "trend_hr": round(best_signal["trend_hr"], 6),
                    "obi": round(best_signal["obi"], 4),
                    "spread_bps": round(best_signal["spread_bps"], 2),
                },
            )
            self.set_position(state.bot_id, symbol, float(price), "long")
        self.manage_vega_positions(state)

    def manage_vega_positions(self, state: BotState) -> None:
        now = state.timestamp
        for symbol, position in list(self.bot_positions.get(state.bot_id, {}).items()):
            if position.get("side") != "long":
                continue
            held_qty = self.holdings_qty(state.balances, symbol)
            if held_qty <= ZERO:
                self.clear_position(state.bot_id, symbol)
                continue
            price = state.marks[symbol]
            entry_price = position["entry_price"]
            pnl = (float(price) - entry_price) / entry_price
            age = now - position["entry_time"]
            if pnl >= 0.0025:
                sell_qty = held_qty * Decimal("0.65")
                self.place_order(
                    state.bot_id,
                    symbol,
                    "SELL",
                    sell_qty,
                    {
                        "strategy": "vega_pulse_microstructure_v1",
                        "exit_reason": "take_profit",
                        "pnl_pct": round(pnl, 5),
                    },
                )
                if sell_qty >= held_qty:
                    self.clear_position(state.bot_id, symbol)
                continue
            if pnl <= -0.005 or (age > 300 and pnl < 0):
                self.place_order(
                    state.bot_id,
                    symbol,
                    "SELL",
                    held_qty,
                    {
                        "strategy": "vega_pulse_microstructure_v1",
                        "exit_reason": "risk_guard",
                        "pnl_pct": round(pnl, 5),
                    },
                )
                self.clear_position(state.bot_id, symbol)

    def phantom_lattice_logic(self, state: BotState) -> None:
        now = state.timestamp
        btc_hist = state.history["BTCUSDT"]
        usdt = self.usdt_balance(state.balances)
        candidates: list[dict[str, Any]] = []
        for symbol in ["ETHUSDT", "SOLUSDT"]:
            metrics = self.ratio_zscore(symbol, lookback=120)
            if not metrics:
                continue
            z_score, current_ratio, mean_ratio = metrics
            if abs(z_score) < 1.6:
                continue
            candidates.append(
                {
                    "symbol": symbol,
                    "z": z_score,
                    "current_ratio": current_ratio,
                    "mean_ratio": mean_ratio,
                }
            )
        if not candidates:
            return
        candidates.sort(key=lambda c: abs(c["z"]), reverse=True)
        for candidate in candidates:
            symbol = candidate["symbol"]
            price = state.marks[symbol]
            held_qty = self.holdings_qty(state.balances, symbol)
            direction = "BUY" if candidate["z"] < 0 else "SELL"
            obi = self.get_order_book_imbalance(symbol, depth=10)
            if obi is None:
                continue
            if direction == "BUY" and not (obi > 0.08):
                continue
            if direction == "SELL" and held_qty <= ZERO:
                continue
            strong = abs(candidate["z"]) >= 2.5 and abs(obi) >= 0.18
            if direction == "BUY" and usdt > Decimal("60"):
                alloc_pct = Decimal("0.28" if strong else "0.18")
                qty = (usdt * alloc_pct) / price
                self.place_order(
                    state.bot_id,
                    symbol,
                    "BUY",
                    qty,
                    {
                        "strategy": "phantom_lattice_ratio_arb_v1",
                        "z_score": round(candidate["z"], 4),
                        "current_ratio": round(candidate["current_ratio"], 8),
                        "mean_ratio": round(candidate["mean_ratio"], 8),
                        "obi": round(obi, 4),
                        "strong": strong,
                    },
                )
                self.set_position(state.bot_id, symbol, float(price), "long")
                self.mark_trade(state.bot_id, symbol, now)
                break
            if direction == "SELL" and held_qty > ZERO:
                sell_fraction = Decimal("0.70" if strong else "0.55")
                self.place_order(
                    state.bot_id,
                    symbol,
                    "SELL",
                    held_qty * sell_fraction,
                    {
                        "strategy": "phantom_lattice_ratio_arb_v1",
                        "z_score": round(candidate["z"], 4),
                        "current_ratio": round(candidate["current_ratio"], 8),
                        "mean_ratio": round(candidate["mean_ratio"], 8),
                        "obi": round(obi, 4),
                        "strong": strong,
                    },
                )
                if sell_fraction >= 1:
                    self.clear_position(state.bot_id, symbol)
                self.mark_trade(state.bot_id, symbol, now)
                break
        self.phantom_take_profit(state)

    def phantom_take_profit(self, state: BotState) -> None:
        for symbol in ["ETHUSDT", "SOLUSDT"]:
            held_qty = self.holdings_qty(state.balances, symbol)
            if held_qty <= ZERO:
                continue
            metrics = self.ratio_zscore(symbol, lookback=120)
            if not metrics:
                continue
            z_score, _, _ = metrics
            if z_score > 0.3:
                obi = self.get_order_book_imbalance(symbol, depth=10)
                if obi is not None and obi < -0.05:
                    self.place_order(
                        state.bot_id,
                        symbol,
                        "SELL",
                        held_qty * Decimal("0.60"),
                        {
                            "strategy": "phantom_lattice_ratio_arb_v1",
                            "z_score": round(z_score, 4),
                            "exit_reason": "ratio_reverted",
                        },
                    )

    # ── runtime orchestration ────────────────────────────────────────────
    def run_bots(self) -> None:
        marks = self.current_marks()
        history = {symbol: list(self.history[symbol]) for symbol in self.symbols}
        timestamp = time.time()
        bot_ids = [
            "solstice_drift",
            "obsidian_flux",
            "vega_pulse",
            "phantom_lattice",
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
            if bot_id == "solstice_drift":
                self.solstice_drift_logic(state)
            elif bot_id == "obsidian_flux":
                self.obsidian_flux_logic(state)
            elif bot_id == "vega_pulse":
                self.vega_pulse_logic(state)
            elif bot_id == "phantom_lattice":
                self.phantom_lattice_logic(state)

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
        consecutive_failures = 0
        while True:
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
            result = self.publish_marks(marks)
            self.run_bots()
            self.log(
                "published marks "
                + json.dumps(result["marks"])
                + (" source=coinbase" if self.source == "coinbase" else " synthetic")
            )
            time.sleep(self.loop_seconds)


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
