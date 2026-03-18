from __future__ import annotations

from collections import defaultdict, deque
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
import json
import math
import os
import random
import time
from typing import Any

import psycopg2
import requests
from psycopg2.extras import RealDictCursor

ZERO = Decimal('0')
SAT = Decimal('0.00000001')


@dataclass
class BotState:
    bot_id: str
    marks: dict[str, Decimal]
    history: dict[str, list[Decimal]]
    balances: dict[str, Decimal]
    tick: int
    event_score: float
    narrative_score: float


class LeagueRuntime:
    def __init__(self) -> None:
        self.season_id = os.getenv('DEFAULT_SEASON_ID', 'season-001')
        self.trade_engine_url = os.getenv('TRADE_ENGINE_URL', 'http://trade_engine:8088')
        self.loop_seconds = float(os.getenv('INGEST_LOOP_SECONDS', '5'))
        self.bootstrap = os.getenv('AUTO_BOOTSTRAP_SEASON', 'true').lower() in {'1', 'true', 'yes'}
        self.starting_btc = float(os.getenv('DEFAULT_STARTING_BTC', '0.05'))
        self.source = os.getenv('MARKET_DATA_SOURCE', 'synthetic')
        self.seed = int(os.getenv('SYNTHETIC_SEED', '42'))
        self.max_history = int(os.getenv('SYNTHETIC_HISTORY_SIZE', '180'))
        self.rand = random.Random(self.seed)
        self.tick = 0
        self.symbols = ['BTCUSDT', 'ETHUSDT', 'SOLUSDT', 'DOGEUSDT']
        self.state = {
            'BTCUSDT': {'price': 65000.0, 'drift': 0.0006, 'amp': 0.007},
            'ETHUSDT': {'price': 3450.0, 'drift': 0.0013, 'amp': 0.013},
            'SOLUSDT': {'price': 142.0, 'drift': 0.0022, 'amp': 0.024},
            'DOGEUSDT': {'price': 0.165, 'drift': 0.0035, 'amp': 0.04},
        }
        self.history = {symbol: deque(maxlen=self.max_history) for symbol in self.symbols}
        self.narrative_score = 0.0
        self.event_score = 0.0
        self.last_event_note = 'calm tape'

    def log(self, message: str) -> None:
        print(f"[data_ingest] {datetime.now(timezone.utc).isoformat()} {message}", flush=True)

    def get_dsn(self) -> str:
        host = os.getenv('POSTGRES_HOST', 'timescaledb')
        port = os.getenv('POSTGRES_PORT', '5432')
        user = os.getenv('POSTGRES_USER', 'paperbot')
        password = os.getenv('POSTGRES_PASSWORD', 'paperbot')
        database = os.getenv('POSTGRES_DB', 'paperbot')
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
                        cur.execute('SELECT 1')
                        cur.fetchone()
                requests.get(f'{self.trade_engine_url}/health', timeout=3).raise_for_status()
                return
            except Exception as exc:  # pragma: no cover - startup retry loop
                self.log(f'waiting for dependencies: {exc}')
                time.sleep(3)

    def maybe_bootstrap(self) -> None:
        if not self.bootstrap:
            return
        payload = {'season_id': self.season_id, 'starting_btc': self.starting_btc}
        response = requests.post(f'{self.trade_engine_url}/season/bootstrap', json=payload, timeout=10)
        response.raise_for_status()
        self.log(f'bootstrapped season {self.season_id}')

    def current_marks(self) -> dict[str, Decimal]:
        return {symbol: Decimal(str(meta['price'])) for symbol, meta in self.state.items()}

    def update_synthetic_market(self) -> dict[str, float]:
        self.tick += 1
        phase = self.tick
        self.narrative_score = 0.65 * math.sin(phase / 8) + 0.35 * math.sin(phase / 21)
        pulse = math.sin(phase / 5)
        event_raw = 0.55 * pulse + self.rand.uniform(-0.2, 0.2)
        if phase % 17 == 0:
            event_raw += self.rand.choice([-1.4, -0.9, 0.9, 1.6])
        self.event_score = max(-2.0, min(2.0, event_raw))

        for symbol, meta in self.state.items():
            base_noise = self.rand.uniform(-meta['amp'], meta['amp'])
            cyclical = math.sin((phase + len(symbol)) / 6) * meta['amp'] * 0.6
            trend = meta['drift']
            if symbol == 'BTCUSDT':
                shock = self.event_score * 0.0022 + self.narrative_score * 0.0012
            elif symbol == 'ETHUSDT':
                shock = self.narrative_score * 0.006 + self.event_score * 0.002
            elif symbol == 'SOLUSDT':
                shock = self.narrative_score * 0.008 + self.event_score * 0.0045
            else:
                shock = self.event_score * 0.009 + max(self.narrative_score, 0) * 0.0035

            ret = trend + base_noise + cyclical + shock
            if phase % 29 == 0 and symbol in {'SOLUSDT', 'DOGEUSDT'}:
                ret += self.rand.choice([-0.06, -0.03, 0.03, 0.07])
            meta['price'] = max(meta['price'] * (1 + ret), 0.0001)
            self.history[symbol].append(Decimal(str(meta['price'])))

        if self.event_score > 0.9:
            self.last_event_note = 'positive catalyst / breakout tape'
        elif self.event_score < -0.9:
            self.last_event_note = 'negative shock / liquidation tape'
        else:
            self.last_event_note = 'range-to-trend transition'

        return {symbol: round(meta['price'], 8) for symbol, meta in self.state.items()}

    def publish_marks(self, marks: dict[str, float]) -> dict[str, Any]:
        response = requests.post(
            f'{self.trade_engine_url}/marks',
            json={'season_id': self.season_id, 'marks': marks},
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
                return {row['asset']: Decimal(str(row['free'])) for row in cur.fetchall()}

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

    def symbol_history(self, symbol: str) -> list[Decimal]:
        return list(self.history[symbol])

    def holdings_qty(self, balances: dict[str, Decimal], symbol: str) -> Decimal:
        base, _ = split_symbol(symbol)
        return balances.get(base, ZERO)

    def usdt_balance(self, balances: dict[str, Decimal]) -> Decimal:
        return balances.get('USDT', ZERO)

    def place_order(self, bot_id: str, symbol: str, side: str, quantity: Decimal, rationale: dict[str, Any]) -> None:
        quantity = self.quant(quantity)
        if quantity <= ZERO:
            return
        payload = {
            'season_id': self.season_id,
            'bot_id': bot_id,
            'symbol': symbol,
            'side': side,
            'order_type': 'market',
            'quantity': float(quantity),
            'rationale': rationale,
            'metadata': {
                'runtime': 'synthetic_v1',
                'tick': self.tick,
                'event_note': self.last_event_note,
            },
        }
        response = requests.post(f'{self.trade_engine_url}/orders', json=payload, timeout=10)
        if response.ok:
            body = response.json()
            self.log(f"order {bot_id} {side} {symbol} qty={quantity} fill={body['fill_price']}")
            return
        self.log(f'order rejected for {bot_id}: {response.status_code} {response.text}')

    def aurora_logic(self, state: BotState) -> None:
        candidates = ['ETHUSDT', 'SOLUSDT']
        scores = []
        btc_mom = self.pct_change(state.history['BTCUSDT'], 6)
        for symbol in candidates:
            rel = self.pct_change(state.history[symbol], 6) - btc_mom
            long_mom = self.pct_change(state.history[symbol], 12)
            vol = self.stdev_returns(state.history[symbol], 12)
            conviction = rel * 1.8 + long_mom * 1.3 + state.narrative_score * 0.18 - vol * 1.2
            scores.append((conviction, symbol, rel, long_mom, vol))
        scores.sort(reverse=True)
        best = scores[0]
        conviction, symbol, rel, long_mom, vol = best
        price = state.marks[symbol]
        balances = state.balances
        held_qty = self.holdings_qty(balances, symbol)
        usdt = self.usdt_balance(balances)
        strong = conviction > 0.035 and state.narrative_score > -0.15
        weak = conviction < -0.01 or state.narrative_score < -0.55
        if strong and usdt > Decimal('150'):
            alloc = min(usdt * Decimal('0.42'), usdt)
            qty = alloc / price
            self.place_order(
                state.bot_id,
                symbol,
                'BUY',
                qty,
                {
                    'strategy': 'aurora_quanta_swing_v1',
                    'conviction': round(conviction, 6),
                    'relative_strength_vs_btc': round(rel, 6),
                    'long_momentum': round(long_mom, 6),
                    'volatility': round(vol, 6),
                    'narrative_score': round(state.narrative_score, 6),
                },
            )
        elif held_qty > ZERO and weak:
            self.place_order(
                state.bot_id,
                symbol,
                'SELL',
                held_qty * Decimal('0.55'),
                {
                    'strategy': 'aurora_quanta_swing_v1',
                    'conviction': round(conviction, 6),
                    'relative_strength_vs_btc': round(rel, 6),
                    'long_momentum': round(long_mom, 6),
                    'volatility': round(vol, 6),
                    'narrative_score': round(state.narrative_score, 6),
                    'exit_reason': 'thesis_invalidated',
                },
            )
        elif balances.get('BTC', ZERO) > Decimal('0.006') and conviction < -0.03 and usdt < Decimal('100'):
            self.place_order(
                state.bot_id,
                'BTCUSDT',
                'SELL',
                balances['BTC'] * Decimal('0.35'),
                {
                    'strategy': 'aurora_quanta_swing_v1',
                    'btc_momentum': round(btc_mom, 6),
                    'narrative_score': round(state.narrative_score, 6),
                    'rotation': 'raise_dry_powder',
                },
            )

    def storm_logic(self, state: BotState) -> None:
        candidates = ['SOLUSDT', 'DOGEUSDT', 'ETHUSDT']
        ranked = []
        for symbol in candidates:
            fast = self.pct_change(state.history[symbol], 2)
            burst = self.pct_change(state.history[symbol], 4)
            vol = self.stdev_returns(state.history[symbol], 8)
            breakout = fast * 2.4 + burst * 1.1 + state.event_score * 0.15 + vol * 0.8
            ranked.append((breakout, symbol, fast, burst, vol))
        ranked.sort(reverse=True)
        score, symbol, fast, burst, vol = ranked[0]
        balances = state.balances
        usdt = self.usdt_balance(balances)
        held_qty = self.holdings_qty(balances, symbol)
        price = state.marks[symbol]
        if score > 0.05 and usdt > Decimal('70'):
            aggress = Decimal('0.18') if state.event_score < 1.1 else Decimal('0.3')
            qty = (usdt * aggress) / price
            self.place_order(
                state.bot_id,
                symbol,
                'BUY',
                qty,
                {
                    'strategy': 'stormchaser_delta_breakout_v1',
                    'breakout_score': round(score, 6),
                    'fast_momentum': round(fast, 6),
                    'burst_momentum': round(burst, 6),
                    'event_score': round(state.event_score, 6),
                    'micro_volatility': round(vol, 6),
                },
            )
        elif held_qty > ZERO and (fast < -0.018 or state.event_score < -0.8):
            self.place_order(
                state.bot_id,
                symbol,
                'SELL',
                held_qty * Decimal('0.8'),
                {
                    'strategy': 'stormchaser_delta_breakout_v1',
                    'breakout_score': round(score, 6),
                    'fast_momentum': round(fast, 6),
                    'burst_momentum': round(burst, 6),
                    'event_score': round(state.event_score, 6),
                    'exit_reason': 'momentum_failure',
                },
            )

    def mercury_logic(self, state: BotState) -> None:
        candidates = ['ETHUSDT', 'SOLUSDT', 'DOGEUSDT']
        balances = state.balances
        usdt = self.usdt_balance(balances)
        ranked = []
        for symbol in candidates:
            series = state.history[symbol]
            if len(series) < 8:
                continue
            values = [float(x) for x in series[-6:]]
            mean = sum(values[:-1]) / len(values[:-1])
            last = values[-1]
            deviation = (last - mean) / mean if mean else 0.0
            bounce = self.pct_change(series, 1)
            short_reversion = self.pct_change(series, 2)
            vol = self.stdev_returns(series, 6)
            expectancy = (-deviation * 1.9) + (-bounce * 0.7) + (-short_reversion * 0.5) - (vol * 0.25)
            ranked.append((expectancy, symbol, deviation, bounce, short_reversion, vol))
        if not ranked:
            return
        ranked.sort(reverse=True)
        expectancy, symbol, deviation, bounce, short_reversion, vol = ranked[0]
        held_qty = self.holdings_qty(balances, symbol)
        price = state.marks[symbol]
        if (deviation < -0.0025 or bounce < -0.003) and expectancy > -0.002 and usdt > Decimal('45'):
            qty = (usdt * Decimal('0.12')) / price
            self.place_order(
                state.bot_id,
                symbol,
                'BUY',
                qty,
                {
                    'strategy': 'mercury_vanta_mean_reversion_v1',
                    'expectancy_score': round(expectancy, 6),
                    'deviation_from_mean': round(deviation, 6),
                    'bounce': round(bounce, 6),
                    'short_reversion': round(short_reversion, 6),
                    'micro_volatility': round(vol, 6),
                },
            )
        elif held_qty > ZERO and (deviation > 0.0035 or bounce < -0.0045 or expectancy < -0.012):
            self.place_order(
                state.bot_id,
                symbol,
                'SELL',
                held_qty * Decimal('0.65'),
                {
                    'strategy': 'mercury_vanta_mean_reversion_v1',
                    'expectancy_score': round(expectancy, 6),
                    'deviation_from_mean': round(deviation, 6),
                    'bounce': round(bounce, 6),
                    'short_reversion': round(short_reversion, 6),
                    'micro_volatility': round(vol, 6),
                    'exit_reason': 'edge_decay',
                },
            )

    def maybe_fund_trading_cash(self, state: BotState) -> bool:
        usdt = self.usdt_balance(state.balances)
        btc = state.balances.get('BTC', ZERO)
        if usdt >= Decimal('120') or btc <= Decimal('0.0025'):
            return False
        if state.bot_id == 'aurora_quanta':
            fraction = Decimal('0.28')
        elif state.bot_id == 'stormchaser_delta':
            fraction = Decimal('0.18')
        else:
            fraction = Decimal('0.14')
        self.place_order(
            state.bot_id,
            'BTCUSDT',
            'SELL',
            btc * fraction,
            {
                'strategy': 'runtime_cash_funding_v1',
                'event_score': round(state.event_score, 6),
                'narrative_score': round(state.narrative_score, 6),
                'note': 'seed_quote_inventory_for_alt_trading',
            },
        )
        return True

    def run_bots(self) -> None:
        marks = self.current_marks()
        history = {symbol: self.symbol_history(symbol) for symbol in self.symbols}
        bot_ids = ['aurora_quanta', 'stormchaser_delta', 'mercury_vanta']
        for bot_id in bot_ids:
            state = BotState(
                bot_id=bot_id,
                marks=marks,
                history=history,
                balances=self.get_balances(bot_id),
                tick=self.tick,
                event_score=self.event_score,
                narrative_score=self.narrative_score,
            )
            if self.maybe_fund_trading_cash(state):
                continue
            if bot_id == 'aurora_quanta':
                self.aurora_logic(state)
            elif bot_id == 'stormchaser_delta':
                self.storm_logic(state)
            else:
                self.mercury_logic(state)

    def run(self) -> None:
        self.log(f'starting runtime source={self.source} season={self.season_id} loop={self.loop_seconds}s')
        self.wait_for_dependencies()
        self.maybe_bootstrap()
        while True:
            marks = self.update_synthetic_market()
            result = self.publish_marks(marks)
            self.run_bots()
            self.log(
                'published marks '
                + json.dumps(result['marks'])
                + f' narrative={self.narrative_score:.3f} event={self.event_score:.3f}'
            )
            time.sleep(self.loop_seconds)


def split_symbol(symbol: str) -> tuple[str, str]:
    symbol = symbol.upper()
    for quote in ('USDT', 'BTC', 'USD'):
        if symbol.endswith(quote):
            return symbol[:-len(quote)], quote
    raise ValueError(f'Unsupported symbol: {symbol}')


def main() -> None:
    LeagueRuntime().run()


if __name__ == '__main__':
    main()
