#!/usr/bin/env python3
"""
Season 4 Bot Executor — 3-Day Competition
Automates all 12 bots trading simultaneously against each other.
"""

import asyncio
import json
import os
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

SEASON_ID = os.getenv('SEASON_ID', 'season-004')
TRADE_ENGINE_URL = os.getenv('TRADE_ENGINE_URL', 'http://localhost:8088')
DB_HOST = os.getenv('POSTGRES_HOST', 'timescaledb')
DB_PORT = os.getenv('POSTGRES_PORT', '5432')
DB_USER = os.getenv('POSTGRES_USER', 'paperbot')
DB_PASS = os.getenv('POSTGRES_PASSWORD', 'paperbot')
DB_NAME = os.getenv('POSTGRES_DB', 'paperbot')

COMPETITION_DURATION_HOURS = 72
REFRESH_INTERVAL_SECONDS = 5
MAX_CONCURRENT_ORDERS_PER_BOT = 4

# Load bot strategies
STRATEGIES_FILE = Path(__file__).parent / 'bot_strategies.json'
with open(STRATEGIES_FILE) as f:
    STRATEGIES_DATA = json.load(f)
    BOT_STRATEGIES = STRATEGIES_DATA['bot_strategies']

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

def get_bot_balances():
    """Get current balances for all bots in Season 4."""
    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT DISTINCT ON (bot_id) bot_id, free, locked
                FROM bot_balances
                WHERE season_id = %s AND asset = 'BTC'
                ORDER BY bot_id, ts DESC
            """, (SEASON_ID,))
            return {row['bot_id']: {
                'free': Decimal(str(row['free'])),
                'locked': Decimal(str(row['locked']))
            } for row in cur.fetchall()}

def get_latest_marks():
    """Get latest market prices."""
    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT DISTINCT ON (symbol) symbol, mark_price
                FROM market_marks
                WHERE season_id = %s
                ORDER BY symbol, ts DESC
                LIMIT 100
            """, (SEASON_ID,))
            return {row['symbol']: Decimal(str(row['mark_price'])) for row in cur.fetchall()}

def get_open_positions(bot_id):
    """Get open positions for a bot."""
    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT bot_id, symbol, side, quantity, entry_price
                FROM bot_orders
                WHERE season_id = %s AND bot_id = %s AND status = 'filled' AND exit_time IS NULL
                ORDER BY created_at DESC
            """, (SEASON_ID, bot_id))
            return [dict(row) for row in cur.fetchall()]

# ============================================================================
# MARKET DATA FEEDS
# ============================================================================

def get_big_losers():
    """Get Coinbase Big Losers from database."""
    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT symbol, change_24h_pct, change_1h_pct, mark_price
                FROM market_marks
                WHERE season_id = %s AND change_24h_pct < -15
                ORDER BY change_24h_pct ASC
                LIMIT 20
            """, (SEASON_ID,))
            return [dict(row) for row in cur.fetchall()]

def get_big_gainers():
    """Get Coinbase Big Gainers from database."""
    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT symbol, change_24h_pct, change_15m_pct, mark_price, volume_24h
                FROM market_marks
                WHERE season_id = %s AND change_24h_pct > 20
                ORDER BY change_24h_pct DESC
                LIMIT 20
            """, (SEASON_ID,))
            return [dict(row) for row in cur.fetchall()]

# ============================================================================
# BOT EXECUTION ENGINES
# ============================================================================

class BotExecutor:
    """Executes trades for a single bot."""
    
    def __init__(self, bot_id):
        self.bot_id = bot_id
        self.strategy = BOT_STRATEGIES.get(bot_id, {})
        self.strategy_type = self.strategy.get('type', 'unknown')
        self.risk_tolerance = self.strategy.get('risk_tolerance', 0.30)
    
    async def execute(self):
        """Main execution loop for this bot."""
        print(f"[{self.bot_id}] Starting execution ({self.strategy_type})")
        
        # Route to appropriate executor
        if self.strategy_type == 'mean_reversion':
            await self.execute_mean_reversion()
        elif self.strategy_type == 'momentum':
            await self.execute_momentum()
        elif self.strategy_type == 'macro_trend':
            await self.execute_macro_trend()
        elif self.strategy_type == 'volatility_arbitrage':
            await self.execute_volatility_arb()
        elif self.strategy_type == 'degenerate_yolo':
            await self.execute_degenerate_yolo()
        elif self.strategy_type == 'microstructure':
            await self.execute_microstructure()
        elif self.strategy_type == 'event_driven':
            await self.execute_event_driven()
        else:
            await self.execute_generic()
    
    async def execute_mean_reversion(self):
        """Mean reversion: buy dips, sell bounces."""
        balances = get_bot_balances()
        bot_balance = balances.get(self.bot_id, {})
        available_usdt = bot_balance.get('free', Decimal(0))
        
        # Check for big losers
        if self.bot_id == 'loser_reversal_hunter':
            losers = get_big_losers()
            for loser in losers[:3]:  # Take top 3 losers
                if Decimal(str(loser['change_24h_pct'])) < -15:
                    # Buy signal
                    quantity = (available_usdt * Decimal('0.20')) / Decimal(str(loser['mark_price']))
                    await self.submit_order(
                        symbol=loser['symbol'],
                        side='buy',
                        quantity=float(quantity),
                        rationale={
                            'strategy': 'mean_reversion',
                            'change_24h': float(loser['change_24h_pct']),
                            'conviction': 'capitulation_bounce'
                        }
                    )
        
        await asyncio.sleep(REFRESH_INTERVAL_SECONDS)
    
    async def execute_momentum(self):
        """Momentum: chase gainers before exhaustion."""
        balances = get_bot_balances()
        bot_balance = balances.get(self.bot_id, {})
        available_usdt = bot_balance.get('free', Decimal(0))
        
        if self.bot_id == 'gainer_momentum_catcher':
            gainers = get_big_gainers()
            for gainer in gainers[:4]:  # Take top 4 gainers
                if Decimal(str(gainer['change_24h_pct'])) > 20:
                    # Buy signal
                    quantity = (available_usdt * Decimal('0.20')) / Decimal(str(gainer['mark_price']))
                    await self.submit_order(
                        symbol=gainer['symbol'],
                        side='buy',
                        quantity=float(quantity),
                        rationale={
                            'strategy': 'momentum',
                            'change_24h': float(gainer['change_24h_pct']),
                            'conviction': 'momentum_continuation'
                        }
                    )
        
        await asyncio.sleep(REFRESH_INTERVAL_SECONDS)
    
    async def execute_macro_trend(self):
        """Macro trend: patient, long timeframe."""
        balances = get_bot_balances()
        bot_balance = balances.get(self.bot_id, {})
        available_usdt = bot_balance.get('free', Decimal(0))
        
        # Simple trend following on BTC
        marks = get_latest_marks()
        btc_price = marks.get('BTCUSDT')
        
        if btc_price:
            # Buy small amounts consistently
            quantity = (available_usdt * Decimal('0.10')) / btc_price
            await self.submit_order(
                symbol='BTCUSDT',
                side='buy',
                quantity=float(quantity),
                rationale={
                    'strategy': 'macro_trend',
                    'btc_price': float(btc_price),
                    'conviction': 'trend_following'
                }
            )
        
        await asyncio.sleep(REFRESH_INTERVAL_SECONDS * 2)
    
    async def execute_volatility_arb(self):
        """Volatility arbitrage: exploit spikes."""
        balances = get_bot_balances()
        bot_balance = balances.get(self.bot_id, {})
        available_usdt = bot_balance.get('free', Decimal(0))
        
        # Buy big losers, short big gainers concept (simplified to buy losers)
        losers = get_big_losers()
        if losers:
            loser = losers[0]
            quantity = (available_usdt * Decimal('0.15')) / Decimal(str(loser['mark_price']))
            await self.submit_order(
                symbol=loser['symbol'],
                side='buy',
                quantity=float(quantity),
                rationale={
                    'strategy': 'volatility_arb',
                    'vol_spike': 'detected',
                    'conviction': 'reversion_expected'
                }
            )
        
        await asyncio.sleep(REFRESH_INTERVAL_SECONDS)
    
    async def execute_degenerate_yolo(self):
        """Degenerate YOLO: all-in on high-conviction plays."""
        balances = get_bot_balances()
        bot_balance = balances.get(self.bot_id, {})
        available_usdt = bot_balance.get('free', Decimal(0))
        
        gainers = get_big_gainers()
        if gainers:
            # Go all-in on top gainer
            gainer = gainers[0]
            quantity = (available_usdt * Decimal('0.40')) / Decimal(str(gainer['mark_price']))
            await self.submit_order(
                symbol=gainer['symbol'],
                side='buy',
                quantity=float(quantity),
                rationale={
                    'strategy': 'degenerate_yolo',
                    'conviction': 'to_the_moon',
                    'bet_size': '40%_of_portfolio'
                }
            )
        
        await asyncio.sleep(REFRESH_INTERVAL_SECONDS * 3)
    
    async def execute_microstructure(self):
        """Microstructure: high frequency, small edges."""
        balances = get_bot_balances()
        bot_balance = balances.get(self.bot_id, {})
        available_usdt = bot_balance.get('free', Decimal(0))
        
        # Buy and hold small amounts (simulate frequent trades)
        marks = get_latest_marks()
        btc_price = marks.get('BTCUSDT')
        
        if btc_price and available_usdt > Decimal('0.00001'):
            quantity = (available_usdt * Decimal('0.05')) / btc_price
            await self.submit_order(
                symbol='BTCUSDT',
                side='buy',
                quantity=float(quantity),
                rationale={
                    'strategy': 'microstructure',
                    'edge': 'orderbook_imbalance',
                    'conviction': 'small_repeated_edge'
                }
            )
        
        await asyncio.sleep(REFRESH_INTERVAL_SECONDS)
    
    async def execute_event_driven(self):
        """Event-driven: fast, reacts to volatility spikes."""
        balances = get_bot_balances()
        bot_balance = balances.get(self.bot_id, {})
        available_usdt = bot_balance.get('free', Decimal(0))
        
        # Buy losers opportunistically
        losers = get_big_losers()
        if losers:
            for loser in losers[:2]:
                quantity = (available_usdt * Decimal('0.22')) / Decimal(str(loser['mark_price']))
                await self.submit_order(
                    symbol=loser['symbol'],
                    side='buy',
                    quantity=float(quantity),
                    rationale={
                        'strategy': 'event_driven',
                        'event': 'volatility_spike',
                        'conviction': 'opportunistic'
                    }
                )
        
        await asyncio.sleep(REFRESH_INTERVAL_SECONDS)
    
    async def execute_generic(self):
        """Fallback: simple trend following."""
        await asyncio.sleep(REFRESH_INTERVAL_SECONDS * 2)
    
    async def submit_order(self, symbol, side, quantity, rationale):
        """Submit order to trade engine."""
        try:
            payload = {
                'season_id': SEASON_ID,
                'bot_id': self.bot_id,
                'symbol': symbol,
                'side': side,
                'order_type': 'market',
                'quantity': quantity,
                'rationale': rationale,
                'metadata': {
                    'timestamp': datetime.utcnow().isoformat(),
                    'strategy_type': self.strategy_type
                }
            }
            
            response = requests.post(
                f'{TRADE_ENGINE_URL}/orders',
                json=payload,
                timeout=5
            )
            
            if response.status_code == 200:
                result = response.json()
                print(f"[{self.bot_id}] Order submitted: {symbol} {side} {quantity}")
                return result
            else:
                print(f"[{self.bot_id}] Order failed: {response.text}")
                
        except Exception as e:
            print(f"[{self.bot_id}] Error submitting order: {e}")

# ============================================================================
# MAIN ORCHESTRATOR
# ============================================================================

async def run_competition():
    """Run the 3-day competition with all 12 bots."""
    print("=" * 70)
    print(f"🚀 SEASON 4 BOT COMPETITION STARTED")
    print(f"   Duration: {COMPETITION_DURATION_HOURS} hours")
    print(f"   Bots: {len(BOT_STRATEGIES)}")
    print(f"   Season: {SEASON_ID}")
    print("=" * 70)
    
    # Create executor for each bot
    executors = [BotExecutor(bot_id) for bot_id in BOT_STRATEGIES.keys()]
    
    # Run all bots concurrently
    start_time = datetime.utcnow()
    end_time = start_time + timedelta(hours=COMPETITION_DURATION_HOURS)
    
    while datetime.utcnow() < end_time:
        try:
            # Execute all bots in parallel
            tasks = [executor.execute() for executor in executors]
            await asyncio.gather(*tasks)
            
            # Print status every 60 seconds
            if int((datetime.utcnow() - start_time).total_seconds()) % 60 == 0:
                elapsed = (datetime.utcnow() - start_time).total_seconds() / 3600
                print(f"[{elapsed:.1f}h] All bots executing...")
            
        except Exception as e:
            print(f"Error in main loop: {e}")
            await asyncio.sleep(10)
    
    print("=" * 70)
    print("🏁 COMPETITION ENDED")
    print("=" * 70)

def main():
    """Entry point."""
    print(f"Starting Bot Executor for {SEASON_ID}...")
    asyncio.run(run_competition())

if __name__ == '__main__':
    main()
