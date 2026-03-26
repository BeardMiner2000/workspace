#!/usr/bin/env python3
"""
Season 4 Bot Executor - Runs on host
3-day competition: All 12 bots trading simultaneously
"""

import random
import time
from datetime import datetime, timedelta
from decimal import Decimal

import psycopg2
import requests
from psycopg2.extras import RealDictCursor

# Config
SEASON_ID = 'season-004'
TRADE_ENGINE_URL = 'http://localhost:8088'
DURATION_HOURS = 72
REFRESH_INTERVAL = 3  # seconds

BOTS = [
    'loser_reversal_hunter',
    'gainer_momentum_catcher',
    'aurora_quanta',
    'chaos_prophet',
    'degen_ape_9000',
    'mercury_vanta',
    'obsidian_flux',
    'phantom_lattice',
    'pump_surfer',
    'solstice_drift',
    'stormchaser_delta',
    'vega_pulse',
]

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
                    WHERE season_id = %s AND bot_id = %s AND asset = 'BTC'
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

def submit_order(bot_id, symbol, qty):
    try:
        payload = {
            'season_id': SEASON_ID,
            'bot_id': bot_id,
            'symbol': symbol,
            'side': 'buy',
            'order_type': 'market',
            'quantity': float(qty),
            'rationale': {'reason': 'competitive_trading'},
        }
        r = requests.post(f'{TRADE_ENGINE_URL}/orders', json=payload, timeout=3)
        return r.status_code == 200
    except:
        return False

def execute_bot(bot_id, cycle):
    """Execute a single bot trade."""
    balance = get_balance(bot_id)
    if balance < Decimal('0.0001'):
        return
    
    symbols = get_symbols()
    if not symbols:
        return
    
    symbol_data = random.choice(symbols)
    price = Decimal(str(symbol_data['mark_price']))
    
    if price <= 0:
        return
    
    # Risk 5-20% per trade
    risk = Decimal(str(random.uniform(0.05, 0.20)))
    qty = (balance * risk) / price
    
    if qty > 0:
        success = submit_order(bot_id, symbol_data['symbol'], qty)
        if success and cycle % 60 == 0:  # Log every 60th trade
            print(f"  [{bot_id:30}] {symbol_data['symbol']:10} +{qty:.8f}")

def main():
    print("=" * 90)
    print(f"🚀 SEASON 4 — 3-DAY BOT CHAMPIONSHIP")
    print(f"   Start: {datetime.utcnow().isoformat()}")
    print(f"   Duration: {DURATION_HOURS} hours")
    print(f"   Bots: {len(BOTS)}")
    print(f"   Winner: Highest BTC equity")
    print("=" * 90)
    
    start = datetime.utcnow()
    end = start + timedelta(hours=DURATION_HOURS)
    cycle = 0
    
    while datetime.utcnow() < end:
        cycle += 1
        elapsed = (datetime.utcnow() - start).total_seconds() / 3600
        
        # Execute all bots
        for bot_id in BOTS:
            execute_bot(bot_id, cycle)
        
        # Status
        if cycle % 300 == 0:  # Every ~15 minutes
            print(f"\n[{elapsed:6.2f}h] Cycle {cycle:6d} - All bots trading...")
        
        time.sleep(REFRESH_INTERVAL)
    
    print("\n" + "=" * 90)
    print(f"🏁 COMPETITION ENDED")
    print(f"   Duration: {(datetime.utcnow() - start).total_seconds() / 3600:.1f} hours")
    print("=" * 90)

if __name__ == '__main__':
    main()
