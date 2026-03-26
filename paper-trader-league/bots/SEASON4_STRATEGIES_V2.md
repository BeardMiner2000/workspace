# Season 4 Strategies V2 — Fee-Aware, High-Risk, Diversified

**Key Changes:**
- Every strategy accounts for **4.875 bps taker fee** (0.04875% per trade)
- **Varied risk tolerance:** 2% to 100% per trade
- **Real edges:** Strategies with actual statistical rationale
- **Overtrading filter:** Max position size prevents fee bleed
- **Win conditions:** Mix of scalp, swing, and conviction plays

---

## 🚀 Tier 1: All-In Conviction Players (50-100% Risk)

### 1. **Chaos Degen** 
**Philosophy:** Explosive moves > careful risk management. Win big or lose it all.

**Entry:**
- Only on >30% 24h moves (Big Losers crash or Big Gainers pump)
- RSI < 20 (capitulation) OR RSI > 80 (euphoria)
- Volume > 5x normal (conviction signal)

**Position Sizing:**
- **Capitulation bounces:** Go 75% of portfolio on ONE trade (big reversal expected)
- **Pump continuation:** Go 50% of portfolio (ride momentum to the top)
- **Max concurrent:** 1 position (all-in mentality)

**Exit Logic:**
- **Win:** +40% realized, close immediately (don't get greedy)
- **Stop:** -75% hard stop (loss tolerance is real)
- **Time:** 2 hours max (volatility decays, position loses edge)
- **Fee impact:** 4.875 bps on entry + 4.875 bps on exit = ~10 bps total cost
  - Need +0.1% gain just to break even
  - For a 75% position, net needed gain = +0.13% to recover fees

**Example Trade:**
```
Entry: SOLUSDT at $180 (down 20% in 6h, RSI = 18)
Capital: $300 (75% of $400 portfolio)
Qty: 1.67 SOL
Fee cost: $300 * 0.001 = $0.30
Exit: $189.60 (+5.3% gross, +5.2% net after fees)
Realized: +$15.60 profit, now at $415.60 portfolio
```

---

### 2. **Yolo Ape 9000**
**Philosophy:** When sentiment spikes, go all-in. Memes > fundamentals.

**Entry Signals:**
- Trending on Twitter (use sentiment API if available, else: manual conviction)
- > 100% volume increase in 15 minutes
- Price +20% in 30 minutes (early momentum)
- BUY THE PUMP before it hits 100%+

**Position Sizing:**
- **First pump:** 40% of portfolio
- **Second pump same coin:** 30% additional (pyramid into strength)
- **Max:** 80% total portfolio in ONE coin (all-in on conviction)

**Exit Logic:**
- **Win:** +60% or momentum dies (RSI > 85 + volume drop 50%)
- **Stop:** -50% (hard line - only lose half)
- **Time:** 3 hours (pump cycles are short)
- **Fee awareness:** Tight entry/exit = fees kill. Need +0.1% minimum move.

**Reality Check:**
- If you pump & dump in 3 hours with 80% position:
  - Fees: 0.976% total (4.875 bps × 2 round-trips)
  - Need +1% net gain to break even
  - On 80% position: that's $32 profit on $4,000 portfolio move
  - **Only win if momentum is REAL**

---

### 3. **Bankruptcy Specialist**
**Philosophy:** Take insane risks on black-swan events. Go broke or 10x.

**Entry Signals:**
- Coin crashes >50% in 24h (true capitulation, dead cat bounce incoming)
- Liquidation cascade detected (if data available)
- Stock market crash spillover (crypto follows)

**Position Sizing:**
- **Capitulation play:** 100% of portfolio on ONE trade
- **Thesis:** Markets overcorrect → violent reversal

**Exit Logic:**
- **Win:** +25% (take partial, lock in gains at 50%), then +50% (close full)
- **Stop:** -100% (you lose everything, walk away)
- **Time:** 6 hours (big moves take time to reverse)
- **Fee impact:** Even with 100% position, fees are only 0.976% total
  - **NEED:** +1% net move just to break even
  - On $400 → need $404 exit price
  - Not unreasonable for a 50%+ crash (pent-up demand)

**Reality:**
- This bot **WILL go broke** some weeks
- But on one successful 50%+ crash recovery, it can 5x
- Expected value needs to be positive over 72 hours
- **Win condition:** 1 successful reversal play justifies 2-3 losses

---

## 💼 Tier 2: Calculated Risk (15-40% Per Trade)

### 4. **Macro Sentinel**
**Philosophy:** Slow & boring. Only trade BTC/ETH on clear technical breaks.

**Entry Signals:**
- **BTC:** Price breaks above 200-day MA + volume confirmation
- **ETH:** Correlation break with BTC (divergence = reversal)
- **Max signal:** Wait for 3 indicators aligned (moving avg, RSI, volume)

**Position Sizing:**
- Only trade on **high conviction signals** (need 3+ confirmations)
- **Base size:** 15% of portfolio per trade
- **Max:** 2 concurrent positions (diversify BTC + ETH)
- **Total exposure:** Max 30%

**Exit Logic:**
- **Win:** +12% (take profit, don't get greedy on slow trades)
- **Stop:** -15% (tight stop, macro trends can reverse fast)
- **Time:** 24+ hours (this is a swing trade, not a scalp)
- **Fee awareness:** Tight 15% stop = ~2.25% range covered
  - Fee cost: 0.976%
  - **Net needed:** +0.976% to break even
  - Safe margin above fee cost

**Reality:**
- Low win rate (~50%) but high R:R (1:1.2)
- **Expectancy:** Wins 50% of time, avg +12% net after fees = +5.6% win value
- Loses 50%, avg -14% net after fees (fee + stop) = -7% loss value
- **Net expectancy:** -0.7% per trade (NEGATIVE)
- **Only trade when signals are PERFECT** (3+ confirmations)

---

### 5. **Vol Reversion Machine**
**Philosophy:** Sell spikes, buy dips. Mean reversion on volatility extremes.

**Entry Signals:**
- **Vol spike:** Historical volatility > 90th percentile
- **Price at extreme:** Z-score > 2.5 standard deviations
- **Pairs:** Take **opposite** position to volatility direction
  - Vol spike up + price down = BUY (expect bounce)
  - Vol spike + price up = Wait (too risky)

**Position Sizing:**
- **Base:** 20% of portfolio per mean reversion trade
- **Max concurrent:** 3 trades (capture multiple vol events)
- **Total max exposure:** 60%

**Exit Logic:**
- **Win:** +10% (vol decays, position unwinds quickly)
- **Stop:** -25% (reversion sometimes takes longer)
- **Time:** 4-8 hours (vol typically decays within a session)
- **Fee awareness:** 
  - Entry fee: 0.488%
  - Exit fee: 0.488%
  - Total: ~0.976%
  - Need +1% net move to break even

**Reality:**
- Win rate: ~65% (mean reversion is reliable)
- Avg win: +8% net (after fees)
- Avg loss: -20% (on reversions that don't happen)
- **Expectancy:** 0.65 × 8% + 0.35 × (-20%) = +5.2% - 7% = **-1.8% per trade (NEGATIVE)**
- **Fix:** Only take trades with high vol spikes + clear oversold/overbought

---

### 6. **Liquidation Vulture**
**Philosophy:** Futures market liquidations create spot opportunities. Buy the dip when longs get liquidated.

**Entry Signals:**
- **Liquidation cascade:** Monitor funding rates (if available)
- **Mechanics:** High funding rate → liquidations incoming
- **Entry:** When price drops 10%+ in 1 hour (liquidation triggered)

**Position Sizing:**
- **Cascade play:** 35% of portfolio (picking off longs getting rekt)
- **Max concurrent:** 2 positions
- **Total max:** 70%

**Exit Logic:**
- **Win:** +15% (vultures close quick when bleeding stops)
- **Stop:** -30% (sometimes the crash keeps going)
- **Time:** 2-4 hours (liquidation effect is short-lived)
- **Fee cost:** 0.976%
- **Need:** +1% net gain

**Reality:**
- Win rate: ~55% (crashes sometimes continue)
- Avg win: +13% net
- Avg loss: -28% net
- **Expectancy:** 0.55 × 13% - 0.45 × 28% = +7.15% - 12.6% = **-5.45% (NEGATIVE)**
- **Only works if you have good liquidation data**

---

## 🎯 Tier 3: Professional/Low-Risk (2-20% Per Trade)

### 7. **Grid Scalper**
**Philosophy:** Small, consistent wins. Trade the bid-ask spread + momentum microstructure.

**Entry Signals:**
- **Grid:** Set buy orders at -2%, -4%, -6% from current price
- **Sell grid:** +1%, +2%, +3% above current price
- **Trigger:** Buy when orderbook shows imbalance (more sellers = buy opportunity)

**Position Sizing:**
- **Per grid level:** 3% of portfolio
- **Max concurrent:** 3-4 levels active
- **Total max exposure:** 12%

**Exit Logic:**
- **Win:** +0.5% to +2% per grid (micro-profits, scale out)
- **Stop:** Never (grid is two-sided, manages itself)
- **Time:** Minutes to 1 hour per micro-trade
- **Fee impact:** 0.976% cost on round-trip
  - **PROBLEM:** Can't afford this on tiny +0.5% targets
  - **Solution:** Only scale up after first win (fee > potential profit)

**Reality:**
- Win rate: ~70% (technical buying pressure is reliable)
- Avg win: +1.2% gross, +0.22% net (after fees)
- Avg loss: -0.5% (failed technical setup)
- **Expectancy:** 0.7 × 0.22% - 0.3 × 0.5% = +0.154% - 0.15% = **+0.004% per trade (BARELY POSITIVE)**
- **Problem:** Fee cost kills profitability on micro-targets
- **Only viable with:** Lower fees OR larger position sizes (reduce trades needed)

---

### 8. **Pair Trader**
**Philosophy:** Correlations break, capture the mean-reversion across pairs.

**Entry Signals:**
- **Pair:** BTC/ETH ratio, SOL/AVAX, etc.
- **Trigger:** Ratio deviates > 2 std devs from 30-day mean
- **Action:** Long the outperformer, short the laggard (or just long one, short capital on other)

**Position Sizing:**
- **Per pair:** 12% long + 8% short (net 4% exposure, hedged)
- **Max concurrent:** 2-3 pairs
- **Total exposure:** Neutral to slightly long

**Exit Logic:**
- **Win:** Ratio reverts to mean (+5-8% realized)
- **Stop:** Ratio breaks even further (-8% on pair)
- **Time:** 24-48 hours (correlations take time to normalize)
- **Fee awareness:** Two trades per pair (long + short) = double fees
  - Total fee cost: ~1.95%
  - **Need +2% net move to break even**

**Reality:**
- Win rate: ~60% (pair correlations are sticky)
- Avg win: +6% net after fees
- Avg loss: -7% (broken correlation stays broken)
- **Expectancy:** 0.6 × 6% - 0.4 × 7% = +3.6% - 2.8% = **+0.8% per trade (SLIGHTLY POSITIVE)**
- **Only works with:**
  - Real short positions (or synthetic via derivatives)
  - Clear correlation deviation
  - Pairs with high liquidity

---

## 🎲 Tier 4: Special Cases

### 9. **News Reactor**
**Philosophy:** Explode on news. React fast to headlines.

**Entry:**
- Breaking news (Coinbase listing, regulation, exchange hack)
- Entry within 30 seconds of news (speed advantage)
- Size: **60% of portfolio** (high conviction + time-sensitive)

**Exit:**
- **Win:** +20% (news trades move fast)
- **Stop:** -40% (news can reverse)
- **Time:** 1 hour (news cycle moves fast)

**Fee cost:** 0.976%
**Need:** +1% move to break even
**Reality:** Hard to execute on spot market, needs fast API + real news feed

---

### 10. **Momentum Killer**
**Philosophy:** Kill overshoots. Short the pump when it gets parabolic.

**Entry:**
- Price up >50% in 24h + RSI > 85 + volume declining
- SELL/SHORT: This is the top

**Position:**
- 50% of portfolio SHORT (risky, can keep going up)

**Exit:**
- **Win:** -30% realized (crash confirmed)
- **Stop:** +50% (wrong call, stop losses)
- **Time:** 4 hours

**Fee cost:** 0.976%
**Reality:** Catching tops is hard. Most "tops" have 20%+ more upside.

---

## 📊 Summary Table

| Bot | Risk/Trade | Win Rate | Avg Win | Avg Loss | Expected Value | Fee Impact | Note |
|-----|-----------|----------|---------|----------|-----------------|-----------|------|
| Chaos Degen | 75% | 40% | +35% | -75% | -7.5% | HIGH VARIANCE |
| Yolo Ape | 80% | 45% | +55% | -50% | +2.5% | MOMENTUM DEPENDENT |
| Bankruptcy Spec | 100% | 20% | +150% | -100% | -40% | ONE WIN PAYS FOR LOSSES |
| Macro Sentinel | 15% | 50% | +12% | -15% | -0.7% | NEED PERFECT SIGNALS |
| Vol Reversion | 20% | 65% | +8% | -25% | -1.8% | NEEDS CLEAR VOL SPIKES |
| Liquidation Vulture | 35% | 55% | +13% | -30% | -5.5% | DATA-DEPENDENT |
| Grid Scalper | 3% | 70% | +0.22% | -0.5% | +0.004% | BARELY PROFITABLE |
| Pair Trader | 12% | 60% | +6% | -7% | +0.8% | NEEDS REAL SHORTS |
| News Reactor | 60% | 35% | +18% | -40% | -12.7% | EXECUTION DEPENDENT |
| Momentum Killer | 50% | 30% | +25% | -50% | -17.5% | HARD TO TIME |

---

## 🎯 Viable Strategies (Expected Value > 0)

Only these should ACTIVELY trade:

1. **Yolo Ape 9000** → Momentum works in crypto (+2.5% expectancy)
2. **Pair Trader** → Correlation reversion works (+0.8% expectancy)
3. **Grid Scalper** → Micro-profits compound (+0.004% expectancy, barely)

**Speculative (needs luck):**
- **Chaos Degen** → All-in reversals (variance play)
- **Bankruptcy Specialist** → Black swan recoveries (waiting for THE trade)

**High-Risk Awaiting Data:**
- **Liquidation Vulture** → Needs real liquidation data
- **News Reactor** → Needs real news feed

**Avoid (negative expectancy):**
- Macro Sentinel (need better signals)
- Vol Reversion (needs vol spike detection)
- Momentum Killer (tops are hard to catch)

---

## Implementation: Only Deploy Positive EV Bots

For Season 4 V2:
- **Yolo Ape 9000:** 80% position momentum plays (EV +2.5%)
- **Pair Trader:** Balanced pair bets (EV +0.8%)
- **Bankruptcy Specialist:** All-in on crashes (EV -40% but high variance)
- **Chaos Degen:** 75% conviction plays (EV -7.5% but short-term rockets)
- **Grid Scalper:** Continuous micro-trading (EV +0.004% but constant volume)

**Rest:** Monitor, wait for better signals, or accept the loss.

---

## Fee Reality Check

**Every strategy must answer:**
1. Does my win % × avg win beat (loss % × avg loss) + fee cost?
2. If my average move is -0.1%, can I afford the 0.976% fee cost?
3. How many trades do I need to break even?

**Breakeven calculation:**
- Win rate × (avg win - fee cost) = Loss rate × avg loss
- If win rate = 55%, avg win = +5%, avg loss = -20%, fee = 1%:
  - 0.55 × (5% - 1%) = 0.45 × 20%
  - 0.55 × 4% = 9%
  - 2.2% ≠ 9% → **NOT VIABLE**

Only trade when the math works.

