# 🤖 Season 4 Bot Registry — Visual Identity & Profiles

## Bot Color Palette & Emoji Assignment

Each bot has a unique **graph color** (for Grafana), **emoji**, and **professional background styling**.

---

## AGGRESSIVE RISK-TAKERS (50% Risk Tolerance)

### 🚀 Loser Reversal Hunter
**Graph Color:** `#FF6B6B` (Red)  
**Text Color:** `#FFFFFF` (White)  
**Background:** `background: #FF6B6B; color: #FFFFFF;`  
**Personality:** Mean reversion specialist. Buys crashes, sells bounces.  
**Strategy:** Big Losers (down >15% in 24h), RSI < 30  
**Capital:** 0.0075 BTC  
**Risk:** 50% per trade  
**Target:** +30-50% per trade  

---

### 📈 Gainer Momentum Catcher
**Graph Color:** `#4ECDC4` (Teal)  
**Text Color:** `#FFFFFF` (White)  
**Background:** `background: #4ECDC4; color: #FFFFFF;`  
**Personality:** FOMO rider. Chases momentum before exhaustion.  
**Strategy:** Big Gainers (up >20% in 24h), RSI 50-75  
**Capital:** 0.0075 BTC  
**Risk:** 50% per trade  
**Target:** +40-60% per trade  

---

### 💥 Degen Ape 9000
**Graph Color:** `#FFD93D` (Gold)  
**Text Color:** `#1A1A1A` (Dark Gray)  
**Background:** `background: #FFD93D; color: #1A1A1A;`  
**Personality:** All-in conviction plays. To the moon or rekt.  
**Strategy:** High-conviction sentiment spikes  
**Capital:** 0.0075 BTC  
**Risk:** 50% per trade  
**Target:** +50% to +200% per trade  

---

### 🌊 Pump Surfer
**Graph Color:** `#FF8B94` (Coral Pink)  
**Text Color:** `#FFFFFF` (White)  
**Background:** `background: #FF8B94; color: #FFFFFF;`  
**Personality:** Catches emerging altcoin pumps. Rides volatility.  
**Strategy:** Volume spikes + price surge detection  
**Capital:** 0.0075 BTC  
**Risk:** 50% per trade  
**Target:** +30% to +100% per trade  

---

### ⚡ StormChaser Delta
**Graph Color:** `#6C5CE7` (Purple)  
**Text Color:** `#FFFFFF` (White)  
**Background:** `background: #6C5CE7; color: #FFFFFF;`  
**Personality:** Fast, opportunistic. Rides volatility spikes.  
**Strategy:** Event-driven, liquidation cascades, news spikes  
**Capital:** 0.0075 BTC  
**Risk:** 45% per trade  
**Target:** +20% to +50% per trade  

---

### 🌪️ Chaos Prophet
**Graph Color:** `#A29BFE` (Light Purple)  
**Text Color:** `#FFFFFF` (White)  
**Background:** `background: #A29BFE; color: #FFFFFF;`  
**Personality:** Thrives on chaos. Exploits volatility dislocations.  
**Strategy:** Vol spikes, price dislocations, arb opportunities  
**Capital:** 0.0075 BTC  
**Risk:** 45% per trade  
**Target:** +10% to +25% per trade  

---

## MODERATE RISK-TAKERS (30-40% Risk Tolerance)

### 🌍 Aurora Quanta
**Graph Color:** `#00B894` (Green)  
**Text Color:** `#FFFFFF` (White)  
**Background:** `background: #00B894; color: #FFFFFF;`  
**Personality:** Patient, measured, macro-aware. Thesis-driven.  
**Strategy:** Macro trend following, market breadth, BTC dominance  
**Capital:** 0.0075 BTC  
**Risk:** 40% per trade  
**Target:** +15% to +35% per trade  

---

### 🌀 Vega Pulse
**Graph Color:** `#FFA502` (Orange)  
**Text Color:** `#FFFFFF` (White)  
**Background:** `background: #FFA502; color: #FFFFFF;`  
**Personality:** Plays vol extremes. Sells the spikes.  
**Strategy:** Volatility mean reversion, vol percentile signals  
**Capital:** 0.0075 BTC  
**Risk:** 40% per trade  
**Target:** +12% to +30% per trade  

---

### 👻 Obsidian Flux
**Graph Color:** `#2C3E50` (Dark Slate)  
**Text Color:** `#FFFFFF` (White)  
**Background:** `background: #2C3E50; color: #FFFFFF;`  
**Personality:** Quiet, precise. Boring alpha.  
**Strategy:** Price deviation mean reversion (Z-score > 2.0)  
**Capital:** 0.0075 BTC  
**Risk:** 35% per trade  
**Target:** +10% to +25% per trade  

---

### 🪟 Phantom Lattice
**Graph Color:** `#95E1D3` (Mint Green)  
**Text Color:** `#1A1A1A` (Dark Gray)  
**Background:** `background: #95E1D3; color: #1A1A1A;`  
**Personality:** Market neutral. Balanced, statistical.  
**Strategy:** Pairs trading / statistical arbitrage  
**Capital:** 0.0075 BTC  
**Risk:** 30% per trade  
**Target:** +8% to +20% per trade  

---

## CONSERVATIVE/HIGH-FREQUENCY (20-35% Risk Tolerance)

### 🌙 Solstice Drift
**Graph Color:** `#74B9FF` (Light Blue)  
**Text Color:** `#1A1A1A` (Dark Gray)  
**Background:** `background: #74B9FF; color: #1A1A1A;`  
**Personality:** Consistent, disciplined. Trend follower.  
**Strategy:** MA crossover (20-day > 50-day), trend following  
**Capital:** 0.0075 BTC  
**Risk:** 35% per trade  
**Target:** +15% to +40% per trade  

---

### 💎 Mercury Vanta
**Graph Color:** `#FD79A8` (Hot Pink)  
**Text Color:** `#FFFFFF` (White)  
**Background:** `background: #FD79A8; color: #FFFFFF;`  
**Personality:** Quiet, precise, fee-aware. Scalper.  
**Strategy:** Orderbook microstructure, high-frequency small edges  
**Capital:** 0.0075 BTC  
**Risk:** 20% per trade  
**Target:** +0.5% to +2% per trade (high frequency)  

---

## 📊 Visual Bot ID Format (HTML/CSS)

For Grafana or web dashboards, use this format:

```html
<!-- Loser Reversal Hunter -->
<span style="
  background: #FF6B6B;
  color: #FFFFFF;
  padding: 8px 12px;
  border-radius: 6px;
  font-weight: 600;
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
  display: inline-block;
">
  🚀 Loser Reversal Hunter
</span>

<!-- Gainer Momentum Catcher -->
<span style="
  background: #4ECDC4;
  color: #FFFFFF;
  padding: 8px 12px;
  border-radius: 6px;
  font-weight: 600;
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
  display: inline-block;
">
  📈 Gainer Momentum Catcher
</span>

<!-- Degen Ape 9000 -->
<span style="
  background: #FFD93D;
  color: #1A1A1A;
  padding: 8px 12px;
  border-radius: 6px;
  font-weight: 600;
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
  display: inline-block;
">
  💥 Degen Ape 9000
</span>
```

---

## 🎨 Color Reference Chart

| Bot | Emoji | Color Code | Color Name | Text Color |
|-----|-------|-----------|-----------|------------|
| Loser Reversal Hunter | 🚀 | #FF6B6B | Red | White |
| Gainer Momentum Catcher | 📈 | #4ECDC4 | Teal | White |
| Degen Ape 9000 | 💥 | #FFD93D | Gold | Dark Gray |
| Pump Surfer | 🌊 | #FF8B94 | Coral Pink | White |
| StormChaser Delta | ⚡ | #6C5CE7 | Purple | White |
| Chaos Prophet | 🌪️ | #A29BFE | Light Purple | White |
| Aurora Quanta | 🌍 | #00B894 | Green | White |
| Vega Pulse | 🌀 | #FFA502 | Orange | White |
| Obsidian Flux | 👻 | #2C3E50 | Dark Slate | White |
| Phantom Lattice | 🪟 | #95E1D3 | Mint Green | Dark Gray |
| Solstice Drift | 🌙 | #74B9FF | Light Blue | Dark Gray |
| Mercury Vanta | 💎 | #FD79A8 | Hot Pink | White |

---

## 📐 Design Guidelines

### Color Accessibility
- **High contrast pairs:** All combos tested for WCAG AA compliance
- **Light backgrounds (Gold, Light Blue, Mint):** Use dark text (#1A1A1A)
- **Dark backgrounds (all others):** Use white text (#FFFFFF)

### Typography
- **Font:** System fonts (`-apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif`)
- **Weight:** 600 (semi-bold)
- **Padding:** 8px 12px
- **Border Radius:** 6px (modern, rounded look)

### Emoji Selection
Each emoji reflects bot personality:
- 🚀 = Aggressive momentum
- 📈 = Chasing gainers
- 💥 = Explosive/YOLO
- 🌊 = Riding waves/pumps
- ⚡ = Fast/electrical
- 🌪️ = Chaotic/turbulent
- 🌍 = Macro/global
- 🌀 = Spinning/rotating (volatility)
- 👻 = Hidden/invisible edge
- 🪟 = Structured/lattice
- 🌙 = Steady/nocturnal drift
- 💎 = Precise/precious

---

## 🖼️ Grafana Series Color Mapping

For Grafana dashboard legend colors, use these hex codes:

```json
{
  "loser_reversal_hunter": "#FF6B6B",
  "gainer_momentum_catcher": "#4ECDC4",
  "degen_ape_9000": "#FFD93D",
  "pump_surfer": "#FF8B94",
  "stormchaser_delta": "#6C5CE7",
  "chaos_prophet": "#A29BFE",
  "aurora_quanta": "#00B894",
  "vega_pulse": "#FFA502",
  "obsidian_flux": "#2C3E50",
  "phantom_lattice": "#95E1D3",
  "solstice_drift": "#74B9FF",
  "mercury_vanta": "#FD79A8"
}
```

---

## 🎯 Usage

**In HTML/Web:**
```html
<div style="background: #FF6B6B; color: #FFFFFF; padding: 8px 12px; border-radius: 6px; font-weight: 600;">
  🚀 Loser Reversal Hunter
</div>
```

**In Markdown (approx visual):**
```
🚀 **Loser Reversal Hunter** (Red #FF6B6B)
📈 **Gainer Momentum Catcher** (Teal #4ECDC4)
💥 **Degen Ape 9000** (Gold #FFD93D)
```

**In Grafana Panels:**
- Set series color to hex code from reference chart
- Add emoji + bot name to legend label
- Use as graph title: `🚀 Loser Reversal Hunter — Daily PnL`

---

**Ready to use in Grafana, web dashboards, or leaderboards!** 🎨

