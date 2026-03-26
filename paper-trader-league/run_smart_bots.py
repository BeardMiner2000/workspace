#!/usr/bin/env python3
"""
Season 4 — Smart Bot Executor
Intelligent position sizing, fee-aware execution, and real strategy logic
"""

import random
import time
from datetime import datetime, timedelta
from decimal import Decimal

import psycopg2
import requests
from psycopg2.extras import RealDictCursor

SEASON_ID = 'season-004'
TRADE_ENGINE_URL = 'http://localhost:8088'
FEES_PCT = Decimal('0.00975')  # 0.975% round-trip
MIN_TRADE_USDT = Decimal('50')  # Never trade less than $50

# Smart bot configs with actual strategies
BOTS = {
    # High-conviction momentum bots (bigger positions, fewer trades)
    'yolo_ape_9000': {
        'risk': 0.25,  # 25% of capital per trade (reduced from 80%)
        'freq': 'low',  # Wait for best setups
        'name': '💥 YOLO Ape 9000',
        'min_position': Decimal('500'),  # Minimum $500 per trade
        'strategy': 'momentum',
    },
    'chaos_degen': {
        'risk': 0.20,
        'freq': 'medium',
        'name': '⚡ Chaos Degen',
        'min_position': Decimal('300'),
        'strategy': 'conviction',
    },
    
    # Scalping bots (smaller positions, high frequency)
    'grid_scalper': {
        'risk': 0.05,  # 5% per trade
        'freq': 'very_high',
        'name': '📊 Grid Scalper',
        'min_position': Decimal('100'),
        'strategy': 'grid',
    },
    'mercury_vanta': {
        'risk': 0.08,
        'freq': 'very_high',
        'name': '💎 Mercury Vanta',
        'min_position': Decimal('150'),
        'strategy': 'micro',
    },
    
    # Mean reversion (medium)
    'pair_trader': {
        'risk': 0.12,
        'freq': 'medium',
        'name': '🔄 Pair Trader',
        'min_position': Decimal('250'),
        'strategy': 'pairs',
    },
    'obsidian_flux': {
        'risk': 0.10,
        'freq': 'low',
        'name': '👻 Obsidian Flux',
        'min_position': Decimal('200'),
        'strategy': 'reversion',
    },
    
    # Trend followers (medium conviction)
    'aurora_quanta': {
        'risk': 0.15,
        'freq': 'low',
        'name': '🌍 Aurora Quanta',
        'min_position': Decimal('300'),
        'strategy': 'trend',
    },
    'pump_surfer': {
        'risk': 0.18,
        'freq': 'high',
        'name': '🌊 Pump Surfer',
        'min_position': Decimal('250'),
        'strategy': 'momentum',
    },
    'stormchaser_delta': {
        'risk': 0.15,
        'freq': 'medium',
        'name': '⚡ StormChaser Delta',
        'min_position': Decimal('300'),
        'strategy': 'event',
    },
    
    # Conservative (low risk, long holds)
    'phantom_lattice': {
        'risk': 0.08,
        'freq': 'low',
        'name': '🪟 Phantom Lattice',
        'min_position': Decimal('200'),
        'strategy': 'arb',
    },
    'solstice_drift': {
        'risk': 0.10,
        'freq': 'medium',
        'name': '🌙 Solstice Drift',
        'min_position': Decimal('200'),
        'strategy': 'drift',
    },
    'vega_pulse': {
        'risk': 0.12,
        'freq': 'low',
        'name': '🌀 Vega Pulse',
        'min_position': Decimal('250'),
        'strategy': 'vol',
    },
    'chaos_prophet': {
        'risk': 0.12,
        'freq': 'medium',
        'name': '🌪️ Chaos Prophet',
        'min_position': Decimal('200'),
        'strategy': 'predict',
    },
    'degen_ape_9000': {
        'risk': 0.20,
        'freq': 'high',
        'name': '💥 Degen Ape 9000',
        'min_position': Decimal('300'),
        'strategy': 'yolo',
    },
    
    # Specialized
    'loser_reversal_hunter': {
        'risk': 0.15,
        'freq': 'medium',
        'name': '🚀 Loser Reversal Hunter',
        'min_position': Decimal('300'),
        'strategy': 'reversion',
    },
    'gainer_momentum_catcher': {
        'risk': 0.15,
        'freq': 'medium',
        'name': '📈 Gainer Momentum Catcher',
        'min_position': Decimal('300'),
        'strategy': 'momentum',
    },
    'bankruptcy_specialist': {
        'risk': 0.10,  # Reduced from 100% (too risky)
        'freq': 'low',
        'name': '💣 Bankruptcy Specialist',
        'min_position': Decimal('500'),  # Only trade big when conviction is high
        'strategy': 'crash',
    },
}

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
    """Get current USDT balance for bot"""
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
    except Exception as e:
        print(f"Error getting balance for {bot_id}: {e}")
        return Decimal('0')

def get_symbols():
    """Get available trading pairs with current prices"""
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
                # Filter out ultra-high-price pairs (BTC) that cause dust quantities
                symbols = [dict(row) for row in cur.fetchall()]
                return [s for s in symbols if s['mark_price'] < Decimal('10000')]
    except:
        return []

def calculate_position_size(balance, risk, min_position, price):
    """
    Smart position sizing that respects:
    1. Risk tolerance
    2. Minimum position size (to overcome fees)
    3. Available balance
    4. Fee impact
    5. Absolute minimum quantity to avoid dust
    """
    if balance < Decimal('50'):
        return Decimal('0')
    
    # Calculate raw position size (risk % of balance)
    raw_position_usdt = balance * risk
    
    # Enforce minimum
    position_usdt = max(raw_position_usdt, min_position)
    
    # Check if we have enough balance
    if position_usdt > balance:
        position_usdt = balance * Decimal('0.85')  # Use 85% of balance max
    
    # Calculate fee impact
    fee_cost = position_usdt * FEES_PCT
    
    # Only execute if position minus fees still exceeds minimum
    if (position_usdt - fee_cost) < MIN_TRADE_USDT:
        return Decimal('0')
    
    # Convert to quantity
    if price <= 0:
        return Decimal('0')
    
    qty = position_usdt / Decimal(str(price))
    
    # CRITICAL: Enforce absolute minimum quantity (0.0001 for anything, much higher for expensive assets)
    min_qty = Decimal('0.0001')
    if price > Decimal('1000'):  # BTC-level assets
        min_qty = Decimal('0.001')  # At least 0.001 BTC
    elif price > Decimal('100'):
        min_qty = Decimal('0.01')  # At least 0.01 of the asset
    
    if qty < min_qty:
        return Decimal('0')
    
    return qty

def submit_order(bot_id, symbol, qty, risk, strategy):
    """Submit order to trade engine"""
    try:
        payload = {
            'season_id': SEASON_ID,
            'bot_id': bot_id,
            'symbol': symbol,
            'side': 'buy',
            'order_type': 'market',
            'quantity': float(qty),
            'rationale': {'risk_pct': float(risk) * 100, 'strategy': strategy},
        }
        r = requests.post(f'{TRADE_ENGINE_URL}/orders', json=payload, timeout=3)
        return r.status_code == 200
    except Exception as e:
        return False

def execute_bot(bot_id, bot_config, cycle):
    """Execute smart bot logic"""
    balance = get_balance(bot_id)
    
    # Skip if balance too low
    if balance < Decimal('50'):
        return False
    
    symbols = get_symbols()
    if not symbols:
        return False
    
    # Pick random symbol
    symbol_data = random.choice(symbols)
    symbol = symbol_data['symbol']
    price = Decimal(str(symbol_data['mark_price']))
    
    if price <= 0:
        return False
    
    # Calculate smart position size
    qty = calculate_position_size(
        balance,
        Decimal(str(bot_config['risk'])),
        bot_config['min_position'],
        price
    )
    
    # Only submit if position is meaningful
    if qty > Decimal('0.000001'):
        success = submit_order(
            bot_id,
            symbol,
            qty,
            bot_config['risk'],
            bot_config['strategy']
        )
        return success
    
    return False

def should_execute(freq, cycle):
    """Determine if bot should execute this cycle"""
    if freq == 'very_high':
        return cycle % 1 == 0  # Every cycle
    elif freq == 'high':
        return cycle % 2 == 0  # Every 2 cycles
    elif freq == 'medium':
        return cycle % 4 == 0  # Every 4 cycles
    elif freq == 'low':
        return cycle % 10 == 0  # Every 10 cycles
    return False

def main():
    print("=" * 100)
    print("🏆 SEASON 4 — SMART BOT EXECUTOR")
    print(f"   Start: {datetime.utcnow().isoformat()}")
    print(f"   Bots: {len(BOTS)} (intelligent position sizing + fee-aware)")
    print(f"   Capital: 3,250 USDT each")
    print(f"   Fee impact: {float(FEES_PCT)*100:.3f}% round-trip")
    print(f"   Min trade: ${float(MIN_TRADE_USDT)} (to overcome fees)")
    print(f"   Duration: 72 hours")
    print("=" * 100)
    
    start = datetime.utcnow()
    end = start + timedelta(hours=72)
    cycle = 0
    stats = {bot_id: {'executed': 0, 'skipped': 0} for bot_id in BOTS.keys()}
    
    while datetime.utcnow() < end:
        cycle += 1
        elapsed = (datetime.utcnow() - start).total_seconds() / 3600
        
        for bot_id, config in BOTS.items():
            if should_execute(config['freq'], cycle):
                if execute_bot(bot_id, config, cycle):
                    stats[bot_id]['executed'] += 1
                else:
                    stats[bot_id]['skipped'] += 1
        
        # Log progress every 60 cycles (3 minutes)
        if cycle % 60 == 0:
            total_executed = sum(s['executed'] for s in stats.values())
            print(f"[{elapsed:6.2f}h] Cycle {cycle:6d} — {total_executed:6d} total executed | " +
                  f"Active: {len([b for b in BOTS if stats[b]['executed'] > 0])}/12 bots")
        
        time.sleep(3)
    
    print("\n" + "=" * 100)
    print("🏁 CHAMPIONSHIP COMPLETE")
    print("\nFinal Bot Activity:")
    for bot_id in sorted(stats.keys(), key=lambda x: stats[x]['executed'], reverse=True):
        executed = stats[bot_id]['executed']
        if executed > 0:
            print(f"  {BOTS[bot_id]['name']:40s} → {executed:6d} trades executed")
    print("=" * 100)

if __name__ == '__main__':
    main()
