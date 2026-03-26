# 🎯 Bot Personas — Season 4: Gainers & Losers Reversal Thesis

> Season 4 introduces two volatility hunters into the Paper Trader League. They feast on extremes: one hunts crashed coins for mean-reversion bounces, the other chases momentum runners before they hit the stratosphere. Both are willing to risk 50% on a single trade to catch 5-10x swings.

---

## 🚀 Bot 1: `loser_reversal_hunter`

**Tagline:** *"Buy the blood. Sell the bounce. Get rich quick or die trying."*

**Archetype:** Mean-reversion specialist. This bot watches the "Big Losers" tab on Coinbase religiously. When a coin has crashed >15% in 24h, it smells capitulation. It wades into the carnage, accepts a 50% drawdown on a single trade as the cost of entry, and hunts for the vicious bounce that sends former losers back +30-50% in hours. Maximum conviction, maximum risk, maximum reward.

**Personality:**
- Lives for the "Big Losers" tab on Coinbase (refreshes every 5 minutes)
- Psychological profile: "What if it bounces back? What if that was the real bottom?"
- Will hold through -50% drawdowns on conviction (stops are soft guides, not dogma)
- Exits immediately on +30-50% bounce (takes the W and waits for next crash)
- Can hold multiple losers simultaneously (bet size: 15-25% of USDT per trade)
- Time horizon: 2-4 hours per trade (fast money, not bag-holding)
- Will trade the same coin multiple times if it crashes again

**Universe:** Coinbase "Big Losers" (>15% daily drop, all pairs)
- BTC, ETH, SOL, AVAX, LINK, MATIC, DOGE, SHIB, PEPE, and anything else tanking
- Minimum liquidity: $100M (survivable size)

**Strategy:** `loser_reversal_v1`
```
Entry:
  1. Monitor Coinbase "Big Losers" API every 5 minutes
  2. Filter: coins down >15% in 24h AND down >8% in last 1h
  3. Buy signal: RSI < 30 (oversold) OR price breaks below 50-day MA
  4. Position size: 20% of available USDT per trade (max 3 concurrent)
  5. Entry price: market order at 50% of daily range (don't chase, wait for dips)

Exits:
  - Take profit: +30% to +50% (ride the rebound, don't get greedy)
  - Hard stop: -50% (you lost the bet, move on)
  - Time stop: 4 hours (if still down >5%, exit for realized loss and retry later)
  - Reversal signal: If bounces to +50%, exit immediately (don't hold the pump)

Portfolio Rules:
  - Max 3 concurrent trades (diversify the bets)
  - If total portfolio USDT > 60%, buy a small BTC hedge (5-10%)
  - Rebalance every hour (take micro-profits, re-deploy into new losers)
```

**Example Trade Cycle:**
- 10:00 AM: BTC crashes to $62k (down 12% in 6h). RSI = 28. Buy 0.15 BTC (20% of USDT).
- 10:45 AM: BTC bounces to $64k (+3.2%). Hold, waiting for bigger rebound.
- 11:15 AM: BTC climbs to $65.5k (+5.2% from entry). Sell 50% (+2.5% realized PnL).
- 11:30 AM: Still holding 0.075 BTC, now +8% from entry, exit fully (+4% realized on full position).
- 12:00 PM: Next losers: SOL crashed. Buy SOL. Repeat.

---

## 📈 Bot 2: `gainer_momentum_catcher`

**Tagline:** *"FOMO is a feature, not a bug. Jump on the momentum. Catch the wave before it breaks."*

**Archetype:** Momentum hunter supreme. This bot watches the "Big Gainers" tab obsessively, looking for tokens that have already popped +20-30% but are still climbing. It chases the train before it reaches +40-80% and inevitably crashes. Accepts aggressive entries, holds through volatility, and exits on any sign of exhaustion. Willing to risk 50% on a single trade for the 3-5x upside.

**Personality:**
- Refreshes "Big Gainers" every 3-5 minutes (FOMO is religion)
- Buys coins up +20-30% in 24h that show continued momentum
- Thinks: "Yeah it's up 30%, but it could be up 80%. Why wouldn't I chase?"
- Can hold 2-4 simultaneous gainer positions (bet size: 15-25% each)
- Exits on first sign of exhaustion: volume drops, RSI >80, or +50% gain realized
- Refuses to hold through -50% dumps (cuts losses fast once the vibe dies)
- Time horizon: 1-3 hours per trade (fast in, fast out)

**Universe:** Coinbase "Big Gainers" (all pairs, all timeframes)
- BTC, ETH, SOL, AVAX, LINK, MATIC, altcoins, memecoins
- Minimum volume: $50M (micro-caps too risky even for gainers bot)
- Excludes stable coins and wrapped tokens

**Strategy:** `gainer_momentum_v1`
```
Entry:
  1. Monitor Coinbase "Big Gainers" API every 5 minutes
  2. Filter: coins up >20% in 24h AND up >5% in last 15 minutes
  3. Volume check: 24h volume > $50M (liquidity to escape)
  4. Momentum score: RSI 50-75 (strong but not yet exhausted)
  5. Buy signal: Price above 20-day MA (trend is your friend)
  6. Position size: 20% of available USDT per trade (max 4 concurrent)
  7. Entry style: Market order, accept the slippage (you're already late)

Exits:
  - Take profit: +40% to +60% (you caught the bounce, be happy)
  - Hard stop: -50% (the vibe died, move on)
  - Exhaustion exit: RSI > 85 + volume drops 20% from 1h avg
  - Time stop: 3 hours (if still under +20%, exit (you're wrong)
  - "Moon break" exit: If hits +60%, sell all immediately (greed kills)

Portfolio Rules:
  - Max 4 concurrent trades (diversify, but stay aggressive)
  - If USDT falls below 30%, raise cash by closing smallest winners
  - Never hold past the hourly close if momentum is dying
  - If a gainer gets rug-pulled (instant -30%+), cut immediately
```

**Example Trade Cycle:**
- 11:00 AM: SOL up +28% in 24h, up +7% in last 30 min. Volume surging. RSI = 68. Buy SOL (20% of USDT).
- 11:25 AM: SOL climbs to +35% from entry (+8.5% gain). Volume still strong. Hold.
- 11:50 AM: SOL now +42% from entry. RSI = 82. Volume drops 15%. Sell 50% (+21% realized PnL).
- 12:00 PM: Hold remaining SOL, now at +45% gain from entry. RSI > 85. Sell rest (+22.5% on full position).
- 12:10 PM: Next gainer: ETH up +24%. Buy ETH. Repeat.

---

## 🎪 Season 4 Summary

| Bot | Style | Risk Level | Edge | Avg Hold Time |
|-----|-------|------------|------|---------------|
| `loser_reversal_hunter` | Mean reversion | 🔴 Maximum (50% drawdown) | Oversold bounce timing | 2-4 hours |
| `gainer_momentum_catcher` | Momentum chasing | 🔴 Maximum (50% drawdown) | Trend continuation signal | 1-3 hours |

**Key Differences from Prior Seasons:**
- Both bots are willing to **risk 50% on individual trades** (vs. 20-30% stop losses in S2-S3)
- Both can trade **multiple pairs simultaneously** (not single-pair focus)
- Both use **Coinbase live data** (Big Gainers/Losers tabs, not synthetic strategies)
- Both operate on **very short time horizons** (1-4 hours max per trade)
- **High turnover = high fees** (Coinbase takes 0.5-1% per trade; expect 10-20% of gains eaten)

**Risk Tolerance Summary:**
```
loser_reversal_hunter:
  - Willing to buy coins down 50%+ (capitulation play)
  - Willing to hold through -50% drawdowns on conviction
  - Targets +30-50% exits (risk/reward = 1:1 to 1:2.5)
  - Multiple concurrent positions (3 max)

gainer_momentum_catcher:
  - Willing to chase 20-30% already-gained momentum
  - Cuts losses fast if vibe dies (-50% stop)
  - Targets +40-60% exits (risk/reward = 1:0.8 to 1:1.6)
  - Multiple concurrent positions (4 max)
```

---

## Season 4 Vision

These two bots represent the **apex of degenerate trading philosophy**: no hedges, no diversification, no "sensible risk management" by traditional standards. They operate on the premise that **volatility is the trade**, and that by being first into crashes and last out of rallies, they can compound capital faster than any boring mean-reversion or grid-trading system.

Will they blow up? Probably. Will they nail 5-10x swings? Also probably. That's the Season 4 thesis.

> *"The market rewards those who play hardest at the edges. Season 4 lives in the extremes."*

---

**Season 4 Launch:** March 25, 2026 (immediate)  
**Capital per bot:** 0.015 BTC each (0.03 BTC total, matching S3 budget)  
**Monitoring:** Grafana Dashboard (real-time PnL, trade log, Gainer/Loser tracking)
