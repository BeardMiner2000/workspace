# 🏆 SEASON 4 LEADERBOARD — 3-DAY BOT CHAMPIONSHIP

**Status:** 🟢 LIVE  
**Duration:** 72 hours (3 days)  
**Start Time:** March 26, 2026 02:50 UTC  
**End Time:** March 29, 2026 02:50 UTC  

**Prize:** Glory, bragging rights, and a spot in the Paper Trader League Hall of Fame

---

## 📊 CURRENT STANDINGS

| Rank | Bot | Strategy Type | Capital | BTC Value | PnL | Win Rate | Trades |
|------|-----|---------------|---------|-----------|-----|----------|--------|
| 1 | TBD | - | 0.0075 | - | - | - | - |
| 2 | TBD | - | 0.0075 | - | - | - | - |
| 3 | TBD | - | 0.0075 | - | - | - | - |
| 4 | TBD | - | 0.0075 | - | - | - | - |
| 5 | TBD | - | 0.0075 | - | - | - | - |
| 6 | TBD | - | 0.0075 | - | - | - | - |
| 7 | TBD | - | 0.0075 | - | - | - | - |
| 8 | TBD | - | 0.0075 | - | - | - | - |
| 9 | TBD | - | 0.0075 | - | - | - | - |
| 10 | TBD | - | 0.0075 | - | - | - | - |
| 11 | TBD | - | 0.0075 | - | - | - | - |
| 12 | TBD | - | 0.0075 | - | - | - | - |

---

## 🤖 COMPETITORS

### Aggressive Risk Takers (50% Risk Per Trade)

**🚀 Loser Reversal Hunter**
- **Strategy:** Mean reversion on Coinbase Big Losers
- **Personality:** Buy crashes, sell bounces
- **Max Risk:** 50% per trade
- **Target Return:** +30-50% per trade
- **Entry:** Coins down >15% in 24h, RSI < 30

**📈 Gainer Momentum Catcher**
- **Strategy:** Momentum chasing on Big Gainers
- **Personality:** FOMO rider, catches waves
- **Max Risk:** 50% per trade
- **Target Return:** +40-60% per trade
- **Entry:** Coins up >20% in 24h, momentum strong

**💥 Degen Ape 9000**
- **Strategy:** All-in conviction plays (YOLO)
- **Personality:** To the moon or rekt
- **Max Risk:** 50% per trade
- **Target Return:** +50% to +200% per trade
- **Entry:** Viral sentiment, trending social signals

**🔥 Pump Surfer**
- **Strategy:** Catches emerging altcoin pumps
- **Personality:** Rides volatility spikes
- **Max Risk:** 50% per trade
- **Target Return:** +30% to +100% per trade
- **Entry:** Volume spike + price surge detected

**⚡ Stormchaser Delta**
- **Strategy:** Event-driven, rides volatility
- **Personality:** Fast, opportunistic
- **Max Risk:** 45% per trade
- **Target Return:** +20% to +50% per trade
- **Entry:** Liquidation cascades, news spikes

**🌪️ Chaos Prophet**
- **Strategy:** Exploits volatility dislocations
- **Personality:** Thrives on chaos
- **Max Risk:** 45% per trade
- **Target Return:** +10% to +25% per trade
- **Entry:** Vol spikes, price dislocations

---

### Moderate Risk Takers (30-40% Risk Per Trade)

**🌍 Aurora Quanta**
- **Strategy:** Macro trend following
- **Personality:** Patient, measured, thesis-driven
- **Max Risk:** 40% per trade
- **Target Return:** +15% to +35% per trade
- **Entry:** Market breadth, BTC dominance alignment

**🌀 Vega Pulse**
- **Strategy:** Volatility mean reversion
- **Personality:** Plays vol extremes
- **Max Risk:** 40% per trade
- **Target Return:** +12% to +30% per trade
- **Entry:** Vol percentile > 90th

**👻 Obsidian Flux**
- **Strategy:** Price deviation mean reversion
- **Personality:** Consistent, boring alpha
- **Max Risk:** 35% per trade
- **Target Return:** +10% to +25% per trade
- **Entry:** Z-score > 2.0

**🪟 Phantom Lattice**
- **Strategy:** Pairs trading / stat arb
- **Personality:** Market neutral, balanced
- **Max Risk:** 30% per trade
- **Target Return:** +8% to +20% per trade
- **Entry:** Correlation breakdown

---

### Conservative/High-Frequency Traders (20-25% Risk Per Trade)

**🌙 Solstice Drift**
- **Strategy:** Trend following (MA crossover)
- **Personality:** Consistent, disciplined
- **Max Risk:** 35% per trade
- **Target Return:** +15% to +40% per trade
- **Entry:** 20-day MA > 50-day MA (bullish cross)

**💎 Mercury Vanta**
- **Strategy:** Orderbook microstructure
- **Personality:** Quiet, precise, fee-aware
- **Max Risk:** 20% per trade
- **Target Return:** +0.5% to +2% per trade (high frequency)
- **Entry:** Orderbook imbalance > 1.2x

---

## 🎯 COMPETITION RULES

1. **Duration:** 72 hours (Mar 26 02:50 UTC → Mar 29 02:50 UTC)
2. **Capital:** Each bot starts with 0.0075 BTC
3. **Total Pool:** 0.09 BTC
4. **Winner Criteria:** Highest BTC value at end (no liquidation required)
5. **Risk Tolerance:** All positions welcome. 50% drawdowns acceptable.
6. **Paper Trading Only:** No real capital at risk. Simulation only.
7. **Market Data:** Real Coinbase feeds (Big Gainers/Losers, market marks)
8. **Fee Simulation:** 4.875 bps taker fee applied to all trades
9. **No Liquidation:** Bots can go negative but must be rebalanced manually
10. **Monitoring:** Real-time Grafana dashboard with live leaderboard

---

## 📈 TRACKING METRICS

**Per Bot (Updated Every 5 Minutes):**
- Current BTC equity
- Realized PnL (BTC)
- Unrealized PnL (BTC)
- Win rate (%)
- Total trades
- Largest win
- Largest loss
- Max drawdown (%)
- Sharpe ratio
- Open positions (count)

**Leaderboard Sort:** By total BTC equity (highest wins)

---

## 🏅 PRIZES

| Place | Prize |
|-------|-------|
| 🥇 1st | Hall of Fame entry + bragging rights |
| 🥈 2nd | Honorable mention |
| 🥉 3rd | Certified gambler |
| 4-12 | Participation trophy |

---

## 📺 LIVE MONITORING

**Grafana Dashboard:** http://localhost:3000  
**Leaderboard Endpoint:** `GET /leaderboard` (custom API, TBD)  
**Trade Log API:** `GET /trades?season=season-004` (via trade_engine)  
**Position Monitor:** Real-time open positions per bot  

---

## 🚀 BOTS IN MOTION

All 12 bots are running simultaneously, executing trades based on:
- Real market data (Coinbase Big Gainers/Losers)
- Their individual strategies
- Their risk tolerance profiles
- Real-time market conditions

**The competition is LIVE. May the best bot win.** 🏆

---

## 📋 RULES REMINDERS

- ⚠️ **50% drawdowns are possible.** Some bots WILL go negative.
- ⚠️ **Paper trading only.** No real capital at risk.
- ⚠️ **High frequency.** Trades can execute every 5-30 seconds per bot.
- ⚠️ **Slippage included.** Market orders incur realistic slippage.
- ✅ **Market data is real.** Using actual Coinbase feeds.
- ✅ **Execution is simulated.** Orders go to Paper Trader engine, not live exchange.

---

**Season 4 Competition:** March 26-29, 2026  
**Status:** 🟢 LIVE & RUNNING  
**Bots:** 12 active  
**Capital:** 0.09 BTC  
**Winner:** TBD in 72 hours  

Good luck, bots. May the best algorithm win. 🎯

