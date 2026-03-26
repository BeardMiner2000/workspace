#!/usr/bin/env python3
"""
Season 4 — Holding Bot Executor
Bots BUY and HOLD positions, looking for 10-50% gains before selling
"""

import random
import time
from datetime import datetime, timedelta
from decimal import Decimal
from collections import defaultdict

import psycopg2
import requests
from psycopg2.extras import RealDictCursor

SEASON_ID = 'season-004'
TRADE_ENGINE_URL = 'http://localhost:8088'
FEES_PCT = Decimal('0.00975')
MIN_TRADE_USDT = Decimal('50')

# Bot configs with holding targets
BOTS = {
    'yolo_ape_9000': {
        'buy_freq': 'low',
        'buy_risk': 0.25,
        'sell_target': Decimal('0.40'),  # Sell at +40%
        'stop_loss': Decimal('-0.20'),   # Exit at -20%
        'name': '💥 YOLO Ape 9000',
        'min_position': Decimal('500'),
    },
    'chaos_degen': {
        'buy_freq': 'medium',
        'buy_risk': 0.20,
        'sell_target': Decimal('0.30'),
        'stop_loss': Decimal('-0.15'),
        'name': '⚡ Chaos Degen',
        'min_position': Decimal('300'),
    },
    'grid_scalper': {
        'buy_freq': 'very_high',
        'buy_risk': 0.05,
        'sell_target': Decimal('0.10'),  # Small gains
        'stop_loss': Decimal('-0.05'),
        'name': '📊 Grid Scalper',
        'min_position': Decimal('100'),
    },
    'mercury_vanta': {
        'buy_freq': 'high',
        'buy_risk': 0.08,
        'sell_target': Decimal('0.15'),
        'stop_loss': Decimal('-0.08'),
        'name': '💎 Mercury Vanta',
        'min_position': Decimal('150'),
    },
    'pair_trader': {
        'buy_freq': 'medium',
        'buy_risk': 0.12,
        'sell_target': Decimal('0.25'),
        'stop_loss': Decimal('-0.12'),
        'name': '🔄 Pair Trader',
        'min_position': Decimal('250'),
    },
    'obsidian_flux': {
        'buy_freq': 'low',
        'buy_risk': 0.10,
        'sell_target': Decimal('0.35'),
        'stop_loss': Decimal('-0.15'),
        'name': '👻 Obsidian Flux',
        'min_position': Decimal('200'),
    },
    'aurora_quanta': {
        'buy_freq': 'low',
        'buy_risk': 0.15,
        'sell_target': Decimal('0.50'),  # Hold for big wins
        'stop_loss': Decimal('-0.20'),
        'name': '🌍 Aurora Quanta',
        'min_position': Decimal('300'),
    },
    'pump_surfer': {
        'buy_freq': 'high',
        'buy_risk': 0.18,
        'sell_target': Decimal('0.35'),
        'stop_loss': Decimal('-0.15'),
        'name': '🌊 Pump Surfer',
        'min_position': Decimal('250'),
    },
    'stormchaser_delta': {
        'buy_freq': 'medium',
        'buy_risk': 0.15,
        'sell_target': Decimal('0.40'),
        'stop_loss': Decimal('-0.15'),
        'name': '⚡ StormChaser Delta',
        'min_position': Decimal('300'),
    },
    'phantom_lattice': {
        'buy_freq': 'low',
        'buy_risk': 0.08,
        'sell_target': Decimal('0.20'),
        'stop_loss': Decimal('-0.10'),
        'name': '🪟 Phantom Lattice',
        'min_position': Decimal('200'),
    },
    'solstice_drift': {
        'buy_freq': 'medium',
        'buy_risk': 0.10,
        'sell_target': Decimal('0.25'),
        'stop_loss': Decimal('-0.12'),
        'name': '🌙 Solstice Drift',
        'min_position': Decimal('200'),
    },
    'vega_pulse': {
        'buy_freq': 'low',
        'buy_risk': 0.12,
        'sell_target': Decimal('0.30'),
        'stop_loss': Decimal('-0.15'),
        'name': '🌀 Vega Pulse',
        'min_position': Decimal('250'),
    },
    'chaos_prophet': {
        'buy_freq': 'medium',
        'buy_risk': 0.12,
        'sell_target': Decimal('0.35'),
        'stop_loss': Decimal('-0.15'),
        'name': '🌪️ Chaos Prophet',
        'min_position': Decimal('200'),
    },
    'degen_ape_9000': {
        'buy_freq': 'high',
        'buy_risk': 0.20,
        'sell_target': Decimal('0.45'),
        'stop_loss': Decimal('-0.20'),
        'name': '💥 Degen Ape 9000',
        'min_position': Decimal('300'),
    },
    'loser_reversal_hunter': {
        'buy_freq': 'medium',
        'buy_risk': 0.15,
        'sell_target': Decimal('0.50'),  # Reversals hold long
        'stop_loss': Decimal('-0.25'),
        'name': '🚀 Loser Reversal Hunter',
        'min_position': Decimal('300'),
    },
    'gainer_momentum_catcher': {
        'buy_freq': 'medium',
        'buy_risk': 0.15,
        'sell_target': Decimal('0.40'),
        'stop_loss': Decimal('-0.15'),
        'name': '📈 Gainer Momentum Catcher',
        'min_position': Decimal('300'),
    },
    'bankruptcy_specialist': {
        'buy_freq': 'low',
        'buy_risk': 0.10,
        'sell_target': Decimal('1.00'),  # Crash recoveries: 100% target
        'stop_loss': Decimal('-0.50'),   # Can lose 50% waiting for bounce
        'name': '💣 Bankruptcy Specialist',
        'min_position': Decimal('500'),
    },
}

# Track open positions: {bot_id: {'symbol': str, 'qty': Decimal, 'entry_price': Decimal, 'buy_time': datetime}}
POSITIONS = defaultdict(dict)

def get_db():
    return psycopg2.connect(
        host='127.0.0.1',
        port=5432,
        user='paperbot',
        password='paperbot',
        database='paperbot',
        cursor_factory=RealDictCursor
    )

def get_balance(bot_id):
    try:
        with get_db() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT DISTINCT ON (bot_id) free
                    FROM bot_balances
                    WHERE season_id = %s AND bot_id = %s AND asset = 'USDT'
                    ORDER BY bot_id, ts DESC
                """, (SEASON_ID, bot_id))
                row = cur.fetchone()
                return Decimal(str(row['free'])) if row else Decimal('0')
    except:
        return Decimal('0')

def get_symbols():
    try:
        with get_db() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT DISTINCT ON (symbol) symbol, mark_price
                    FROM market_marks
                    WHERE season_id = %s AND mark_price > 0
                    ORDER BY symbol, ts DESC
                    LIMIT 50
                """, (SEASON_ID,))
                symbols = [dict(row) for row in cur.fetchall()]
                return [s for s in symbols if s['mark_price'] < Decimal('10000')]
    except:
        return []

def calculate_position_size(balance, risk, min_position, price):
    if balance < Decimal('50'):
        return Decimal('0')
    
    raw_position_usdt = balance * Decimal(str(risk))
    position_usdt = max(raw_position_usdt, min_position)
    
    if position_usdt > balance:
        position_usdt = balance * Decimal('0.85')
    
    fee_cost = position_usdt * FEES_PCT
    if (position_usdt - fee_cost) < MIN_TRADE_USDT:
        return Decimal('0')
    
    if price <= 0:
        return Decimal('0')
    
    qty = position_usdt / Decimal(str(price))
    
    min_qty = Decimal('0.0001')
    if price > Decimal('1000'):
        min_qty = Decimal('0.001')
    elif price > Decimal('100'):
        min_qty = Decimal('0.01')
    
    if qty < min_qty:
        return Decimal('0')
    
    return qty

def submit_order(bot_id, symbol, qty, side):
    try:
        payload = {
            'season_id': SEASON_ID,
            'bot_id': bot_id,
            'symbol': symbol,
            'side': side,
            'order_type': 'market',
            'quantity': float(qty),
            'rationale': {'action': 'buy' if side == 'BUY' else 'sell_for_profit'},
        }
        r = requests.post(f'{TRADE_ENGINE_URL}/orders', json=payload, timeout=3)
        return r.status_code == 200
    except:
        return False

def buy(bot_id, config, symbols):
    """Place a BUY order"""
    if bot_id in POSITIONS and POSITIONS[bot_id]:
        return False  # Already holding
    
    balance = get_balance(bot_id)
    if balance < Decimal('50'):
        return False
    
    if not symbols:
        return False
    
    symbol_data = random.choice(symbols)
    symbol = symbol_data['symbol']
    price = Decimal(str(symbol_data['mark_price']))
    
    if price <= 0:
        return False
    
    qty = calculate_position_size(balance, config['buy_risk'], config['min_position'], price)
    if qty <= Decimal('0'):
        return False
    
    if submit_order(bot_id, symbol, qty, 'BUY'):
        POSITIONS[bot_id] = {
            'symbol': symbol,
            'qty': qty,
            'entry_price': price,
            'buy_time': datetime.utcnow(),
            'buy_price_usdt': qty * price,
        }
        return True
    
    return False

def sell(bot_id, config, symbols, reason='profit'):
    """Close position with SELL order"""
    if bot_id not in POSITIONS or not POSITIONS[bot_id]:
        return False
    
    pos = POSITIONS[bot_id]
    symbol = pos['symbol']
    qty = pos['qty']
    
    # Get current price
    current_price = next((s['mark_price'] for s in symbols if s['symbol'] == symbol), None)
    if not current_price:
        return False
    
    current_price = Decimal(str(current_price))
    
    if submit_order(bot_id, symbol, qty, 'SELL'):
        pnl_pct = (current_price - pos['entry_price']) / pos['entry_price']
        hold_time = (datetime.utcnow() - pos['buy_time']).total_seconds() / 60  # minutes
        del POSITIONS[bot_id]
        return True
    
    return False

def should_buy(freq, cycle):
    if freq == 'very_high':
        return cycle % 1 == 0
    elif freq == 'high':
        return cycle % 3 == 0
    elif freq == 'medium':
        return cycle % 5 == 0
    elif freq == 'low':
        return cycle % 15 == 0
    return False

def should_sell_check(bot_id, config, current_price):
    """Check if position should be closed"""
    if bot_id not in POSITIONS or not POSITIONS[bot_id]:
        return None
    
    pos = POSITIONS[bot_id]
    current_price_dec = Decimal(str(current_price))
    entry_price = pos['entry_price']
    
    # Calculate gain/loss %
    pnl_pct = (current_price_dec - entry_price) / entry_price
    
    sell_target = Decimal(str(config['sell_target']))
    stop_loss = Decimal(str(config['stop_loss']))
    
    # Take profit
    if pnl_pct >= sell_target:
        return 'profit'
    
    # Stop loss
    if pnl_pct <= stop_loss:
        return 'stop_loss'
    
    return None

def main():
    print("=" * 100)
    print("🏆 SEASON 4 — HOLDING BOT EXECUTOR")
    print(f"   Start: {datetime.utcnow().isoformat()}")
    print(f"   Strategy: BUY & HOLD for 10-100% gains")
    print(f"   Bots: {len(BOTS)}")
    print(f"   Duration: 72 hours")
    print("=" * 100)
    
    start = datetime.utcnow()
    end = start + timedelta(hours=72)
    cycle = 0
    stats = {bot_id: {'buys': 0, 'sells': 0} for bot_id in BOTS.keys()}
    
    while datetime.utcnow() < end:
        cycle += 1
        elapsed = (datetime.utcnow() - start).total_seconds() / 3600
        
        symbols = get_symbols()
        if not symbols:
            time.sleep(3)
            continue
        
        # BUY phase
        for bot_id, config in BOTS.items():
            if should_buy(config['buy_freq'], cycle):
                if buy(bot_id, config, symbols):
                    stats[bot_id]['buys'] += 1
        
        # SELL phase (check all positions)
        for bot_id, config in BOTS.items():
            if bot_id in POSITIONS and POSITIONS[bot_id]:
                symbol = POSITIONS[bot_id]['symbol']
                current_price = next((s['mark_price'] for s in symbols if s['symbol'] == symbol), None)
                
                if current_price:
                    sell_signal = should_sell_check(bot_id, config, current_price)
                    if sell_signal:
                        if sell(bot_id, config, symbols, sell_signal):
                            stats[bot_id]['sells'] += 1
        
        # Log progress
        if cycle % 60 == 0:
            holdings = len([b for b in BOTS if b in POSITIONS and POSITIONS[b]])
            total_buys = sum(s['buys'] for s in stats.values())
            total_sells = sum(s['sells'] for s in stats.values())
            print(f"[{elapsed:6.2f}h] Cycle {cycle:6d} — " +
                  f"Holdings: {holdings}/12 | Buys: {total_buys} | Sells: {total_sells}")
        
        time.sleep(3)
    
    print("\n" + "=" * 100)
    print("🏁 CHAMPIONSHIP COMPLETE")
    print("\nFinal Activity:")
    for bot_id in sorted(stats.keys(), key=lambda x: stats[x]['buys'], reverse=True):
        buys = stats[bot_id]['buys']
        sells = stats[bot_id]['sells']
        if buys > 0 or sells > 0:
            print(f"  {BOTS[bot_id]['name']:40s} → {buys:3d} buys, {sells:3d} sells")
    print("=" * 100)

if __name__ == '__main__':
    main()
