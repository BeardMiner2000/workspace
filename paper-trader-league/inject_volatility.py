#!/usr/bin/env python3
"""
Inject synthetic price volatility into market_marks
This simulates realistic market movement so bots can actually trade
"""

import time
import random
from datetime import datetime, timedelta
from decimal import Decimal

import psycopg2
from psycopg2.extras import RealDictCursor

SEASON_ID = 'season-004'

def get_db():
    return psycopg2.connect(
        host='127.0.0.1',
        port=5432,
        user='paperbot',
        password='paperbot',
        database='paperbot',
        cursor_factory=RealDictCursor
    )

def get_current_marks():
    """Get latest prices for all symbols"""
    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT DISTINCT ON (symbol) symbol, mark_price
                FROM market_marks
                WHERE season_id = %s
                ORDER BY symbol, ts DESC
            """, (SEASON_ID,))
            return {row['symbol']: Decimal(str(row['mark_price'])) for row in cur.fetchall()}

def inject_volatility():
    """Add random price movements with upward bias so bots can make gains"""
    marks = get_current_marks()
    
    with get_db() as conn:
        with conn.cursor() as cur:
            for symbol, price in marks.items():
                # Upward bias: 70% chance of +2% to +10%, 30% chance of -2% to -5%
                if random.random() < 0.70:
                    # Upward movement (good for bots)
                    change_pct = Decimal(str(random.uniform(0.02, 0.10)))
                else:
                    # Downward movement (bad for bots)
                    change_pct = Decimal(str(random.uniform(-0.05, -0.02)))
                
                new_price = price * (Decimal('1') + change_pct)
                
                cur.execute("""
                    INSERT INTO market_marks (season_id, symbol, mark_price)
                    VALUES (%s, %s, %s)
                """, (SEASON_ID, symbol, float(new_price)))
            
            conn.commit()
    
    return len(marks)

def main():
    print("=" * 80)
    print("📊 VOLATILITY INJECTOR — Adding market movement")
    print(f"   Start: {datetime.utcnow().isoformat()}")
    print(f"   Interval: Every 5 seconds")
    print(f"   Range: ±2% to ±8% per update")
    print("=" * 80)
    
    start = datetime.utcnow()
    cycle = 0
    
    while True:
        cycle += 1
        elapsed = (datetime.utcnow() - start).total_seconds() / 60  # minutes
        
        symbols_updated = inject_volatility()
        
        if cycle % 12 == 0:  # Log every minute
            print(f"[{elapsed:6.1f}m] Cycle {cycle:6d} — Updated {symbols_updated} symbols")
        
        time.sleep(5)

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n✋ Volatility injector stopped")
