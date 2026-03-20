# Experiment 1 Post-Mortem: aurora_quanta
**Date:** 2026-03-19 | **Analyst:** Neon Cortex

---

## Executive Summary

aurora_quanta lost **35.5% of starting capital** (0.01775 BTC) in 30 hours, with **24% eaten by fees alone** (0.01200 BTC). The loss was not primarily a market timing failure — it was a **mechanical self-destruction**: a synthetic sine wave oscillator drove the bot into a relentless buy-sell cascade, generating 9,500+ trades at 3 bps each while the actual market barely moved.

---

## 1. ROOT CAUSE OF LOSSES

### 1a. The Sine Wave Trap

The `narrative_score` — the *primary* buy/sell trigger — is not a market signal. It's a mathematical oscillator:

```python
narrative_score = 0.65 * sin(tick / 8) + 0.35 * sin(tick / 21)
```

With a 5-second loop, the dominant cycle (period=8) completes in **40 seconds**. The combined waveform completes one full oscillation roughly every **3–7 minutes**. The bot was designed as a swing trader meant to respond to macro regime changes — but its primary signal changed direction every few minutes.

**Buy threshold**: `conviction > 0.035 AND narrative_score > -0.15`  
**Sell threshold**: `conviction < -0.01 OR narrative_score < -0.55`

The narrative_score alone is sufficient to trigger both buys and sells. It oscillates between approximately +1.0 and -1.0, crossing these thresholds multiple times per hour.

### 1b. The Cascade Liquidation Pattern

This is the most catastrophic code bug. Each sell trigger disposes of only **55% of holdings**:

```python
self.place_order(state.bot_id, symbol, 'SELL', held_qty * Decimal('0.55'), ...)
```

But the sell condition remains true for many consecutive ticks while the sine wave descends. The result is **a series of 10–20 sell orders per exit cycle**, geometrically decaying in size:

```
Tick 31: SELL 10.23 SOL  (55% of 18.6 SOL)
Tick 32: SELL  4.61 SOL  (55% of 8.39 SOL)
Tick 33: SELL  2.07 SOL
Tick 34: SELL  0.93 SOL
Tick 35: SELL  0.42 SOL
Tick 36: SELL  0.19 SOL
Tick 37: SELL  0.085 SOL
Tick 38: SELL  0.038 SOL
Tick 39: SELL  0.017 SOL
Tick 40: SELL  0.0077 SOL
Tick 41: SELL  0.0035 SOL
Tick 42: SELL  0.0016 SOL
... (continues until dust)
```

**Every single one of these micro-sells incurs a 3 bps fee.** The fee is the same whether you're selling $800 worth of SOL or $0.001 worth. This turns a single "exit decision" into a fee-harvesting machine with 15+ individual transactions.

### 1c. The Cascade Accumulation Pattern

The same pattern applies on entry. When the buy condition is satisfied, the bot buys **42% of available USDT** each tick:

```python
alloc = min(usdt * Decimal('0.42'), usdt)
qty = alloc / price
```

With USDT available at each tick:
```
Tick 3:  BUY 42% of USDT → USDT drops to 58%
Tick 4:  BUY 42% of 58% = 24.4% of original
Tick 5:  BUY 42% of 33.6% = 14.1%
Tick 6:  BUY 42% of 19.5% = 8.2%
... (10+ buys to deploy capital)
```

Each tick fires a fresh market order. Again, each order = a fee event.

### 1d. Cycle Frequency Math

At 5 seconds/tick:
- **Buy phase duration**: ~8–12 ticks = 40–60 seconds of cascading buys
- **Sell phase duration**: ~12–20 ticks = 60–100 seconds of cascading sells  
- **Cycle period**: ~50–80 ticks = ~4–7 minutes per full buy+sell cycle

Over 30 hours (21,600 ticks):
- ~300–450 full oscillation cycles
- ~20–25 orders per cycle
- **Estimated aurora_quanta orders: 6,000–11,000** ✓ (actual: ~6,000–7,000 of the 9,582 total)

### 1e. The maybe_fund_trading_cash Drain

A separate mechanism sells 28% of aurora's BTC when USDT < $120:

```python
if bot_id == 'aurora_quanta':
    fraction = Decimal('0.28')
```

This triggers frequently because the cascade buying depletes USDT quickly. Each trigger = another BTC sell order = another fee + erosion of the BTC base. Observed in the CSV: BTC funding sells at ticks 1, 7, 12, 16, 20, 56, 59, etc.

### 1f. No Stop-Loss, No Position Sizing by Conviction

- **Conviction 0.036** (barely above threshold) gets the same 42% allocation as **conviction 0.15**
- There is no stop-loss mechanism — a losing position cycles indefinitely
- The sell trigger (`conviction < -0.01`) fires on even tiny negative signals, immediately beginning the cascade

---

## 2. WHAT WORKED

### 2a. The Conviction Formula Has Real Components

The formula includes genuine market signals:
```python
conviction = rel * 1.8 + long_mom * 1.3 + narrative_score * 0.18 - vol * 1.2
```

`rel` (relative strength vs BTC) and `long_mom` (12-tick price momentum) are derived from **actual Coinbase prices**. In isolation, these would form a reasonable relative-momentum signal. The problem is that `narrative_score * 0.18` poisons the formula and the sell threshold is nearly met by narrative_score alone.

### 2b. Symbol Selection Was Reasonable

Aurora chose between ETH and SOL based on relative strength vs BTC — a sound macro approach. The bot correctly identified the stronger performer each cycle.

### 2c. Some Individual Round-Trips Were Profitable

When the bot happened to buy into a micro-rally and sell at a higher price within the same cycle (e.g., buying SOL at $90.05 and selling at $90.23), individual round-trips could be slightly profitable before fees. Unfortunately, the fee load (~3 bps × 2 sides = 6 bps per round trip) consumed any micro-profit.

### 2d. Volatility Penalization Works

The `-vol * 1.2` term in conviction correctly penalizes high-volatility assets. During the experiment, this appropriately reduced conviction during turbulent periods.

---

## 3. UNEXPECTED MARKET CONDITIONS

### 3a. A Genuinely Flat, Choppy Market

The BTC range was only **+4.3%** ($68,789–$71,741) over 30 hours — an unusually tight, directionless session. Aurora's synthetic signals assumed trending behavior that would "confirm" the sine wave's direction. Instead:

- **Real prices drifted sideways-to-down**: ETH opened ~$2,200, ended ~$2,137–$2,145 (≈-2.5%)
- **SOL opened ~$90.10, ended ~$88.87–$89.25** (≈-1.4%)
- **BTC drifted slightly down** from $71,600 to the high-$68,000s range during the session

The synthetic signals had no way to detect or respect this regime. They oscillated regardless of what the market did.

### 3b. Synthetic Prices Diverged from Real Prices

In `fetch_live_marks()`, real Coinbase prices populate `self.state` and `self.history`, but the narrative/event scores are still calculated from the tick counter — completely decoupled from real price action. The market's actual momentum signal had no pathway into the buy/sell decision.

### 3c. Micro-Flat Price Action Maximized Fee Damage

In a trending market, a fast directional bot can stay in a winning position for extended periods, amortizing fees over a large gain. In a choppy market, every flip incurs fees with no directional profit to show for it. Aurora was designed for trend/macro conditions but ran in precisely the worst environment for its actual behavior.

### 3d. SOL and ETH Moved Slightly Below BTC

The relative strength calculation (`pct_change(history[symbol], 6) - btc_mom`) would have returned weakly negative values for most of the session, partially suppressing conviction. This meant the bot was often trading near the threshold — borderline signals that fired unpredictably and created more oscillation.

---

## 4. SPECIFIC CODE CHANGES FOR EXPERIMENT 2

### Fix 1: ELIMINATE the synthetic narrative_score from trading decisions
```python
# REMOVE from aurora_logic:
conviction = rel * 1.8 + long_mom * 1.3 + state.narrative_score * 0.18 - vol * 1.2
strong = conviction > 0.035 and state.narrative_score > -0.15
weak = conviction < -0.01 or state.narrative_score < -0.55

# REPLACE WITH real signals only:
conviction = rel * 2.0 + long_mom * 1.5 + rsi_signal * 0.3 - vol * 1.2
strong = conviction > 0.06   # higher bar without synthetic noise
weak = conviction < -0.04    # also higher bar
```

### Fix 2: Add a minimum hold time (cooldown)
```python
# Add to BotState or runtime state dict:
self.last_trade_time = {}  # bot_id -> timestamp

# Before any order:
now = time.time()
last = self.last_trade_time.get(state.bot_id, 0)
if now - last < 1800:  # 30-minute minimum between entry/exit
    return
self.last_trade_time[state.bot_id] = now
```

### Fix 3: Replace cascade sell with a SINGLE full exit
```python
# REMOVE the 55% partial sell (causes cascade)
# REPLACE WITH:
self.place_order(state.bot_id, symbol, 'SELL', held_qty, ...)  # full exit, one order
```

### Fix 4: Scale position size by conviction strength
```python
# REMOVE flat 42% allocation:
# alloc = min(usdt * Decimal('0.42'), usdt)

# REPLACE WITH conviction-scaled sizing:
conviction_pct = min(conviction / 0.20, 1.0)  # max out at conviction=0.20
alloc_pct = Decimal(str(0.10 + conviction_pct * 0.20))  # 10%-30% range
alloc = usdt * alloc_pct
```

### Fix 5: Add a hard stop-loss
```python
# Track entry price per symbol:
self.entry_prices = {}  # (bot_id, symbol) -> Decimal

# After buy, record entry:
self.entry_prices[(state.bot_id, symbol)] = price

# In logic, check stop:
entry = self.entry_prices.get((state.bot_id, symbol))
if entry and held_qty > ZERO:
    drawdown = float((price - entry) / entry)
    if drawdown < -0.025:  # 2.5% stop-loss
        self.place_order(state.bot_id, symbol, 'SELL', held_qty, 
                        {'exit_reason': 'stop_loss', 'drawdown': drawdown})
        return
```

### Fix 6: Replace maybe_fund_trading_cash with a less aggressive version
```python
# Reduce aurora's BTC sell fraction:
fraction = Decimal('0.10')  # was 0.28 — too aggressive
# And raise the USDT floor:
if usdt >= Decimal('200') or btc <= Decimal('0.005'):  # was $120 / 0.0025
    return False
```

### Fix 7: Add RSI signal computation (real signal)
```python
def compute_rsi(self, series: list[Decimal], period: int = 14) -> float:
    if len(series) < period + 1:
        return 50.0
    values = [float(x) for x in series[-(period+1):]  ]
    gains, losses = [], []
    for i in range(1, len(values)):
        delta = values[i] - values[i-1]
        gains.append(max(delta, 0))
        losses.append(max(-delta, 0))
    avg_gain = sum(gains) / period
    avg_loss = sum(losses) / period
    if avg_loss == 0:
        return 100.0
    rs = avg_gain / avg_loss
    return 100.0 - (100.0 / (1.0 + rs))

# Then in logic:
rsi = self.compute_rsi(state.history[symbol], 14)
rsi_signal = (50.0 - rsi) / 50.0  # negative when overbought, positive when oversold
```

---

## 5. NEW NAME + IDENTITY FOR EXPERIMENT 2

### Retiring: aurora_quanta
Aurora was a creature of synthetic light — a sine wave bot pretending to be a macro trader. It traded its own hallucinations. Time to put it down.

### Introducing: **solstice_drift**

**Persona**: A patient, deliberate trend-follower. Where aurora was frantic and synthetic, solstice_drift is slow and empirical. It waits. It watches real price structure. It enters only when multiple real signals align, and it exits in a single clean move — not a 20-order cascade. Its name reflects what it actually does: catch drifts around meaningful turning points, like a market's solstice — the moment momentum genuinely shifts.

**Character**: Cautious optimist. Prefers quality over frequency. Would rather sit in cash for hours than take a bad trade. Doesn't care about being busy. Cares about being right.

**Symbol**: 🌅

---

## 6. PROPOSED STRATEGY SPEC FOR EXPERIMENT 2

### Bot Identity
- **Name**: `solstice_drift`
- **Strategy ID**: `solstice_drift_momentum_v1`

### Signal Sources (REAL only, from Coinbase API)
| Signal | Source | Calculation |
|--------|--------|-------------|
| RSI | Real price history | 14-period RSI on the 5-second tick history |
| Relative Strength | Real prices | 12-tick pct_change(symbol) - pct_change(BTC) |
| Trend Momentum | Real prices | 30-tick pct_change (10-minute lookback) |
| Volatility | Real prices | stdev_returns(24) — 2-minute rolling vol |
| BTC Regime | Real BTC price | 60-tick BTC momentum — buy alts only if BTC not crashing |

No synthetic signals. No event_score. No narrative_score.

### Entry Logic
```
conviction = (rel_strength * 2.0) + (trend_30tick * 1.5) + (rsi_signal * 0.5) - (vol * 1.5) + (btc_filter * 0.3)

BUY when:
  - conviction > 0.08  (higher bar than aurora's 0.035)
  - RSI < 60  (not overbought)
  - BTC 60-tick momentum > -0.005  (BTC not in freefall)
  - No position currently held
  - Cooldown: 30 minutes since last trade
```

### Position Sizing
- Base allocation: **15% of USDT** at minimum conviction
- Scale up to **30% of USDT** at high conviction (conviction > 0.15)
- Maximum single position: **35% of total portfolio value**
- Never deploy more than 50% of available USDT at once

### Exit Logic
Single-order exit (NO cascades):
```
SELL 100% of position when ANY of:
  - conviction < -0.05 (clear negative signal)
  - RSI > 70 (overbought, take profit)
  - Stop-loss: price < entry_price * 0.975  (2.5% hard stop)
  - Take-profit: price > entry_price * 1.04  (4% profit target)
  - Max hold time: 4 hours (time-based exit)
```

### Trade Frequency Target
- **Target**: 5–15 trades per day (vs aurora's 320/hour)
- **Cooldown enforcement**: Hard 30-minute lock between trades
- **Expected fee cost**: ~0.00020 BTC/day (vs aurora's 0.00400/day)

### BTC Reserve Management
- Only fund USDT from BTC if USDT < $200 AND BTC balance > 0.010 BTC
- Maximum BTC sell: 10% of BTC balance (vs aurora's 28%)
- Do not sell BTC if BTC momentum is strongly positive (hold the asset)

### Symbol Universe
- **Primary candidates**: ETHUSDT, SOLUSDT (same as aurora)
- **Selection method**: Same relative-strength ranking (real momentum only)
- **Exclusion rule**: Do not trade any symbol with 2-minute volatility > 1.5% (too choppy)

### Risk Limits
- Max drawdown from starting capital: **15%** → halt trading
- Max single-trade loss: **2.5%** → stop-loss
- Fee budget per day: **0.0005 BTC** → if exceeded, pause for rest of day

---

## 7. SUMMARY TABLE

| Dimension | aurora_quanta (Exp 1) | solstice_drift (Exp 2 plan) |
|-----------|----------------------|----------------------------|
| Primary signal | Synthetic sine wave | Real RSI + momentum |
| Trade frequency | ~320/hour | ~0.5/hour |
| Position exit | 55% cascade (10-20 orders) | 100% single order |
| Stop-loss | None | 2.5% hard stop |
| Position sizing | Flat 42% USDT | 15-30% by conviction |
| Cooldown | None | 30 minutes |
| Fee cost (30hr) | 0.01200 BTC (24%) | ~0.0005 BTC (~1%) |
| BTC sell aggressiveness | 28% per trigger | 10% per trigger |

---

## Closing Note

aurora_quanta's failure was almost entirely self-inflicted. The market was mild — a 4.3% BTC range in 30 hours is not a crisis. But the bot treated its own oscillating math as reality, chasing signals that had nothing to do with what was actually happening on Coinbase. The result was a fee-generating machine that systematically transferred capital to the exchange.

solstice_drift must be the opposite: patient, empirical, and above all, **slow**. In choppy markets, the bot that trades least wins. The edge in experiment 2 isn't cleverness — it's restraint.

---
*Generated from analysis of exp1_orders.csv (12,287 rows), exp1_market_marks.csv (69,078 rows), and services/data_ingest/src/main.py*
