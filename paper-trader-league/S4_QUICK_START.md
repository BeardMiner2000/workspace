# 🚀 Season 4 Quick Start Guide

**TL;DR:** Two new bots hunting Coinbase Big Gainers/Losers. Risk 50% per trade. Hold 1-4 hours. Target 15-25% monthly gains.

---

## The Two Bots

### 1. **Loser Reversal Hunter**
```
Watches: Coinbase "Big Losers" tab (down >15% in 24h)
Entry: RSI < 30, down >8% in 1h
Exit: +30-50% OR -50% stop OR 4h timeout
Holds: 2-4 hours
Max concurrent: 3
```

### 2. **Gainer Momentum Catcher**
```
Watches: Coinbase "Big Gainers" tab (up >20% in 24h)
Entry: Up >5% in 15 min, RSI 50-75, above 20-day MA
Exit: +40-60% OR -50% stop OR 3h timeout OR RSI exhaustion
Holds: 1-3 hours
Max concurrent: 4
```

---

## Key Numbers

| Metric | Value |
|--------|-------|
| Capital per bot | 0.015 BTC |
| Max risk per trade | 50% |
| Target profit per trade | +30-50% (reversals), +40-60% (gainers) |
| Expected win rate | 55-60% |
| Monthly target | +15-25% |
| Max portfolio drawdown | 35% (triggers liquidate-all) |

---

## Deployment Checklist

- [ ] Deploy bot runners (Docker: `docker-compose up -d loser_reversal_hunter gainer_momentum_catcher`)
- [ ] Connect Coinbase API (Big Gainers/Losers feeds, refresh every 5 min)
- [ ] Set up TimescaleDB tables (bot_positions, bot_trades, bot_metrics)
- [ ] Import Grafana dashboard (`S4_GRAFANA_DASHBOARD.json`)
- [ ] Test with 0.001 BTC per bot (24 hours, verify execution)
- [ ] Scale to 0.015 BTC per bot
- [ ] Monitor Grafana daily

---

## Real-Time Monitoring

**Grafana Dashboard:** `paper_trader_s4`

Live views:
- Current positions (symbol, gain/loss, time held)
- Daily PnL per bot
- Trade log (last 50 trades per bot)
- Win rate (7-day rolling)
- Coinbase Big Gainers/Losers feed

Alerts:
- Daily loss > 5%
- Single trade loss > -30%
- Portfolio drawdown > 25%

---

## Example Trade (Loser Reversal Hunter)

```
10:00 AM  BTC down 12% in 6h. RSI = 28. Entry: Buy 0.15 BTC.
10:45 AM  +3.2% gain. Hold.
11:15 AM  +5.2% gain. Sell 50%. Take +2.5%.
11:30 AM  Remaining +8%. Sell all. Full PnL: +4%.
```

---

## Example Trade (Gainer Momentum Catcher)

```
11:00 AM  SOL up +28% in 24h, up +7% in 30 min. RSI = 68. Entry: Buy SOL.
11:25 AM  +8.5% gain. Hold.
11:50 AM  +21% gain. RSI = 82. Volume drops. Sell 50%. Take +10.5%.
12:00 PM  Sell remaining at +25%. Full PnL: +22.5%.
```

---

## Risk Management

**Hard Rules:**
- Max -50% per trade (hard stop, no exceptions)
- Max 4 concurrent positions (don't over-leverage)
- Max 35% portfolio drawdown (liquidate all trigger)
- No hedges, no diversification (full conviction only)

**Soft Rules:**
- Take profit at +30-50% (don't get greedy)
- Exit if momentum dies (RSI exhaustion, volume drops)
- Time stops enforce discipline (3-4 hour max holds)

---

## Success Criteria (First Month)

- ✅ Both bots live and executing trades
- ✅ Grafana dashboard shows real position data
- ✅ No untracked losses or orphaned positions
- ✅ First week break-even or better
- ✅ Monthly +15-25% gains achieved by April 30

---

## Documentation

- **Full Strategy:** `BOT_PERSONAS_S4.md` (detailed personas, example trades)
- **Bot Guides:** `bots/loser_reversal_hunter/README.md`, `bots/gainer_momentum_catcher/README.md`
- **Configs:** `config/s4_loser_reversal.json`, `config/s4_gainer_momentum.json`
- **Launch Notes:** `S4_LAUNCH_NOTES.md` (deployment, risks, success criteria)
- **Grafana Template:** `S4_GRAFANA_DASHBOARD.json`

---

## Ready to Launch?

All documentation, configs, and bot logic are finalized. Just need API feeds + Grafana wired up.

**Status:** 🟢 Ready for deployment
**Capital Committed:** 0.03 BTC
**Next Step:** Deploy bot runners + test with 0.001 BTC per bot
