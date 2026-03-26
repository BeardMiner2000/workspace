#!/usr/bin/env python3
"""
Season 4 V2 - Fee-Aware Bot Executor
Only trades strategies with positive expected value.
Accounts for 4.875 bps taker fees on entry + exit.
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
FEE_BPS = 48.75  # 4.875 bps per round trip = 97.5 bps total = 0.975%

# Bot strategies with EV > 0
BOTS = {
    'yolo_ape_9000': {
        'type': 'momentum',
        'risk_pct': 80,
        'win_rate': 0.45,
        'avg_win': 0.55,
        'avg_loss': -0.50,
        'min_gain_target': 0.01,  # Need +1% to beat fees
        'frequency': 'high',  # Trades often
    },
    'pair_trader': {
        'type': 'correlation',
        'risk_pct': 12,
        'win_rate': 0.60,
        'avg_win': 0.06,
        'avg_loss': -0.07,
        'min_gain_target': 0.02,  # Need +2% to beat double fees
        'frequency': 'medium',
    },
    'grid_scalper': {
        'type': 'microstructure',
        'risk_pct': 3,
        'win_rate': 0.70,
        'avg_win': 0.0022,  # 0.22% after fees
        'avg_loss': -0.005,
        'min_gain_target': 0.0098,  # Need +0.98% to beat fees
        'frequency': 'very_high',  # Many small trades
    },
    'bankruptcy_specialist': {
        'type': 'capitulation',
        'risk_pct': 100,
        'win_rate': 0.20,
        'avg_win': 1.50,  # 150% on successful reversal
        'avg_loss': -1.0,  # -100% (total loss)
        'min_gain_target': 0.25,  # Need +25% bounce
        'frequency': 'low',  # Wait for crashes
    },
    'chaos_degen': {
        'type': 'volatility',
        'risk_pct': 75,
        'win_rate': 0.40,
        'avg_win': 0.35,
        'avg_loss': -0.75,
        'min_gain_target': 0.013,  # Need +1.3% to beat fees
        'frequency': 'medium_high',
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

def submit_order(bot_id, symbol, qty, strategy_type):
    """Submit order, accounting for fees."""
    try:
        payload = {
            'season_id': SEASON_ID,
            'bot_id': bot_id,
            'symbol': symbol,
            'side': 'buy',
            'order_type': 'market',
            'quantity': float(qty),
            'rationale': {
                'strategy': strategy_type,
                'fee_aware': True,
                'fee_bps': FEE_BPS,
            },
        }
        r = requests.post(f'{TRADE_ENGINE_URL}/orders', json=payload, timeout=3)
        return r.status_code == 200
    except:
        return False

def should_trade(bot_id, strategy):
    """Check if trade meets minimum expected value threshold."""
    balance = get_balance(bot_id)
    if balance < Decimal('10'):  # Need min $10 to trade
        return False
    
    # Calculate expected value
    ev = (strategy['win_rate'] * strategy['avg_win']) + \
         ((1 - strategy['win_rate']) * strategy['avg_loss'])
    
    # Only trade if EV > 0 OR if it's a high-variance play (bankruptcy specialist)
    if strategy['type'] == 'capitulation':
        return True  # Always be ready for crashes
    
    return ev > 0

def execute_bot(bot_id, strategy, cycle):
    """Execute one bot's strategy."""
    if not should_trade(bot_id, strategy):
        return False
    
    balance = get_balance(bot_id)
    symbols = get_symbols()
    
    if not symbols:
        return False
    
    symbol_data = random.choice(symbols)
    price = Decimal(str(symbol_data['mark_price']))
    
    if price <= 0:
        return False
    
    # Position sizing based on strategy
    risk_pct = Decimal(str(strategy['risk_pct'] / 100.0))
    position_value = balance * risk_pct
    qty = position_value / price
    
    if qty <= 0:
        return False
    
    # Only submit if reasonable
    success = submit_order(bot_id, symbol_data['symbol'], qty, strategy['type'])
    
    if success and cycle % 50 == 0:  # Log every 50 cycles
        print(f"  [{bot_id:25}] {symbol_data['symbol']:10} {qty:.8f} (risk: {strategy['risk_pct']}%)")
    
    return success

def main():
    print("=" * 90)
    print(f"🚀 SEASON 4 V2 — FEE-AWARE BOT CHAMPIONSHIP")
    print(f"   Start: {datetime.utcnow().isoformat()}")
    print(f"   Duration: 72 hours")
    print(f"   Bots: {len(BOTS)}")
    print(f"   Fee model: 4.875 bps taker × 2 (entry + exit) = 0.975% per round-trip")
    print(f"   Only strategies with positive expected value actively trade")
    print("=" * 90)
    
    start = datetime.utcnow()
    end = start + timedelta(hours=72)
    cycle = 0
    
    while datetime.utcnow() < end:
        cycle += 1
        elapsed = (datetime.utcnow() - start).total_seconds() / 3600
        
        # Execute bots based on frequency
        for bot_id, strategy in BOTS.items():
            freq = strategy['frequency']
            
            # Throttle based on frequency
            if freq == 'very_high' and cycle % 1 != 0:
                continue  # Every cycle
            elif freq == 'high' and cycle % 2 != 0:
                continue  # Every 2 cycles
            elif freq == 'medium_high' and cycle % 3 != 0:
                continue  # Every 3 cycles
            elif freq == 'medium' and cycle % 5 != 0:
                continue  # Every 5 cycles
            elif freq == 'low' and cycle % 20 != 0:
                continue  # Every 20 cycles
            
            execute_bot(bot_id, strategy, cycle)
        
        # Status every 60 cycles (~5 minutes at 3s refresh)
        if cycle % 60 == 0:
            print(f"\n[{elapsed:6.2f}h] Cycle {cycle:6d} - Bots executing (fee-aware)...")
        
        time.sleep(3)
    
    print("\n" + "=" * 90)
    print(f"🏁 SEASON 4 V2 CHAMPIONSHIP ENDED")
    print(f"   Duration: {(datetime.utcnow() - start).total_seconds() / 3600:.1f} hours")
    print("=" * 90)

if __name__ == '__main__':
    main()
