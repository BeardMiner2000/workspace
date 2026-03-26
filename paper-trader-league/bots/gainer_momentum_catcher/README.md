# 📈 Gainer Momentum Catcher

**Season:** 4  
**Strategy:** Momentum Chasing on Coinbase "Big Gainers"  
**Risk Tolerance:** Maximum (50% per trade)  
**Capital:** 0.015 BTC  
**Status:** Live  

---

## Overview

Gainer Momentum Catcher hunts the "Big Gainers" tab on Coinbase, looking for tokens already up 20-30% that show continued momentum. The thesis: why miss the 80% move if you can catch it at +30%? The bot FOMO's in with full conviction, accepts 50% drawdowns as acceptable risk, and exits on any sign of exhaustion.

## Strategy Snapshot

**Entry Signal:**
- Coin appears in Coinbase "Big Gainers" (up >20% in 24h)
- Up >5% in last 15 minutes (momentum continuing)
- RSI 50-75 (strong but not yet exhausted)
- Price above 20-day MA (trend is your friend)
- Volume > $50M (liquidity to escape when needed)

**Position Size:**
- 20% of available USDT per trade
- Max 4 concurrent positions
- Different coins only (no pyramiding)

**Exit Rules:**
- **Take Profit:** +40-60% (you caught the bounce, be happy)
- **Hard Stop:** -50% (the vibe died, cut losses)
- **Exhaustion Signal:** RSI > 85 AND volume drops 20% from 1h average
- **Time Stop:** 3 hours max (if still under +20%, you're wrong)
- **Hourly Check:** Exit if momentum is dead and gain < 20%

## Example Trades

### Trade 1: Classic Momentum Chase
```
11:00 AM  Entry: SOL up +28% in 24h, up +7% in 30 min. RSI = 68. Buy SOL.
11:25 AM  +8.5% gain from entry. Volume strong. RSI = 72. Hold.
11:50 AM  +21% gain from entry. RSI = 82. Volume drops 15%. Sell 50%.
12:00 PM  Remaining position at +25% gain. RSI > 85. Sell all.
          Realized PnL: +22% (50% sold at +21%, 50% sold at +25%)
```

### Trade 2: The Early Exit
```
2:30 PM   Entry: ETH up +24% in 24h. RSI = 60. Buy ETH.
3:00 PM   +3% gain. Volume dries up. RSI stays flat.
3:30 PM   +1% gain. 1 hour has passed. Still under +20%. Exit for small loss.
```

### Trade 3: The Rug Pull
```
1:00 PM   Entry: Random altcoin up +35%. RSI = 70. Buy.
1:15 PM   +15% gain. Looking good.
1:30 PM   Instant dump. -32% from entry. Rug pulled. HARD CUT. Exit immediately.
          Loss: -32% (less than our -50% budget, so exit quick to preserve capital).
```

### Trade 4: Multi-Position Day
```
11:00 AM  Entry #1: SOL up +22%. Position A.
11:30 AM  Entry #2: ETH up +18%. Position B.
12:00 PM  Entry #3: AVAX up +26%. Position C.
12:30 PM  Entry #4: DOGE up +20%. Position D.

1:00 PM   Sell Position A at +35%. Realized: +7%.
1:15 PM   Sell Position B at +28%. Realized: +5.6%.
1:45 PM   Position C hits -40%. Cut for -40% loss.
2:00 PM   Position D still +8%, 2h elapsed, under +20%. Exit for +1.6% loss.

Net: +7% + 5.6% - 8% - 1.6% = +3% on $X * 4 concurrent = overall +3% portfolio swing
```

## Expected Performance

**Win Rate:** ~60% (momentum continuation is real, but exits are tight)  
**Avg Winner:** +45%  
**Avg Loser:** -20% to -50% (cuts are aggressive)  
**Risk/Reward:** ~1:1 (high precision required, but consistent)  

**Monthly Goal:** 15-25% gains (higher win rate than Loser Reversal, so more compounding)

## Integration

**Grafana Dashboard:** `paper_trader_s4` → "Gainer Momentum Catcher" tab  
**Real-Time Tracking:**
- Entry/exit log
- Current positions (symbol, entry price, gain/loss, elapsed time)
- FOMO accuracy rate (how often we catch tops vs. catch the wave)
- Daily PnL vs. BTC benchmark
- Win/loss ratio
- Max drawdown tracker
- Exhaustion signal heatmap (RSI, volume, momentum scores)

## Notes

- **FOMO is a feature, not a bug.** This bot is designed to chase.
- **Speed matters.** Missing the first 60 seconds of a +30% move kills the R:R.
- **No hedging, no diversification.** Full conviction momentum plays only.
- **4 concurrent positions = 4x leverage on volatility.** Drawdowns hit faster.
- **Feed latency is critical.** Coinbase "Big Gainers" refresh every 5 minutes; bot wins in the first candle.
