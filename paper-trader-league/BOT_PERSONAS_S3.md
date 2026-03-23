# 🎰 Bot Personas — Season 3: The Degen Expansion

> Season 3 introduces three unhinged personalities into the Paper Trader League. They don't read whitepapers. They don't diversify. They _ape_.

---

## 🦍 Bot 1: `degen_ape_9000`

**Tagline:** *"Number go up. Ape harder."*

**Archetype:** Pure memecoin momentum degenerate. No strategy, all conviction. This bot woke up one morning, saw SHIB up 40%, and thought "not enough." It allocates 70% of its bag to a single memecoin based on vibes (technically: 1h + 4h momentum scores), then either rides it to Valhalla or gets liquidated with dignity.

**Personality:**
- Absolutely unashamed about bag-holding PEPE
- Will rotate positions if a shinier coin appears with 2x better momentum
- Says "wagmi" as a risk management strategy
- Takes profit at +40%, cuts losses at -20% (surprisingly disciplined for an ape)
- Maximum hold time: 6 hours (then goes to sleep and wakes up with fresh delusions)

**Universe:** SHIB, PEPE, WIF, BONK, FLOKI, DOGE

**Strategy:** `degen_ape_momentum_v1`
- Scores coins using `(1h_mom × 2.0) + (4h_mom × 0.5)`
- Buys when top score > 0.04 and doesn't already hold the coin
- Allocates up to 70% of USDT in a single move
- Scans every 10 minutes (gotta let the candles cook)

---

## 🏄 Bot 2: `pump_surfer`

**Tagline:** *"I don't buy charts. I buy vibes and DexScreener notifications."*

**Archetype:** Solana micro-cap launch hunter. This bot lives on pump.fun energy, constantly refreshing DexScreener for the next 100x. It surfs into the top gainers before normies notice and theoretically exits before the inevitable rug pull.

**Personality:**
- Checks DexScreener every 60 seconds like it's scrolling Twitter
- Picks top 3 tokens by 24h price change (minimum +20% to even consider)
- Splits bag across up to 3 simultaneous moonshots (25% each)
- Knows when to bail: 2x profit, -40% loss, 2 hours max, or "token vanished from top 10"
- Maintains a BTC hedge when holding too much cash (it's not TOTALLY degenerate)
- Will try to exit even if the token has 0 liquidity (brave)

**Universe:** DexScreener top Solana tokens (live, from the actual API)

**Strategy:** `pump_surfer_dex_v1`
- Refreshes pump token list from DexScreener every 60s
- Entry: top 3 by `price_change_24h > 20%`
- Publishes live pump token prices as marks so MTM actually works
- Exit triggers: 2x (euphoria), -40% (cope), 2h timeout (rationality), or rug (survival)
- Hedge: if USDT > 80% of portfolio and no BTC held → buy 10% in BTC

---

## 🔮 Bot 3: `chaos_prophet`

**Tagline:** *"Buy the despair. Short the euphoria. Embrace the entropy."*

**Archetype:** Contrarian degen mystic. Where others see a chart going down and panic, chaos_prophet smells opportunity. Where others see a 100x pump and FOMO, chaos_prophet sees a short setup. It operates on a 480-tick cycle (alternating two personalities), and has an emergency self-destruct if it draws down 35%.

**Personality:**
- Deeply enjoys buying things that are at their worst moment
- Equally enjoys shorting things that everyone else is buying
- Two modes, alternating every ~40 minutes: Fallen Angel (buy the dip) and Chaos Gambit (short the pump)
- Has a hard rule: if total portfolio drops below 65% of starting value, liquidate *everything* immediately
- Tracks synthetic short positions on DexScreener tokens (since you can't really short BONKUSDT on a paper exchange)

**Universe:** All symbols — Coinbase majors + memecoins + DexScreener Solana tokens

**Strategy A: `fallen_angel_v1`** (ticks 0-239 of 480 cycle)
- Find the coin that has fallen the hardest in the last 4 hours
- Buy if: down >8% AND RSI < 35 (oversold AND beaten)
- Size: 35% of USDT
- Exits: +15% profit, -12% stop, 3-hour max hold

**Strategy B: `chaos_gambit_fade_pump_v1`** (ticks 240-479 of 480 cycle)
- Hunt for DexScreener tokens up >80% in 24h with volume > $100k
- If found: synthetically short them (proxy trade via SOLUSDT + local PnL tracking)
- Fallback: find a Coinbase memecoin up >15% in 2 hours and go SHORT
- Size: 20% of USDT
- Exits: +25% profit (short PnL), -20% stop, 4-hour max hold

---

## Season 3 Summary

| Bot | Style | Risk Level | Edge |
|-----|-------|------------|------|
| `degen_ape_9000` | Momentum ape | 🔴 Maximum | Memecoin momentum scoring |
| `pump_surfer` | Launch hunter | 🔴 Maximum | Real-time DexScreener alpha |
| `chaos_prophet` | Contrarian/fade | 🟠 High | Mean reversion + pump fading |

Season 2's bots (solstice_drift, obsidian_flux, vega_pulse, phantom_lattice) continue running unmodified. Season 3 is the chaotic expansion that nobody asked for and everyone deserved.

> *"They didn't come here to be risk-adjusted. They came here to cook."*
