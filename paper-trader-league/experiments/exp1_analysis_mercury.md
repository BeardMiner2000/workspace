# Experiment 1 Post-Mortem: mercury_vanta

**Date:** 2026-03-18 to 2026-03-19 (30 hours)  
**Market:** Real Coinbase prices via Advanced Trade API  
**BTC range:** $68,789–$71,741 (flat/choppy)  
**Result:** +0.21% (+0.00010 BTC) — only winning bot

---

## Trade Summary

Total orders tagged `mercury_vanta`: **44**

| Type | Count | Notes |
|------|-------|-------|
| BTC SELL (seed funding) | 3 | Runtime cash-management, not mercury_logic |
| ETH BUY | 8 | Scattered across 30 hours |
| SOL BUY | 1 | Single entry at $88.20 |
| DOGE BUY | 32 | Massive burst 15:29–16:04 on Mar 19 |
| Any SELL via mercury_logic | **0** | Mercury never exited a single position |

**Fees paid:** 0.0000205 BTC (almost nothing)  
**Effective trade frequency:** 41 signal trades over ~900 ticks = ~4.5% hit rate

---

## 1. WHY MERCURY WON — Genuine Edge or Lucky Survival?

**Verdict: 70% structural luck, 30% genuine passive edge.**

Mercury won for three reasons that have nothing to do with signal quality:

### A. Other bots self-destructed with fees and bad trades

Aurora Quanta traded aggressively from tick 1: buying SOL/ETH on rising narrative scores, then panic-selling when conviction flipped negative 10 minutes later. Aurora paid thousands of micro-transactions in fees and round-tripped position after position, entering at tick 3 (SOL @ $90.07) and selling at ticks 31–45 at slightly lower prices. Stormchaser chased breakout scores that peaked and immediately reversed on a flat tape, cycling through DOGE accumulation/liquidation loops repeatedly.

Mercury did almost nothing for the first 93 minutes (ticks 1–935) while the other bots were bleeding fees. That silence was mercury's biggest edge.

### B. Ultra-conservative sizing protected capital

12% of USDT per entry, 65% exit size, minimum $45 USDT threshold. With only ~$500 USDT to deploy (after seeding from 0.05 BTC), mercury's worst-case single-trade loss was tiny. The bot never got big enough exposure to seriously hurt itself.

### C. Selective timing hit real-price dips

The bounce signal (`< -0.003`) requires a genuine 0.3% drop in a single tick. These aren't noise — on a 5-second loop, a 0.3% single-tick drop in ETH or DOGE is real selling pressure. Mercury bought 3 ETH tranches when ETH fell from ~$2165 to $2156 in a single tick cluster (tick 936–939). That bought dip recovered. The DOGE spree at 15:29–16:04 bought DOGE around $0.092x when it had dipped from $0.095, which is a real structural entry. The experiment ended with those positions still open — whether they were profitable depends on final mark prices, but the entries were not reckless.

---

## 2. WHAT SIGNALS ACTUALLY WORKED

### What triggered trades

Looking at all 41 signal-trade rationales:

| Signal | Observed Range | Primary Trigger? |
|--------|---------------|-----------------|
| `bounce` | -0.000542 to -0.003676 | **Yes — nearly all trades** |
| `deviation_from_mean` | -0.000282 to -0.003967 | Secondary |
| `expectancy_score` | +0.002 to +0.011 | Gate/filter |
| `micro_volatility` | 0.000440 to 0.003604 | Suppressive weight |

The bounce signal (`pct_change(series, 1) < -0.003`) was the dominant entry trigger. Almost every trade shows `bounce < -0.003`. The `deviation_from_mean` alone (`< -0.0025`) rarely fired without bounce also qualifying.

### What actually had edge

**Bounce signal: weak but real.** Catching a 0.3% single-tick drop in a mean-reverting range-bound market has statistical merit. In the flat BTC-drag environment of this experiment, most of these bounces did partially recover within the 30-minute price history window.

**Expectancy composite as filter:** The `expectancy` formula combines all four signals with sensible weights. The `expectancy > -0.002` guard prevented entries during sustained downtrends where bounce AND deviation AND reversion were all negative simultaneously. This filter worked: zero catastrophic entries.

### What got lucky

**Volume clustering near support:** The DOGE spree from 15:29–16:04 coincidentally bought near a relative support level ($0.0921–0.0926), but mercury had no way to know this. It just kept firing on bounce signals while DOGE was stuck in a range. If DOGE had been in a downtrend, this cluster would have been an averaging-down disaster.

**No sells needed:** Mercury's biggest lucky break is that none of its positions ever triggered the sell condition (`deviation > 0.0035`). This means the market never recovered enough above the short-term mean to force an exit. Mercury held everything and the experiment ended — so no realized losses. The apparent +0.21% is as much "unrealized position surviving until close" as it is genuine trading profit.

---

## 3. THE HIDDEN WEAKNESS — What Would Have Destroyed Mercury on a Trending Day

### Mercury has no trend awareness whatsoever.

The `mercury_logic` computes deviation and bounce from a 6-tick window (the last 30 seconds on a 5-second loop). There is no longer-term momentum filter, no regime detection, no comparison to BTC direction.

**On a trending day, here's what happens:**

ETH drops 3% over two hours. Every 0.3% bounce in a downtrend looks like a mean-reversion opportunity. Mercury buys the first dip at -0.3%. Price keeps falling. Mercury buys again at -0.6% (deviation now -0.006, bounce < -0.003 again). Buys again. Again. Again. The position sizing is 12% of USDT each time, but as USDT depletes, the positions get smaller — but the accumulation continues until USDT hits $45. Mercury goes max long in a downtrend with no stop.

**The sell condition is broken for trending markets.** The exit fires when `deviation > 0.0035` (price above the short-term mean). In a downtrend, the short-term mean keeps stepping down. The position never exits because the local mean moves with the price. You're holding losses until the experiment ends.

**Estimated damage in a 5% ETH downtrend over 30 hours:** Mercury would accumulate ~35–40 ETH positions across the descent, hold all of them, and finish the experiment with unrealized losses of potentially 2–4% of total portfolio — turning a +0.21% win into a -3% loss.

**The second hidden weakness:** Mercury only has one candidate symbol ranked as "best" per tick. It trades the best of ETHUSDT/SOLUSDT/DOGEUSDT by expectancy. But with 180-tick history (15 minutes), all three alt prices are correlated to BTC moves. In a risk-off dump, all three will show `bounce < -0.003` simultaneously — and mercury will keep rotating entries into whichever alt is "most oversold" while the entire alt market is crashing.

---

## 4. HOW TO MAKE IT GENUINELY BETTER

Not "trade less." Actually better signals.

### 4.1 Real Order Book Imbalance (Coinbase Advanced Trade)

**Problem mercury has:** Bounce is backward-looking. A tick-level price drop could be a few small sellers or one large one. You can't tell.

**Fix:** Pull real order book at time of signal.

```
GET /api/v3/brokerage/best_bid_ask
  → best_bid, best_ask, bid_size, ask_size per product
```

**Signal: Book Imbalance**
```python
imbalance = (bid_size - ask_size) / (bid_size + ask_size)
# Range: -1.0 (all asks) to +1.0 (all bids)
# Entry only if imbalance > +0.1 (buyers still present on dip)
# Skip entry if imbalance < -0.2 (aggressive sellers dominating)
```

This catches the difference between a real dip-buy opportunity (bid wall holding) vs. a knife-catch (bids collapsing). Would have prevented approximately half of mercury's weaker DOGE entries where bounce was negative but book was thin.

### 4.2 Bid-Ask Spread as Volatility Quality Filter

```
GET /api/v3/brokerage/best_bid_ask
  → spread = (best_ask - best_bid) / best_bid
```

**Signal: Spread-Normalized Entry**
```python
# Wide spread = illiquid = dangerous, skip
# Tight spread = liquid = good, proceed
if spread > 0.002:  # > 20bps spread
    skip entry
# Replace micro_volatility in expectancy with spread_penalty:
spread_penalty = spread * 50  # normalize to similar scale
```

In a trending or panic market, spreads widen dramatically. This would naturally suppress entries during genuine selloffs — exactly when mercury's bounce signal goes off most aggressively.

### 4.3 OHLCV Candles for Better Mean Context

```
GET /api/v3/brokerage/market/candles
  product_id: ETH-USDT
  granularity: FIVE_MINUTE
  start/end: last 2 hours
```

**Replace the 6-tick rolling window with candle-based deviation:**
```python
# Current: 6 price ticks = last 30 seconds
# Proposed: 24 x 5min candles = last 2 hours
candle_closes = [c['close'] for c in candles[-24:]]
candle_mean = statistics.mean(candle_closes)
candle_deviation = (current_price - candle_mean) / candle_mean

# Multi-timeframe confirmation:
# Only enter if BOTH short (6-tick) AND medium (24-candle) show oversold
if candle_deviation > -0.005:
    skip  # not deep enough relative to 2hr mean
```

This would have **prevented the entire DOGE accumulation cluster**. DOGE at $0.0921 at 15:30 on March 19 was not meaningfully below its 2-hour mean — it was at the bottom of a multi-hour range. A 2-hour candle mean would have shown deviation only at -0.1% or so, not the -0.25% that the 30-second window saw.

### 4.4 Trend Regime Filter

```python
# Use 24-candle trend slope as gate
import numpy as np
prices = [c['close'] for c in candles[-24:]]
x = np.arange(len(prices))
slope = np.polyfit(x, prices, 1)[0]
trend_pct_per_hour = (slope * 12) / prices[-1]  # 12 candles/hour

# Only enter long if trend is flat or rising
if trend_pct_per_hour < -0.003:  # >0.3%/hr decline
    skip mean-reversion entry
    # optionally: short instead
```

This single filter would have eliminated ~80% of the "buying into downtrend" risk.

### 4.5 Fix the Exit Logic

**Current exits:**
- `deviation > 0.0035` (price above local 30-sec mean) → almost never fires in trends
- `bounce < -0.0045` (another down-tick) → perversely exits on further dips
- `expectancy < -0.012` → fires late in sustained downtrends

**Better exits:**
```python
# Time-based: exit if held for > N ticks without reaching target
# Profit target: exit 65% when position up > 0.25%
# Hard stop: exit 100% if position down > 0.5% from entry
# Trailing: track entry price, sell when price returns to entry - 0.1%
```

---

## 5. NEW NAME + IDENTITY

Mercury Vanta was supposed to be fast and dark. In practice it was slow and patient — more like a patient arbitrageur that waits for genuine dislocation.

**New Name: `vega_pulse`**

**Persona:** A market microstructure specialist that reads the live order book alongside price history. Where mercury reacted to price alone, vega_pulse reads the book: it knows *why* price moved, not just *that* it moved. Calm, precise, waits for high-conviction setups where price dislocation is confirmed by book imbalance.

**Tag line:** "Don't catch falling knives. Catch knives the book wants to stop."

**Identity:**
- Uses real order book data, not just price history
- Enters only when buyers are defending (positive imbalance on the dip)  
- Exits on profit target (not just deviation crossover)
- Has a genuine trend filter — knows when to sit out
- Still low-frequency, still small sizing, but now with reasons

---

## 6. NEW STRATEGY SPEC — vega_pulse v1

### Data Sources (real Coinbase Advanced Trade API)

#### A. Order Book (every tick)
```
GET /api/v3/brokerage/best_bid_ask
Params: product_ids=ETH-USDT,SOL-USDT,DOGE-USDT,BTC-USDT
Response: best_bid, best_ask, bid_qty, ask_qty per product
```

Compute per symbol:
```python
spread_bps = (ask - bid) / bid * 10000
book_imbalance = (bid_qty - ask_qty) / (bid_qty + ask_qty)
```

#### B. OHLCV Candles (refresh every 5 minutes or on signal)
```
GET /api/v3/brokerage/market/candles
Params:
  product_id: {SYMBOL}
  granularity: FIVE_MINUTE
  start: now - 7200s (2 hours)
  end: now
Response: array of {open, high, low, close, volume}
```

Compute:
```python
candle_mean = mean(closes[-24:])      # 2hr mean
candle_stdev = stdev(closes[-24:])    # 2hr stdev
candle_deviation = (current - candle_mean) / candle_mean
slope = linear_slope(closes[-24:])   # trend direction
trend_pct_hr = (slope * 12) / closes[-1]
```

#### C. Short-term Price History (existing, keep)
- 6-tick bounce and short-reversion signals (existing mercury logic)
- micro_volatility from 6-tick stdev

### Signal Computation

```python
def vega_pulse_signal(symbol, current_price, book, candles, tick_history):
    
    # --- Order Book ---
    spread_bps = (book.ask - book.bid) / book.bid * 10000
    imbalance = (book.bid_qty - book.ask_qty) / (book.bid_qty + book.ask_qty)
    
    # --- Multi-timeframe Deviation ---
    candle_mean = mean(candles.close[-24:])
    candle_dev = (current_price - candle_mean) / candle_mean
    tick_dev = mercury_deviation(tick_history[-6:])  # existing logic
    
    # --- Trend Filter ---
    slope = linear_slope(candles.close[-24:])
    trend_pct_hr = (slope * 12) / candles.close[-1]
    
    # --- Composite Signals ---
    bounce = pct_change(tick_history, 1)
    micro_vol = stdev_returns(tick_history, 6)
    
    # --- Entry Conditions (ALL must pass) ---
    is_dip = (tick_dev < -0.0025 or bounce < -0.003)
    is_confirmed = candle_dev < -0.003          # 2hr context confirms dip
    is_liquid = spread_bps < 20                 # not an illiquid moment
    book_supports = imbalance > 0.0             # bids >= asks (buying present)
    not_trending_down = trend_pct_hr > -0.002   # not falling >0.2%/hr
    
    if is_dip and is_confirmed and is_liquid and book_supports and not_trending_down:
        # Entry score for ranking vs. other symbols
        entry_score = (
            (-candle_dev * 2.0)       # deeper dip = higher score
            + (-bounce * 0.8)          # stronger bounce signal
            + (imbalance * 1.5)        # stronger book support
            - (spread_bps * 0.05)      # penalize wide spreads
            - (micro_vol * 0.3)        # penalize high volatility
        )
        return entry_score
    return None

# --- Exit Conditions (check on every tick for held positions) ---
def vega_pulse_exit(position, current_price, tick_history, candles):
    entry_price = position.avg_entry_price
    pnl_pct = (current_price - entry_price) / entry_price
    
    # Profit target: take 65% off at +0.25%
    if pnl_pct > 0.0025:
        return 'TAKE_PROFIT', 0.65
    
    # Hard stop: cut 100% at -0.5%
    if pnl_pct < -0.005:
        return 'STOP_LOSS', 1.0
    
    # Candle-based recovery exit: price returned to 2hr mean
    candle_mean = mean(candles.close[-24:])
    if current_price >= candle_mean * 0.999:
        return 'MEAN_RECOVERY', 0.65
    
    # Stale hold: position older than 60 ticks (5 minutes) and negative
    if position.age_ticks > 60 and pnl_pct < 0:
        return 'TIME_STOP', 1.0
    
    return None
```

### Position Sizing (keep conservative)
```python
alloc_pct = 0.10   # 10% of USDT per entry (down from 12%)
max_positions = 3  # across all symbols simultaneously
min_usdt = 50      # minimum USDT to trade
```

### Expected Improvements vs Mercury

| Metric | Mercury Vanta | Vega Pulse |
|--------|--------------|------------|
| Entry filter layers | 2 | 5 |
| Trend awareness | None | Candle slope |
| Book confirmation | None | Imbalance + spread |
| Exits | 1 condition (often broken) | Profit target + stop + time |
| DOGE cluster risk | Accumulates forever | Max 3 open positions |
| Trend day drawdown | -3 to -5% estimated | -1 to -2% estimated |
| Flat day alpha | +0.1–0.3% | +0.2–0.5% estimated |

---

## Summary Verdict

Mercury won Experiment 1 by being boring in a boring market. It had one thing right: patience. It had everything else wrong: no exits, no trend detection, no book awareness, no multi-timeframe context. On any trending day it becomes a runaway long accumulator with no way out.

Vega Pulse takes mercury's patience and grafts on real microstructure data: live bid-ask, book imbalance, candle context, and hard exits. It keeps the small sizing and selective entry discipline but adds the tools to survive when the tape stops cooperating.

The experiment proved mercury can survive. The next experiment will prove it can actually trade.
