# 🚀 Loser Reversal Hunter

**Season:** 4  
**Strategy:** Mean Reversion on Coinbase "Big Losers"  
**Risk Tolerance:** Maximum (50% per trade)  
**Capital:** 0.015 BTC  
**Status:** Live  

---

## Overview

Loser Reversal Hunter hunts the "Big Losers" tab on Coinbase, looking for coins that have crashed >15% in 24 hours. The thesis: when panic selling hits, that's often the bottom. The bot wades into capitulation with full conviction, accepts 50% drawdowns as the cost of entry, and exits on 30-50% bounces.

## Strategy Snapshot

**Entry Signal:**
- Coin appears in Coinbase "Big Losers" (down >15% in 24h)
- Down >8% in last 1 hour (sustained selling)
- RSI < 30 (oversold, capitulation zone)

**Position Size:**
- 20% of available USDT per trade
- Max 3 concurrent positions
- Different coins only (no pyramiding into same pair)

**Exit Rules:**
- **Take Profit:** +30-50% (ride the rebound, don't get greedy)
- **Hard Stop:** -50% (you lost the bet, move on)
- **Time Stop:** 4 hours max (if still under +5% gain, exit for realized loss)
- **Reversal:** If bounces to +50%, close immediately (don't hold through the re-pump)

## Example Trades

### Trade 1: BTC Capitulation Bounce
```
10:00 AM  Entry: BTC crashes to $62k (down 12% in 6h). RSI = 28. Buy 0.15 BTC.
10:45 AM  +3.2% gain. Hold, waiting for bigger rebound.
11:15 AM  +5.2% gain from entry. Sell 50% of position. Realized PnL: +2.5%.
11:30 AM  Remaining position hits +8%. Sell all. Full realized PnL: +4%.
```

### Trade 2: Altcoin Mean Reversion Whip
```
2:00 PM   Entry: SOL crashes to $135 (down 18% in 4h). RSI = 25. Buy SOL.
2:30 PM   -10% from entry. Hold (hard stop is -50%, not panicking yet).
3:15 PM   -8% from entry. Still holding.
4:00 PM   +2% from entry. Sell 30% for micro-profit. Realized: +0.6%.
4:45 PM   +15% from entry. Sell remaining 70%. Realized PnL: +10.5%.
```

### Trade 3: The Brutal Exit
```
1:00 PM   Entry: PEPE crashes 20%. Buy 20% allocation. RSI = 22.
1:30 PM   -15% from entry. Still holding (we budget -50%).
2:00 PM   -30% from entry. Holding...
2:45 PM   -48% from entry. We're at the edge.
3:00 PM   -50% from entry. HARD STOP. Exit with full loss. Move on to next trade.
```

## Expected Performance

**Win Rate:** ~55% (not all reversals work)  
**Avg Winner:** +35%  
**Avg Loser:** -30% (cut early) to -50% (hard stop)  
**Risk/Reward:** ~1:1.2 (acceptable, but high variance)  

**Monthly Goal:** 10-15% gains (or larger swings with high drawdown periods)

## Integration

**Grafana Dashboard:** `paper_trader_s4` → "Loser Reversal Hunter" tab  
**Real-Time Tracking:**
- Entry/exit log
- Current positions (symbol, entry price, current gain/loss)
- Daily PnL vs. BTC benchmark
- Win/loss ratio
- Max drawdown tracker

## Notes

- **Volatility is the feature, not a bug.** This bot expects 30-50% swings daily.
- **No hedging.** Full conviction plays only.
- **Multiple simultaneous positions increase compounding** but also increase liquidation risk if market turns.
- **Feed latency matters.** Coinbase "Big Losers" updates every 5 minutes; real alpha is in the first 60 seconds of each update.
