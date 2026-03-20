# Experiment 2 — Bot 4 Design: PHANTOM_LATTICE

**Status:** Design complete, ready for integration  
**Author:** Neon Cortex subagent  
**Date:** 2026-03-19  

---

## 1. Name & Persona

### `phantom_lattice`

**Identity:** The Relationship Archeologist  
**Vibe:** Academic, patient, almost invisible — trades the hidden geometry of price relationships, not the prices themselves. Where other bots see candles and momentum, Phantom Lattice sees a web of ratios, tensions, and structural dislocations that temporarily stretch and snap back.

**Core belief:**
> Markets are not individual prices. They are a lattice of relationships. When the geometry bends, it must return to its shape. I watch the bending.

**Trading personality:**  
Phantom Lattice does not care about BTC going up or ETH going down. It cares about whether ETH is *cheap or expensive relative to BTC right now versus how it usually is.* Combined with real-time order book pressure — not sentiment, not news, not oscillators — it only acts when two independent real signals simultaneously agree.

**Why it's different from the other 3:**
- Aurora Quanta: macro regime momentum → **uses narrative_score (fake)**
- StormChaser Delta: event/volatility breakout → **uses event_score (fake)**
- Mercury Vanta: short-term mean reversion on individual prices → **pure price, no cross-pair signal**
- Phantom Lattice: **cross-pair ratio dislocations + live order book microstructure — both real**

**Tagline:** *The lattice always returns to its shape.*

---

## 2. Strategy Rationale

### Why cross-pair ratio stat arb works on real crypto markets

**Economic foundation:**  
ETH and BTC are highly correlated macro assets — both driven by the same macro liquidity cycle, regulatory environment, and institutional flows. Their price *ratio* (ETH/BTC) has a long-term statistical mean around which it oscillates. When the ratio temporarily deviates, it tends to revert. This isn't just theory — ETH/BTC and SOL/BTC cross rates are actively traded by professional desks as a relative-value trade.

**Why short-term deviations happen:**  
Large order flow in one asset (e.g., a whale buying ETH directly) temporarily pushes the ratio away from its mean before arbitrageurs and market makers correct it over the next few minutes. In a 5-second tick environment, we can often detect this dislocation before it's fully corrected.

**Why order book imbalance confirms it:**  
Order book imbalance (OBI) measures whether there are more limit bids than asks sitting in the book right now. A positive OBI means buying pressure is building — market participants want to buy. If ETH/BTC ratio is below its mean (ETH is "cheap") AND the ETH order book shows more bids than asks, that's two independent signals pointing the same direction — high probability that ETH will rise relative to BTC.

**Why this avoids the Exp 1 failures:**
1. **No synthetic signals** — Both signals are computed from real Coinbase data
2. **Two-signal gate** — Must have ratio dislocation AND OBI confirmation simultaneously → drastically fewer false positives
3. **Hard cadence limits** — Maximum 1 trade per symbol per ~2 minutes, prevents fee death
4. **If either signal is unavailable** → skip entirely, never falls back to fake data

---

## 3. Signal Computation

### Signal 1: Cross-Pair Ratio Z-Score

Computed from the existing `state.history` price series (real prices from Coinbase when `MARKET_DATA_SOURCE=coinbase`).

```python
def compute_ratio_zscore(
    alt_hist: list,   # list of Decimal prices for ETH or SOL
    btc_hist: list,   # list of Decimal prices for BTC
    lookback: int = 120,  # ~10 min at 5-sec ticks
) -> tuple[float, float, float] | None:
    """
    Returns (z_score, current_ratio, mean_ratio) or None if insufficient data.
    z_score < 0 → alt is cheap vs BTC (expect ratio to rise → buy alt)
    z_score > 0 → alt is expensive vs BTC (expect ratio to fall → sell alt)
    """
    if len(btc_hist) < lookback or len(alt_hist) < lookback:
        return None

    btc_vals = [float(x) for x in btc_hist[-lookback:]]
    alt_vals = [float(x) for x in alt_hist[-lookback:]]

    ratios = [a / b for a, b in zip(alt_vals, btc_vals) if b > 0]
    if len(ratios) < 20:
        return None

    mean_r = sum(ratios) / len(ratios)
    var_r = sum((r - mean_r) ** 2 for r in ratios) / len(ratios)
    std_r = var_r ** 0.5

    if std_r < 1e-12:
        return None

    z = (ratios[-1] - mean_r) / std_r
    return z, ratios[-1], mean_r
```

### Signal 2: Order Book Imbalance (OBI)

Requires authenticated Coinbase Advanced Trade API (`CB_API_KEY` + `CB_API_SECRET`).

```python
def fetch_order_book_imbalance(self, symbol: str, levels: int = 10) -> float | None:
    """
    Fetch order book for a symbol and compute bid/ask volume imbalance.
    
    Returns float in [-1.0, +1.0]:
      +1.0 = all bids (maximum buying pressure)
      -1.0 = all asks (maximum selling pressure)
       0.0 = balanced book
    Returns None if fetch fails (caller should skip trade, not fall back).
    
    Uses the Coinbase Advanced Trade /book endpoint:
    GET /api/v3/brokerage/market/products/{product_id}/book
    """
    from .market_feed import SYMBOL_MAP, _get_authed

    api_key = os.getenv("CB_API_KEY")
    private_key_pem = os.getenv("CB_API_SECRET")
    if not api_key or not private_key_pem:
        self.log("[phantom_lattice] no API credentials — cannot fetch order book, skipping")
        return None

    cb_sym = SYMBOL_MAP.get(symbol)
    if not cb_sym:
        return None

    try:
        path = f"/api/v3/brokerage/market/products/{cb_sym}/book?limit={levels}"
        data = _get_authed(path, api_key, private_key_pem)

        # Coinbase Advanced Trade API returns pricebook wrapper
        book = data.get("pricebook", data)
        bids = book.get("bids", [])
        asks = book.get("asks", [])

        def parse_size(entry: dict) -> float:
            return float(entry.get("size", entry.get("quantity", 0)))

        bid_vol = sum(parse_size(b) for b in bids[:levels])
        ask_vol = sum(parse_size(a) for a in asks[:levels])

        total = bid_vol + ask_vol
        if total < 1e-10:
            return 0.0

        return (bid_vol - ask_vol) / total

    except Exception as exc:
        self.log(f"[phantom_lattice] order book fetch failed for {symbol}: {exc}")
        return None
```

---

## 4. Decision Logic

```python
def phantom_lattice_logic(self, state: BotState) -> None:
    """
    PHANTOM_LATTICE — Cross-pair ratio stat arb + order book imbalance.

    Strategy:
      1. Compute ETH/BTC and SOL/BTC ratio z-scores from price history
      2. If a ratio is significantly dislocated (|z| > Z_THRESHOLD):
         - z < 0 → alt is cheap vs BTC → candidate BUY signal
         - z > 0 → alt is expensive vs BTC → candidate SELL signal
      3. Fetch live order book imbalance (OBI) for the candidate pair
      4. Only execute if OBI confirms the ratio signal direction
      5. Strict cadence controls prevent overtrading

    Key design principles:
      - NEVER trades on synthetic signals (narrative_score, event_score ignored)
      - If order book is unavailable → skip (no fallback to fake data)
      - Two independent real signals required → far fewer but higher-quality trades
    """
    # ── Tunable parameters ───────────────────────────────────────────────────
    RATIO_LOOKBACK        = 120   # ticks for ratio rolling stats (~10 min @ 5s)
    Z_THRESHOLD           = 1.6   # z-score magnitude needed to consider a trade
    Z_STRONG_THRESHOLD    = 2.5   # larger size for extreme dislocations
    OBI_THRESHOLD         = 0.08  # order book imbalance minimum to confirm
    OBI_STRONG            = 0.18  # stronger OBI = slightly larger position
    GLOBAL_COOLDOWN_TICKS = 10    # min ticks between ANY trade (~50s @ 5s ticks)
    SYMBOL_COOLDOWN_TICKS = 24    # min ticks between trades in same symbol (~2 min)
    BASE_ALLOC            = Decimal('0.18')   # 18% of USDT per trade
    MAX_ALLOC             = Decimal('0.28')   # up to 28% on strong signals
    MAX_POSITION_FRAC     = Decimal('0.45')   # cap at 45% of portfolio in any alt
    MIN_USDT              = Decimal('60')     # minimum USDT to enter
    # ─────────────────────────────────────────────────────────────────────────

    # Initialize cooldown state (persists on LeagueRuntime instance across ticks)
    if not hasattr(self, '_pl_last_trade'):
        self._pl_last_trade: dict[str, int] = {}
    if not hasattr(self, '_pl_last_any'):
        self._pl_last_any: int = 0

    # Global cooldown: don't spam on every tick
    if state.tick - self._pl_last_any < GLOBAL_COOLDOWN_TICKS:
        return

    balances  = state.balances
    usdt      = self.usdt_balance(balances)
    btc_hist  = state.history.get('BTCUSDT', [])
    eth_hist  = state.history.get('ETHUSDT', [])
    sol_hist  = state.history.get('SOLUSDT', [])

    # Need sufficient history to compute meaningful ratios
    min_history = RATIO_LOOKBACK + 5
    if len(btc_hist) < min_history:
        return

    # ── Compute ratio z-scores for candidate pairs ───────────────────────────
    candidates = []  # (|z|, z, symbol, current_ratio, mean_ratio)

    for alt_sym, alt_hist in [('ETHUSDT', eth_hist), ('SOLUSDT', sol_hist)]:
        if len(alt_hist) < min_history:
            continue

        result = self._pl_ratio_zscore(alt_hist, btc_hist, RATIO_LOOKBACK)
        if result is None:
            continue

        z, current_ratio, mean_ratio = result

        # Only consider pairs with meaningful dislocation
        if abs(z) >= Z_THRESHOLD:
            candidates.append((abs(z), z, alt_sym, current_ratio, mean_ratio))

    if not candidates:
        return  # No dislocated pairs — nothing to do

    # Sort by magnitude — trade the most dislocated pair first
    candidates.sort(reverse=True)

    for abs_z, z, alt_sym, current_ratio, mean_ratio in candidates:
        # Per-symbol cooldown
        last_tick = self._pl_last_trade.get(alt_sym, 0)
        if state.tick - last_tick < SYMBOL_COOLDOWN_TICKS:
            continue

        direction = 'BUY' if z < 0 else 'SELL'
        held_qty  = self.holdings_qty(balances, alt_sym)
        price     = state.marks[alt_sym]

        # ── Signal Gate: fetch order book imbalance ──────────────────────────
        # This is the second independent real signal.
        # If unavailable → skip (never degrade to fake signal).
        obi = self.fetch_order_book_imbalance(alt_sym)
        if obi is None:
            continue  # API unavailable — skip this pair

        obi_confirms = (
            (direction == 'BUY'  and obi >  OBI_THRESHOLD) or
            (direction == 'SELL' and obi < -OBI_THRESHOLD)
        )

        if not obi_confirms:
            # OBI doesn't confirm ratio signal — this is the quality filter
            continue

        # ── Signal confirmed: determine size ────────────────────────────────
        strong_signal = abs_z >= Z_STRONG_THRESHOLD and abs(obi) >= OBI_STRONG
        alloc_frac    = MAX_ALLOC if strong_signal else BASE_ALLOC

        # ── Execute BUY ──────────────────────────────────────────────────────
        if direction == 'BUY' and usdt > MIN_USDT:
            # Don't over-concentrate in one alt
            alt_value = held_qty * price
            btc_val   = balances.get('BTC', ZERO) * state.marks.get('BTCUSDT', ZERO)
            total_est = usdt + alt_value + btc_val
            if total_est > ZERO and alt_value / total_est > MAX_POSITION_FRAC:
                continue  # Already at max exposure for this alt

            alloc = min(usdt * alloc_frac, usdt * Decimal('0.35'))
            qty   = alloc / price

            self.place_order(
                state.bot_id,
                alt_sym,
                'BUY',
                qty,
                {
                    'strategy':              'phantom_lattice_ratio_arb_v1',
                    'z_score':               round(z, 4),
                    'abs_z':                 round(abs_z, 4),
                    'current_ratio':         round(current_ratio, 8),
                    'mean_ratio':            round(mean_ratio, 8),
                    'order_book_imbalance':  round(obi, 4),
                    'signal':                'alt_cheap_vs_btc_expect_reversion',
                    'strong_signal':         strong_signal,
                    'alloc_fraction':        float(alloc_frac),
                },
            )
            self._pl_last_trade[alt_sym] = state.tick
            self._pl_last_any            = state.tick
            break  # One trade per logic call

        # ── Execute SELL ─────────────────────────────────────────────────────
        elif direction == 'SELL' and held_qty > ZERO:
            sell_fraction = Decimal('0.70') if strong_signal else Decimal('0.55')

            self.place_order(
                state.bot_id,
                alt_sym,
                'SELL',
                held_qty * sell_fraction,
                {
                    'strategy':              'phantom_lattice_ratio_arb_v1',
                    'z_score':               round(z, 4),
                    'abs_z':                 round(abs_z, 4),
                    'current_ratio':         round(current_ratio, 8),
                    'mean_ratio':            round(mean_ratio, 8),
                    'order_book_imbalance':  round(obi, 4),
                    'signal':                'alt_expensive_vs_btc_expect_reversion',
                    'strong_signal':         strong_signal,
                    'sell_fraction':         float(sell_fraction),
                },
            )
            self._pl_last_trade[alt_sym] = state.tick
            self._pl_last_any            = state.tick
            break  # One trade per logic call

    # ── Stale position exit ───────────────────────────────────────────────────
    # If we're holding a position but the ratio has fully mean-reverted (z near 0)
    # and OBI has flipped → take profit
    for alt_sym in ['ETHUSDT', 'SOLUSDT']:
        held_qty = self.holdings_qty(balances, alt_sym)
        if held_qty <= ZERO:
            continue

        alt_hist = state.history.get(alt_sym, [])
        if len(alt_hist) < min_history:
            continue

        result = self._pl_ratio_zscore(alt_hist, btc_hist, RATIO_LOOKBACK)
        if result is None:
            continue

        z, _, _ = result

        # If z has reverted past 0 or gone positive after we bought → take profit
        if z > 0.3:
            obi = self.fetch_order_book_imbalance(alt_sym)
            if obi is not None and obi < -0.05:
                last_tick = self._pl_last_trade.get(alt_sym, 0)
                if state.tick - last_tick >= SYMBOL_COOLDOWN_TICKS:
                    self.place_order(
                        state.bot_id,
                        alt_sym,
                        'SELL',
                        held_qty * Decimal('0.60'),
                        {
                            'strategy':             'phantom_lattice_ratio_arb_v1',
                            'z_score':              round(z, 4),
                            'order_book_imbalance': round(obi, 4),
                            'signal':               'ratio_reverted_take_profit',
                        },
                    )
                    self._pl_last_trade[alt_sym] = state.tick
                    self._pl_last_any            = state.tick
                    break


def _pl_ratio_zscore(
    self,
    alt_hist: list,
    btc_hist: list,
    lookback: int,
) -> tuple[float, float, float] | None:
    """
    Helper: compute z-score of the alt/BTC price ratio over the lookback window.
    Returns (z_score, current_ratio, mean_ratio) or None if computation fails.
    """
    btc_vals = [float(x) for x in btc_hist[-lookback:]]
    alt_vals = [float(x) for x in alt_hist[-lookback:]]

    n = min(len(btc_vals), len(alt_vals), lookback)
    if n < 20:
        return None

    btc_vals = btc_vals[-n:]
    alt_vals = alt_vals[-n:]

    ratios = [a / b for a, b in zip(alt_vals, btc_vals) if b > 0]
    if len(ratios) < 20:
        return None

    mean_r = sum(ratios) / len(ratios)
    var_r  = sum((r - mean_r) ** 2 for r in ratios) / len(ratios)
    std_r  = var_r ** 0.5

    if std_r < 1e-12:
        return None

    z = (ratios[-1] - mean_r) / std_r
    return z, ratios[-1], mean_r
```

---

## 5. Integration Guide

### Step 1: Add helper methods to `LeagueRuntime`

Add `fetch_order_book_imbalance` and `_pl_ratio_zscore` as methods of `LeagueRuntime` in `services/data_ingest/src/main.py`.

### Step 2: Add bot to the run loop

In `LeagueRuntime.run_bots()`, add `phantom_lattice` to `bot_ids`:

```python
bot_ids = ['aurora_quanta', 'stormchaser_delta', 'mercury_vanta', 'phantom_lattice']
```

And in the dispatch block:

```python
elif bot_id == 'phantom_lattice':
    self.phantom_lattice_logic(state)
```

### Step 3: Bootstrap the bot

The `/season/bootstrap` endpoint initializes all bots. Add `phantom_lattice` to the initial balances in `services/trade_engine/src/season.py` if it does per-bot initialization.

### Step 4: Config file

Create `config/bots/phantom_lattice.yaml`:

```yaml
bot_id: phantom_lattice
display_name: "Phantom Lattice"
strategy: ratio_arb_obi_v1
starting_btc: 0.05
market_data_source: coinbase  # REQUIRED — needs real order book data
```

### Step 5: Environment

This bot REQUIRES:
- `MARKET_DATA_SOURCE=coinbase`
- `CB_API_KEY` and `CB_API_SECRET` set

When running in synthetic mode without API credentials, `fetch_order_book_imbalance` returns `None` and the bot will skip all trades (correct behavior — no degradation to fake signals).

---

## 6. Risk Management Summary

| Parameter | Value | Rationale |
|-----------|-------|-----------|
| Z-score threshold | 1.6σ | Filters out noise, catches real dislocations |
| OBI threshold | 0.08 | Low enough to fire on real signal, high enough to filter noise |
| Global cooldown | 10 ticks (~50s) | Prevents back-to-back trading |
| Per-symbol cooldown | 24 ticks (~2 min) | No churning a single pair |
| Base position size | 18% of USDT | Significant but not reckless |
| Max position size | 28% of USDT | Only on strong dual-signal confluence |
| Max alt exposure | 45% of portfolio | Never puts more than half into one alt |
| Min USDT to trade | $60 | Ensures fees are tiny fraction of position |
| Sell fraction | 55-70% | Never goes to zero — partial exit keeps optionality |

### Expected trade frequency (live market @ 5s ticks)
- **Typical:** 2-8 trades per day
- **Busy market:** up to 15-20 trades per day
- **Comparison to aurora_quanta:** ~9,582 vs ~10-20 → 500x fewer trades → **fee death impossible**

### Hard stops (implement in future iteration)
- If USDT balance drops below $30 → no new buys
- If any alt position is down >8% since purchase → sell 40% (add `_pl_entry_prices` dict)
- Drawdown circuit breaker: if bot equity falls 20% below start → halt trading for 24h

---

## 7. Expected Behavior

### Conditions it profits from:
- ✅ **ETH/BTC or SOL/BTC ratio oscillations** — the ratio deviates and snaps back (most common market state)
- ✅ **Choppy, range-bound markets** — high ratio mean-reversion, bot stays patient and picks spots
- ✅ **Brief order flow imbalances** — large player buys ETH, temporarily pushes ratio down, OBI confirms → bot buys → corrects

### Conditions it suffers in:
- ❌ **Sustained ratio trends** — if ETH/BTC enters a multi-day structural breakout, z-score stays elevated and OBI may keep confirming — could accumulate losing positions
  - *Mitigation: cooldown limits prevent over-accumulation*
- ❌ **API downtime** — if Coinbase order book endpoint is rate-limited or down, bot goes silent (no trades). This is the correct behavior, not a bug
- ❌ **Very low USDT balance** — if BTC → USDT conversion hasn't happened, bot can't enter new longs
  - *Mitigation: `maybe_fund_trading_cash` already handles this*

### What makes it most likely to WIN Experiment 2:
1. **Genuine signal quality**: two independent real market signals both required
2. **Extremely low trade count**: fees will be a tiny fraction of aurora_quanta's
3. **Orthogonal to other bots**: not competing on same signal space → uncorrelated P&L
4. **Patience**: waits for setup quality, doesn't invent trades when market is boring

---

## 8. Complete Drop-In Code Block

The following is the complete set of additions needed for `main.py`. Copy these into the `LeagueRuntime` class:

```python
# ═══════════════════════════════════════════════════════════════════════════════
# PHANTOM LATTICE — Cross-pair ratio stat arb + order book imbalance
# ═══════════════════════════════════════════════════════════════════════════════

def fetch_order_book_imbalance(self, symbol: str, levels: int = 10) -> float | None:
    """
    Fetch order book for a symbol and compute bid/ask volume imbalance.
    Returns float in [-1.0, +1.0] where +1 = all bids, -1 = all asks.
    Returns None on any failure — caller MUST skip trade (no fallback).
    """
    try:
        from .market_feed import SYMBOL_MAP, _get_authed
    except ImportError:
        from market_feed import SYMBOL_MAP, _get_authed

    api_key = os.getenv("CB_API_KEY")
    private_key_pem = os.getenv("CB_API_SECRET")
    if not api_key or not private_key_pem:
        return None

    cb_sym = SYMBOL_MAP.get(symbol)
    if not cb_sym:
        return None

    try:
        path = f"/api/v3/brokerage/market/products/{cb_sym}/book?limit={levels}"
        data = _get_authed(path, api_key, private_key_pem)

        # Coinbase Advanced Trade wraps in pricebook
        book = data.get("pricebook", data)
        bids = book.get("bids", [])
        asks = book.get("asks", [])

        def parse_size(entry: dict) -> float:
            return float(entry.get("size", entry.get("quantity", 0)))

        bid_vol = sum(parse_size(b) for b in bids[:levels])
        ask_vol = sum(parse_size(a) for a in asks[:levels])

        total = bid_vol + ask_vol
        if total < 1e-10:
            return 0.0
        return (bid_vol - ask_vol) / total

    except Exception as exc:
        self.log(f"[phantom_lattice] order book fetch failed for {symbol}: {exc}")
        return None


def _pl_ratio_zscore(
    self,
    alt_hist: list,
    btc_hist: list,
    lookback: int,
) -> tuple[float, float, float] | None:
    """
    Compute z-score of the alt/BTC price ratio.
    Returns (z_score, current_ratio, mean_ratio) or None.
    """
    n = min(len(btc_hist), len(alt_hist), lookback)
    if n < 20:
        return None

    btc_vals = [float(x) for x in btc_hist[-n:]]
    alt_vals = [float(x) for x in alt_hist[-n:]]

    ratios = [a / b for a, b in zip(alt_vals, btc_vals) if b > 0]
    if len(ratios) < 20:
        return None

    mean_r = sum(ratios) / len(ratios)
    var_r  = sum((r - mean_r) ** 2 for r in ratios) / len(ratios)
    std_r  = var_r ** 0.5

    if std_r < 1e-12:
        return None

    z = (ratios[-1] - mean_r) / std_r
    return z, ratios[-1], mean_r


def phantom_lattice_logic(self, state: BotState) -> None:
    """
    PHANTOM LATTICE trading logic.

    Signals:
      1. Cross-pair ratio z-score (ETH/BTC, SOL/BTC) from real price history
      2. Live order book imbalance from Coinbase Advanced Trade API

    Trade only when BOTH signals agree. Skip if either is unavailable.
    """
    RATIO_LOOKBACK        = 120
    Z_THRESHOLD           = 1.6
    Z_STRONG_THRESHOLD    = 2.5
    OBI_THRESHOLD         = 0.08
    OBI_STRONG            = 0.18
    GLOBAL_COOLDOWN_TICKS = 10
    SYMBOL_COOLDOWN_TICKS = 24
    BASE_ALLOC            = Decimal('0.18')
    MAX_ALLOC             = Decimal('0.28')
    MAX_POSITION_FRAC     = Decimal('0.45')
    MIN_USDT              = Decimal('60')

    if not hasattr(self, '_pl_last_trade'):
        self._pl_last_trade: dict[str, int] = {}
    if not hasattr(self, '_pl_last_any'):
        self._pl_last_any: int = 0

    if state.tick - self._pl_last_any < GLOBAL_COOLDOWN_TICKS:
        return

    balances = state.balances
    usdt     = self.usdt_balance(balances)
    btc_hist = state.history.get('BTCUSDT', [])
    eth_hist = state.history.get('ETHUSDT', [])
    sol_hist = state.history.get('SOLUSDT', [])

    min_history = RATIO_LOOKBACK + 5
    if len(btc_hist) < min_history:
        return

    # Build candidate list sorted by dislocation magnitude
    candidates = []
    for alt_sym, alt_hist in [('ETHUSDT', eth_hist), ('SOLUSDT', sol_hist)]:
        if len(alt_hist) < min_history:
            continue
        result = self._pl_ratio_zscore(alt_hist, btc_hist, RATIO_LOOKBACK)
        if result is None:
            continue
        z, current_ratio, mean_ratio = result
        if abs(z) >= Z_THRESHOLD:
            candidates.append((abs(z), z, alt_sym, current_ratio, mean_ratio))

    candidates.sort(reverse=True)

    for abs_z, z, alt_sym, current_ratio, mean_ratio in candidates:
        last_tick = self._pl_last_trade.get(alt_sym, 0)
        if state.tick - last_tick < SYMBOL_COOLDOWN_TICKS:
            continue

        direction = 'BUY' if z < 0 else 'SELL'
        held_qty  = self.holdings_qty(balances, alt_sym)
        price     = state.marks[alt_sym]

        # Gate 2: order book imbalance (real API call)
        obi = self.fetch_order_book_imbalance(alt_sym)
        if obi is None:
            continue  # No fallback — skip

        obi_confirms = (
            (direction == 'BUY'  and obi >  OBI_THRESHOLD) or
            (direction == 'SELL' and obi < -OBI_THRESHOLD)
        )
        if not obi_confirms:
            continue

        strong  = abs_z >= Z_STRONG_THRESHOLD and abs(obi) >= OBI_STRONG
        alloc_f = MAX_ALLOC if strong else BASE_ALLOC

        if direction == 'BUY' and usdt > MIN_USDT:
            # Position concentration check
            alt_value = held_qty * price
            btc_val   = balances.get('BTC', ZERO) * state.marks.get('BTCUSDT', ZERO)
            total_est = usdt + alt_value + btc_val
            if total_est > ZERO and alt_value / total_est > MAX_POSITION_FRAC:
                continue

            qty = min(usdt * alloc_f, usdt * Decimal('0.35')) / price
            self.place_order(
                state.bot_id, alt_sym, 'BUY', qty,
                {
                    'strategy':             'phantom_lattice_ratio_arb_v1',
                    'z_score':              round(z, 4),
                    'current_ratio':        round(current_ratio, 8),
                    'mean_ratio':           round(mean_ratio, 8),
                    'order_book_imbalance': round(obi, 4),
                    'signal':               'alt_cheap_vs_btc',
                    'strong_signal':        strong,
                },
            )
            self._pl_last_trade[alt_sym] = state.tick
            self._pl_last_any            = state.tick
            break

        elif direction == 'SELL' and held_qty > ZERO:
            sell_frac = Decimal('0.70') if strong else Decimal('0.55')
            self.place_order(
                state.bot_id, alt_sym, 'SELL', held_qty * sell_frac,
                {
                    'strategy':             'phantom_lattice_ratio_arb_v1',
                    'z_score':              round(z, 4),
                    'current_ratio':        round(current_ratio, 8),
                    'mean_ratio':           round(mean_ratio, 8),
                    'order_book_imbalance': round(obi, 4),
                    'signal':               'alt_expensive_vs_btc',
                    'strong_signal':        strong,
                },
            )
            self._pl_last_trade[alt_sym] = state.tick
            self._pl_last_any            = state.tick
            break

    # Take-profit on reverted positions
    for alt_sym in ['ETHUSDT', 'SOLUSDT']:
        held_qty = self.holdings_qty(balances, alt_sym)
        if held_qty <= ZERO:
            continue
        alt_hist = state.history.get(alt_sym, [])
        if len(alt_hist) < min_history:
            continue
        result = self._pl_ratio_zscore(alt_hist, btc_hist, RATIO_LOOKBACK)
        if result is None:
            continue
        z, _, _ = result
        if z > 0.3:  # Ratio overshot the other way after our buy
            last_tick = self._pl_last_trade.get(alt_sym, 0)
            if state.tick - last_tick < SYMBOL_COOLDOWN_TICKS:
                continue
            obi = self.fetch_order_book_imbalance(alt_sym)
            if obi is not None and obi < -0.05:
                self.place_order(
                    state.bot_id, alt_sym, 'SELL', held_qty * Decimal('0.60'),
                    {
                        'strategy':             'phantom_lattice_ratio_arb_v1',
                        'z_score':              round(z, 4),
                        'order_book_imbalance': round(obi, 4),
                        'signal':               'ratio_reverted_take_profit',
                    },
                )
                self._pl_last_trade[alt_sym] = state.tick
                self._pl_last_any            = state.tick
                break
```

### Add to `run_bots()`:

```python
def run_bots(self) -> None:
    marks = self.current_marks()
    history = {symbol: self.symbol_history(symbol) for symbol in self.symbols}
    # Add phantom_lattice to bot_ids:
    bot_ids = ['aurora_quanta', 'stormchaser_delta', 'mercury_vanta', 'phantom_lattice']
    for bot_id in bot_ids:
        state = BotState(
            bot_id=bot_id,
            marks=marks,
            history=history,
            balances=self.get_balances(bot_id),
            tick=self.tick,
            event_score=self.event_score,
            narrative_score=self.narrative_score,
        )
        if self.maybe_fund_trading_cash(state):
            continue
        if bot_id == 'aurora_quanta':
            self.aurora_logic(state)
        elif bot_id == 'stormchaser_delta':
            self.storm_logic(state)
        elif bot_id == 'mercury_vanta':
            self.mercury_logic(state)
        elif bot_id == 'phantom_lattice':
            self.phantom_lattice_logic(state)
```

---

## 9. Open Questions / Future Enhancements

1. **Entry price tracking**: Add `_pl_entry_prices` dict to implement percentage-based stop losses
2. **Candle-based trend filter**: Use the `/candles` endpoint (1hr candles) to skip ratio-arb trades that fight the macro trend — could reduce false entries in sustained ratio trends
3. **Multi-lookback confirmation**: Use both 60-tick and 180-tick ratio z-scores; only trade when both show same direction (avoids noisy 10-min signal being contradicted by 30-min reality)
4. **Volume confirmation**: Fetch 24h volume from ticker; reduce size if volume is unusually low (wider spreads, more slippage)
5. **OBI time decay**: If OBI confirmed but trade wasn't placed (due to cooldown), track staleness — OBI data older than 3 ticks should be refetched rather than reused

---

*PHANTOM_LATTICE is designed to be the antidote to Experiment 1's failures. It trades real structure, guards with real microstructure, and refuses to act when information quality degrades. The lattice always returns to its shape.*
