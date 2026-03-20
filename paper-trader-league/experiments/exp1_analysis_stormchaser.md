# Experiment 1 Post-Mortem: stormchaser_delta

**Date:** 2026-03-19  
**Duration:** ~30 hours (2026-03-18 18:36 UTC → 2026-03-20 00:32 UTC)  
**Result:** -90.6% | 0.05 BTC → 0.00472 BTC  
**Market:** BTC $68,789–$71,741 (flat/choppy, ~3% range)

---

## Executive Summary

stormchaser_delta was supposed to be a fast event-driven momentum chaser. It became a hyper-active noise-follower that bought synthetic breakouts 2,295 times and exited only 320 times, systematically destroying capital through fee drag, adverse execution spread, and a buy:sell signal asymmetry of nearly 14:1. Short-selling was bolted on but critically broken by a single-symbol cover bug. The result was near-total wipeout in 30 hours of a flat market.

---

## 1. ROOT CAUSE: The Near-Wipeout

### 1A. The Synthetic Oscillator Was the Real Signal (and It Was Garbage)

The `event_score` is a synthetic sine wave computed as:
```python
pulse = math.sin(phase / 5)
event_raw = 0.55 * pulse + random.uniform(-0.2, 0.2)
# occasional spike at phase % 17 == 0
event_score = clamp(event_raw, -2.0, 2.0)
```

This oscillator has **no connection to real market data**. When real Coinbase prices were used, the bot kept computing narrative/event scores from a tick counter — a synthetic clock running independently of price action. This means:

- In a flat real market (BTC range: $68,789–$71,741), actual price momentum (`fast`, `burst`) was essentially zero.
- The breakout formula — `fast*2.4 + burst*1.1 + event_score*0.15 + vol*0.8` — was dominated by `event_score`.
- When `event_score > 0.333`, the oscillator alone pushed breakout score above the 0.05 buy threshold.
- Simulation of 18,000 ticks confirms: **29.3% of all ticks would trigger a BUY signal from the oscillator alone**, regardless of actual market conditions.

This produced 2,295 buys over 30 hours — roughly **1.27 buys per minute continuously**.

### 1B. Asymmetric Entry/Exit Thresholds (13.9:1 Buy:Sell Ratio)

The exit requires `fast < -0.018` OR `event_score < -0.8`.

- `fast < -0.018` = a 1.8% price drop in 2 ticks (10 seconds) — essentially never in a flat market.
- `event_score < -0.8` occurs only **2.11% of ticks** (380/18,000 simulated).

**Buy:Sell trigger ratio: 5,282 buy ticks vs 380 sell ticks = 13.9:1.**

The bot accumulated positions aggressively but exited reluctantly. At every tick with a positive oscillator pulse, it committed 18% of remaining USDT to a buy. By the time the sell signal fired, prices had already reverted (the oscillator high = price was locally bid up; sell came after reversion).

### 1C. Buy-High / Sell-Low Execution Pattern

Across all symbols, executed buys averaged *above* executed sells:

| Symbol | Avg Buy Price | Avg Sell Price | Spread |
|--------|--------------|----------------|--------|
| DOGEUSDT | 0.094420 | 0.094124 | **-0.31%** |
| ETHUSDT | 2,176.01 | 2,166.37 | **-0.44%** |
| SOLUSDT | 89.59 | 89.31 | **-0.31%** |

The bot bought when the oscillator peaked (inflated momentum reading = locally high price) and sold after the oscillator dropped (price had reverted). Each round-trip destroyed ~0.3–0.44% of capital **before fees**.

### 1D. Fee Death Spiral

- Total fees paid: **0.00204 BTC** (4.08% of starting capital)
- Average fee per trade: 0.00000077 BTC
- 2,655 trades at 5-second intervals = continuous fee bleed

### 1E. The BTC Cash Funding Loop — A Vicious Cycle

`maybe_fund_trading_cash()` fires whenever USDT < 120 AND BTC > 0.0025, selling **18% of remaining BTC** to refuel USDT for more alt bets. This ran **16 times**, draining a total of **0.04791 BTC** — **95.8% of the starting BTC reserve** — just to fund more losing alt trades.

The sequence:
1. Bot buys alts aggressively → USDT depletes
2. Cash funding triggers → sells BTC to get USDT
3. USDT goes toward more alt buys → more losses → USDT depletes again
4. Repeat until BTC is gone

The bot systematically liquidated its reserve asset to fund its own losses.

### 1F. 83.8% of Buys Were "Marginal Breakouts" (Score 0.05–0.10)

Of 2,295 buys:
- **83.8%** had breakout score between 0.05–0.10 (barely above threshold, low confidence)
- **95.2%** had `fast_momentum` < 0.001 (0.1% — essentially flat price action)
- Only **3.8%** had breakout score > 0.20 (genuinely strong signal)

The bot was trading noise 96% of the time.

---

## 2. WHY SHORT-SELLING DIDN'T HELP

### 2A. Impossibly Tight Combined Threshold

Short entry requires ALL of:
```python
score < -0.05 AND event_score < -0.8 AND usdt >= 100 AND short_qty == ZERO
```

- `event_score < -0.8` is a **2.11% condition** by itself.
- For `score < -0.05` in a flat market where fast/burst ≈ 0, you need `event_score * 0.15 < -0.05` → `event_score < -0.333`.
- Combined with the stricter -0.8 floor: shorts fired only when the oscillator was in its deepest negative phase *and* USDT was still above $100.
- Result: only **35 shorts placed in 30 hours** — averaging 1.17 per hour, vs 1.27 buys per minute on the long side.

### 2B. Critical Bug: Cover Only Checks the Top-Ranked Symbol

The `storm_logic` method selects `symbol = ranked[0]` (the single highest-scoring symbol at that tick), then checks `short_qty = self.holdings_short_qty(balances, symbol)`. Cover, short, buy, and sell all operate on this ONE symbol.

**If ETH has an open short but SOL scores highest, the ETH short is permanently ignored.**

Evidence from the data:
- SOLUSDT: **10 shorts opened, 0 covers** — SOL was never top-ranked after its short was placed
- ETHUSDT: 17 shorts, 3 covers
- DOGEUSDT: 8 shorts, 2 covers

The cover logic effectively existed for only the one symbol that happened to be ranked #1 at cover time. Every short on a non-top-ranked symbol was **stuck open until experiment end**.

### 2C. Cover Threshold Too Easy to Trigger — Wrong Direction

The cover fires on `fast > 0.018 OR event_score > 0.6`. With a 29%-trigger oscillator, `event_score > 0.6` fires frequently. The 5 covers that DID happen were triggered by the oscillator swinging positive — not by actual price reversal covering the short at profit. 

Worse: if a short is profitable (price falling), the oscillator will eventually cycle back positive and **prematurely cover** the position before it's run its course.

### 2D. Short Position Sizing Was Too Small (20% of USDT)

Long entries used 18–30% of USDT per trade, meaning the bot rapidly built large long exposure. Short entries used only 20% of USDT *total* (not per trade), while longs could stack repeatedly. The asymmetry meant shorts couldn't offset accumulated long losses even if they worked perfectly.

### 2E. Shorts Arrived Too Late (11 Hours In)

First SHORT appeared at 2026-03-19 05:29 UTC — over 11 hours into the experiment. By then, the account had already lost the majority of its value on the long side. There wasn't enough capital left for shorts to meaningfully contribute.

---

## 3. WHAT WORKED (Limited)

### 3A. Sell Exit Logic Had Some Validity

The 320 sells that DID occur used `fast < -0.018 OR event_score < -0.8` — a strict threshold that at least required a real negative signal. These weren't random. The bot was better at exiting than at entering; the problem was it exited 10x less often than it entered.

### 3B. Strong Breakout Signals (Top 3.8%) Had Directional Edge

The 87 buys with breakout score > 0.20 were triggered by combinations of real price momentum *plus* oscillator boost. These likely had genuine short-term edge but were drowned in noise from the other 2,208 trades.

### 3C. Symbol Selection From Multi-Asset Ranking

The candidate ranking logic (SOLUSDT, DOGEUSDT, ETHUSDT scored against each other, picking highest) is mechanically sound. In a trend environment, this rotation toward the strongest mover would be valuable. The problem is what's being ranked — a synthetic signal rather than real edge.

### 3D. Cover Logic Was Theoretically Correct in Concept

The idea of covering shorts when momentum reverses (`fast > 0.018`) is correct directional logic. If the symbol bug were fixed and the trigger applied to ALL open short symbols, it would be a reasonable stop mechanism.

---

## 4. SPECIFIC CODE CHANGES FOR EXPERIMENT 2

### Fix 1: Loop Over All Symbols for Cover/Short Management

```python
# CURRENT (broken): only processes ranked[0]
score, symbol, fast, burst, vol = ranked[0]
short_qty = self.holdings_short_qty(balances, symbol)
if short_qty > ZERO and (fast > 0.018 or state.event_score > 0.6):
    self.place_order(..., 'COVER', ...)

# FIXED: check ALL symbols for existing shorts first
for sym_candidate in candidates:
    sq = self.holdings_short_qty(balances, sym_candidate)
    if sq > ZERO:
        sym_fast = self.pct_change(state.history[sym_candidate], 2)
        # Use real cover condition: momentum reversal
        if sym_fast > 0.005 or self.pct_change(state.history[sym_candidate], 4) > 0.003:
            self.place_order(state.bot_id, sym_candidate, 'COVER', sq, {...})
        # Hard stop: cover if short has been open too long (e.g., 30 ticks = 2.5 min)
        # (requires tracking short entry tick in state)
```

### Fix 2: Remove the Synthetic event_score as a Signal

```python
# REMOVE from storm_logic:
# - breakout += event_score * 0.15
# - short condition: event_score < -0.8
# - buy condition using event_score anywhere

# REPLACE with real signals (see Section 6)
```

### Fix 3: Fix Entry/Exit Asymmetry

```python
# CURRENT: 18% of USDT per buy, exits only 80% of position
# PROBLEM: buys stack, sells only trim
# FIX: 
aggress = Decimal('0.10')  # reduce from 0.18 to 0.10
# Add max position limit:
if held_qty * price > usdt * Decimal('0.5'):  # don't let position exceed 50% of total USDT equivalent
    return  # skip buy if already overweight
```

### Fix 4: Raise Buy Threshold to Filter Noise

```python
# CURRENT: score > 0.05 (trivially easy)
# FIX: score > 0.15 (requires meaningful combined signal)
if score > 0.15 and usdt > Decimal('70') and short_qty == ZERO:
```

### Fix 5: Tighten Short Entry — Remove event_score dependency

```python
# CURRENT: score < -0.05 AND event_score < -0.8
# FIX: use real bearish signal (see Section 6)
# Minimum: use price action only:
if score < -0.10 and vol > 0.002 and usdt >= Decimal('100') and short_qty == ZERO:
```

### Fix 6: Kill the Cash Funding Loop (or Make It Conditional)

```python
# CURRENT: maybe_fund_trading_cash() REPLACES storm_logic on trigger
# FIX: Never auto-liquidate BTC to fund alt losses
# Option A: disable for stormchaser entirely
# Option B: only fund if account PnL is positive (not when losing)
def maybe_fund_trading_cash(self, state: BotState) -> bool:
    if state.bot_id == 'stormchaser_delta':
        return False  # Stormchaser uses BTC as reserve, no auto-liquidation
```

### Fix 7: Add Trade Cooldown (No Back-to-Back Buys)

```python
# Track last trade tick per symbol
# Only buy if last_buy_tick[symbol] < current_tick - 12  (60 seconds minimum between buys)
```

---

## 5. NEW NAME + IDENTITY

**Bot Name:** `obsidian_flux`

**Persona:** A cold-blooded liquidity predator. No mood, no momentum chasing, no news theater. It watches order book pressure and volume patterns to detect genuine institutional flows — then positions ahead of them with surgical patience. Where stormchaser was a golden retriever chasing its own tail, obsidian_flux is a hawk on a thermal waiting for prey to commit.

**Motto:** *"Don't trade the tick. Trade the intention."*

**Strategy Identity:** Order-Flow Asymmetry Reader. It reads the real Coinbase order book for imbalance and trades only when the pressure differential suggests a directional commitment from larger participants.

---

## 6. NEW STRATEGY SPEC: obsidian_flux

### Core Philosophy

Replace all synthetic signals with real signals available from the Coinbase Advanced Trade API. Focus on **3 quantifiable edges** that have documented academic and practitioner evidence:

1. **Order book imbalance** — real-time buy vs. sell pressure at the top of book
2. **Volume-weighted momentum** — price change confirmed by volume (not just price)
3. **Bid-ask spread dynamics** — widening spread = uncertainty/accumulation; tightening = resolution

### Real Signals to Implement

#### Signal 1: Order Book Imbalance (OBI)

**API:** `GET /api/v3/brokerage/product_book?product_id=ETH-USD&limit=10`

Returns bids/asks with size at each level. Compute:
```
bid_pressure = sum(size for top 5 bid levels)
ask_pressure = sum(size for top 5 ask levels)
OBI = (bid_pressure - ask_pressure) / (bid_pressure + ask_pressure)
# Range: -1.0 (pure selling) to +1.0 (pure buying)
```

**Edge:** OBI > +0.30 with increasing bid depth = institutional accumulation signal. OBI < -0.30 = distribution. This is a **leading indicator** unlike price momentum which is lagging.

**Threshold for entry:** OBI > 0.25 sustained across 3 consecutive ticks (15 seconds).

#### Signal 2: Volume-Confirmed Momentum (VCM)

**API:** Use `GET /api/v3/brokerage/products/{product_id}/candles?granularity=ONE_MINUTE`

Compute 1-minute candle data:
```
price_change_5m = (close_t - close_{t-5}) / close_{t-5}
volume_ratio = volume_t / avg_volume_20m  # current vs avg
VCM = price_change_5m * volume_ratio
# Strong signal: price_change > 0.3% WITH volume_ratio > 1.5x
```

**Edge:** Price moves on high volume are self-reinforcing (large participants confirming direction). Price moves on low volume revert. The synthetic oscillator had zero volume component — this fixes the core problem.

**Threshold:** `VCM > 0.004` (0.4% move on 1.5x normal volume) for long entry.

#### Signal 3: Bid-Ask Spread Compression

**API:** From product book data above.
```
spread = best_ask - best_bid
spread_bps = spread / mid_price * 10000
# Baseline: compute rolling 20-tick avg spread
spread_zscore = (spread_bps - spread_avg) / spread_stdev
```

**Edge:** Spread compression (tightening below avg) indicates a side is committing — market makers are pricing less uncertainty. Use as confirmation, not primary signal.

**Filter:** Only trade when `spread_zscore < -0.5` (spread is tightening, not widening).

### Entry Logic (obsidian_flux)

```
LONG entry requires ALL:
  - OBI > 0.25 (buyer pressure dominant at top of book)
  - VCM > 0.003 (price move confirmed by above-average volume)
  - spread_zscore < 0.5 (spread not blowing out)
  - No existing long position > 30% of USDT equivalent
  - Position open < 3 minutes (stale signals reset)

SHORT entry requires ALL:
  - OBI < -0.25 (seller pressure dominant)
  - VCM < -0.003 (bearish price on above-average volume)  
  - short_qty == ZERO for THIS symbol (check all candidates independently)
  - USDT >= 150

COVER: check ALL symbol shorts on every tick
  - If short open: OBI for THAT symbol > 0.10 OR VCM > 0.001
  - Hard time stop: cover any short older than 20 ticks (100 seconds)

SELL: 
  - OBI < -0.15 for held symbol
  - OR VCM negative for 3 consecutive ticks
  - Sell 100% of position (not 80% partial — clean exits)
```

### Position Sizing

```
Base allocation: 8% of USDT per entry (down from 18%)
Max per symbol: 25% of total portfolio
Max simultaneous open positions: 3 symbols
Trade cooldown: minimum 60 seconds between same-symbol entries
```

### Symbols to Watch

Trade only **BTCUSDT** and **ETHUSDT** in experiment 2. These have:
- Deepest order books on Coinbase (more signal, less manipulation)
- Real institutional presence (OBI is more meaningful)
- Lower bid-ask spread (less slippage destroying edge)

Drop SOLUSDT and DOGEUSDT until signal quality is proven on liquid markets.

### What NOT to Use

- **No synthetic oscillators** — if it's not from the Coinbase API, it's not a signal
- **No narrative_score** — narrative is qualitative and can't be simulated
- **No event_score sine waves** — replace with real volume spikes if a catalyst detection is desired
- **No automatic BTC liquidation** to fund alt bets — BTC is the capital base, protect it

### Success Criteria for Experiment 2

- **Sharpe > 0** (any positive risk-adjusted return is better than Exp 1)
- **Max drawdown < 20%**
- **Trade count < 500 per 30h** (quality > quantity, target ~0.27 trades/min vs 1.47/min for stormchaser)
- **Buy:Sell ratio between 1:1 and 2:1** (not 7:1)

---

## Summary Table

| Issue | stormchaser_delta | obsidian_flux fix |
|-------|------------------|-------------------|
| Signal source | Synthetic sine wave | Real Coinbase order book + volume |
| Buy trigger frequency | 29.3% of ticks | ~3–5% of ticks (OBI + VCM required) |
| Entry size | 18% USDT per buy | 8% USDT, max 25% per symbol |
| Exit coverage | Single top-ranked symbol | All open symbols checked every tick |
| Short/cover logic | Broken (SOL: 10 shorts, 0 covers) | Fixed: per-symbol cover loop + time stop |
| BTC reserve drain | 95.8% liquidated for alt fuel | BTC reserve locked (no auto-liquidation) |
| Trade count | 2,655 in 30h | Target: <500 |
| Symbols | SOL, DOGE, ETH (low liquidity) | BTC, ETH (deepest books) |
| Event detection | Fake oscillator | Real volume anomaly detection |

---

*Analysis complete. Recommend reviewing obsidian_flux spec with team before experiment 2 launch.*
