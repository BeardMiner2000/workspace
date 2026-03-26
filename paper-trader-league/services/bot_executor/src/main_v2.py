#!/usr/bin/env python3
"""
Season 4 Bot Executor V2 — Simplified & Direct
Executes all 12 bots with aggressive trading on Coinbase feeds
"""

import asyncio
import json
import os
import random
import sys
from datetime import datetime, timedelta
from decimal import Decimal
from pathlib import Path

import psycopg2
import requests
from psycopg2.extras import RealDictCursor

# ============================================================================
# CONFIG
# ============================================================================

SEASON_ID = 'season-004'
TRADE_ENGINE_URL = 'http://localhost:8088'
DB_HOST = 'localhost'
DB_PORT = '5432'
DB_USER = 'paperbot'
DB_PASS = 'paperbot'
DB_NAME = 'paperbot'

REFRESH_INTERVAL = 5  # seconds
MAX_DAILY_TRADES_PER_BOT = 10

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

# ============================================================================
# DATABASE
# ============================================================================

def get_db():
    """Get database connection."""
    return psycopg2.connect(
        host=DB_HOST,
        port=DB_PORT,
        user=DB_USER,
        password=DB_PASS,
        database=DB_NAME,
        cursor_factory=RealDictCursor
    )

def get_bot_balance(bot_id):
    """Get current balance for a bot."""
    try:
        with get_db() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT DISTINCT ON (bot_id) bot_id, free, locked
                    FROM bot_balances
                    WHERE season_id = %s AND bot_id = %s AND asset = 'BTC'
                    ORDER BY bot_id, ts DESC
                """, (SEASON_ID, bot_id))
                row = cur.fetchone()
                if row:
                    return {
                        'free': Decimal(str(row['free'])),
                        'locked': Decimal(str(row['locked']))
                    }
    except Exception as e:
        print(f"Error getting balance for {bot_id}: {e}")
    return {'free': Decimal('0'), 'locked': Decimal('0')}

def get_market_symbols():
    """Get list of available market symbols with prices."""
    try:
        with get_db() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT DISTINCT ON (symbol) symbol, mark_price, change_24h_pct
                    FROM market_marks
                    WHERE season_id = %s
                    ORDER BY symbol, ts DESC
                    LIMIT 100
                """, (SEASON_ID,))
                return [dict(row) for row in cur.fetchall()]
    except Exception as e:
        print(f"Error getting market symbols: {e}")
    return []

# ============================================================================
# BOT TRADING LOGIC
# ============================================================================

def submit_order(bot_id, symbol, side, quantity, rationale):
    """Submit order to trade engine."""
    try:
        payload = {
            'season_id': SEASON_ID,
            'bot_id': bot_id,
            'symbol': symbol,
            'side': side,
            'order_type': 'market',
            'quantity': float(quantity),
            'rationale': rationale,
            'metadata': {'timestamp': datetime.utcnow().isoformat()}
        }
        
        response = requests.post(
            f'{TRADE_ENGINE_URL}/orders',
            json=payload,
            timeout=5
        )
        
        if response.status_code == 200:
            print(f"[{bot_id:30}] {symbol:10} {side:4} {quantity:.6f} ✅")
            return True
        else:
            print(f"[{bot_id:30}] Order failed: {response.text[:100]}")
    except Exception as e:
        print(f"[{bot_id:30}] Error: {e}")
    
    return False

def execute_bot_trade(bot_id):
    """Execute a trade for a single bot."""
    balance = get_bot_balance(bot_id)
    if balance['free'] < Decimal('0.00001'):
        return  # No capital left
    
    symbols = get_market_symbols()
    if not symbols:
        return  # No market data
    
    # Select random symbol and buy
    symbol = random.choice(symbols)
    if not symbol['mark_price']:
        return
    
    price = Decimal(str(symbol['mark_price']))
    
    # Risk between 10-30% of portfolio
    risk_pct = Decimal(str(random.uniform(0.10, 0.30)))
    quantity = (balance['free'] * risk_pct) / price
    
    # All bots are trying to win, so be aggressive
    rationale = {
        'strategy': 'competitive_trading',
        'conviction': 'high',
        'risk_pct': float(risk_pct) * 100,
        'symbol_24h_change': float(symbol.get('change_24h_pct', 0))
    }
    
    submit_order(bot_id, symbol['symbol'], 'buy', quantity, rationale)

# ============================================================================
# MAIN LOOP
# ============================================================================

def main():
    """Main execution loop."""
    print("=" * 80)
    print(f"🚀 SEASON 4 — 3-DAY BOT CHAMPIONSHIP STARTED")
    print(f"   Time: {datetime.utcnow().isoformat()}")
    print(f"   Bots: {len(BOTS)}")
    print(f"   Duration: 72 hours")
    print(f"   Winner: Highest BTC equity at end")
    print("=" * 80)
    print()
    
    start_time = datetime.utcnow()
    end_time = start_time + timedelta(hours=72)
    cycle = 0
    
    while datetime.utcnow() < end_time:
        cycle += 1
        current_time = datetime.utcnow()
        elapsed_hours = (current_time - start_time).total_seconds() / 3600
        
        try:
            # Each bot executes a trade every ~5 seconds
            for bot_id in BOTS:
                execute_bot_trade(bot_id)
            
            # Status update every 60 cycles (~5 minutes)
            if cycle % 60 == 0:
                print(f"\n[{elapsed_hours:6.1f}h] Cycle {cycle} - All bots executing...")
            
            # Wait before next cycle
            asyncio.run(asyncio.sleep(REFRESH_INTERVAL))
            
        except KeyboardInterrupt:
            print("\n🛑 Competition stopped by user")
            break
        except Exception as e:
            print(f"Error in main loop: {e}")
            asyncio.run(asyncio.sleep(10))
    
    print("\n" + "=" * 80)
    print(f"🏁 COMPETITION ENDED")
    print(f"   Duration: {(datetime.utcnow() - start_time).total_seconds() / 3600:.1f} hours")
    print(f"   Cycles: {cycle}")
    print("=" * 80)

if __name__ == '__main__':
    main()
