#!/usr/bin/env python3
"""
Season 4 — All 12 Bots Trading in One Place
Fee-aware execution with varied risk profiles
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

# All 12 bots with varied strategies
BOTS = {
    # New V2 fee-aware bots
    'yolo_ape_9000': {'risk': 0.80, 'freq': 'high', 'name': '💥 YOLO Ape 9000'},
    'pair_trader': {'risk': 0.12, 'freq': 'medium', 'name': '🔄 Pair Trader'},
    'grid_scalper': {'risk': 0.03, 'freq': 'very_high', 'name': '📊 Grid Scalper'},
    'bankruptcy_specialist': {'risk': 1.00, 'freq': 'low', 'name': '💣 Bankruptcy Specialist'},
    'chaos_degen': {'risk': 0.75, 'freq': 'medium', 'name': '⚡ Chaos Degen'},
    
    # Legacy bots from S1-S3
    'aurora_quanta': {'risk': 0.15, 'freq': 'low', 'name': '🌍 Aurora Quanta'},
    'chaos_prophet': {'risk': 0.20, 'freq': 'medium', 'name': '🌪️ Chaos Prophet'},
    'degen_ape_9000': {'risk': 0.40, 'freq': 'high', 'name': '💥 Degen Ape 9000'},
    'mercury_vanta': {'risk': 0.05, 'freq': 'very_high', 'name': '💎 Mercury Vanta'},
    'obsidian_flux': {'risk': 0.20, 'freq': 'low', 'name': '👻 Obsidian Flux'},
    'phantom_lattice': {'risk': 0.15, 'freq': 'medium', 'name': '🪟 Phantom Lattice'},
    'pump_surfer': {'risk': 0.30, 'freq': 'high', 'name': '🌊 Pump Surfer'},
    'solstice_drift': {'risk': 0.18, 'freq': 'medium', 'name': '🌙 Solstice Drift'},
    'stormchaser_delta': {'risk': 0.25, 'freq': 'medium', 'name': '⚡ StormChaser Delta'},
    'vega_pulse': {'risk': 0.22, 'freq': 'low', 'name': '🌀 Vega Pulse'},
    
    # New S4 bots
    'loser_reversal_hunter': {'risk': 0.50, 'freq': 'high', 'name': '🚀 Loser Reversal Hunter'},
    'gainer_momentum_catcher': {'risk': 0.50, 'freq': 'high', 'name': '📈 Gainer Momentum Catcher'},
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
                return [dict(row) for row in cur.fetchall()]
    except:
        return []

def submit_order(bot_id, symbol, qty, risk):
    try:
        payload = {
            'season_id': SEASON_ID,
            'bot_id': bot_id,
            'symbol': symbol,
            'side': 'buy',
            'order_type': 'market',
            'quantity': float(qty),
            'rationale': {'risk_pct': float(risk) * 100},
        }
        r = requests.post(f'{TRADE_ENGINE_URL}/orders', json=payload, timeout=3)
        return r.status_code == 200
    except:
        return False

def execute_bot(bot_id, bot_config, cycle):
    balance = get_balance(bot_id)
    if balance < Decimal('10'):
        return False
    
    symbols = get_symbols()
    if not symbols:
        return False
    
    symbol_data = random.choice(symbols)
    price = Decimal(str(symbol_data['mark_price']))
    if price <= 0:
        return False
    
    position_value = balance * Decimal(str(bot_config['risk']))
    qty = position_value / price
    
    if qty > 0:
        return submit_order(bot_id, symbol_data['symbol'], qty, bot_config['risk'])
    
    return False

def should_execute(freq, cycle):
    if freq == 'very_high':
        return True
    elif freq == 'high':
        return cycle % 2 == 0
    elif freq == 'medium':
        return cycle % 3 == 0
    elif freq == 'low':
        return cycle % 10 == 0
    return False

def main():
    print("=" * 90)
    print("🏆 SEASON 4 — 12-BOT CHAMPIONSHIP (CONSOLIDATED)")
    print(f"   Start: {datetime.utcnow().isoformat()}")
    print(f"   Bots: {len(BOTS)} (all trading in season-004)")
    print(f"   Capital: 3,250 USDT each (0.05 BTC equivalent)")
    print(f"   Total Pool: 39,000 USDT (0.6 BTC)")
    print(f"   Duration: 72 hours")
    print("=" * 90)
    
    start = datetime.utcnow()
    end = start + timedelta(hours=72)
    cycle = 0
    
    while datetime.utcnow() < end:
        cycle += 1
        elapsed = (datetime.utcnow() - start).total_seconds() / 3600
        
        for bot_id, config in BOTS.items():
            if should_execute(config['freq'], cycle):
                execute_bot(bot_id, config, cycle)
        
        if cycle % 60 == 0:
            print(f"[{elapsed:6.2f}h] Cycle {cycle:6d} — 12 bots executing...")
        
        time.sleep(3)
    
    print("\n" + "=" * 90)
    print("🏁 CHAMPIONSHIP COMPLETE")
    print("=" * 90)

if __name__ == '__main__':
    main()
