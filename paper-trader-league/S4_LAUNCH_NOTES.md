# 🚀 Season 4 Launch Notes — Gainers & Losers

**Launch Date:** March 25, 2026, 15:57 PDT  
**Capital Allocation:** 0.015 BTC per bot (0.03 BTC total for Season 4)  
**Bots:** 2 new (loser_reversal_hunter, gainer_momentum_catcher)  
**Prior Seasons:** S1-S3 bots continue running unmodified  

---

## What's New in Season 4

### Philosophy Shift
- **Previous seasons:** Focus on single-pair strategies (obsidian_flux, vega_pulse, etc.) with controlled risk (20-30% stops)
- **Season 4:** Multi-pair extreme volatility hunters willing to risk **50% per trade** for 3-10x swings

### The Two Bots

#### 1. **Loser Reversal Hunter** (`loser_reversal_hunter`)
- Watches Coinbase "Big Losers" tab (coins down >15% in 24h)
- Thesis: Capitulation = opportunity. Buys crashed coins expecting bounce.
- Risk: -50% per trade  
- Target Exit: +30-50% bounce  
- Max Concurrent: 3 positions  
- Time Horizon: 2-4 hours per trade  

#### 2. **Gainer Momentum Catcher** (`gainer_momentum_catcher`)
- Watches Coinbase "Big Gainers" tab (coins up >20% in 24h)
- Thesis: Momentum is real. Chase before exhaustion. Catch 40-80% moves at +20-30% entry.
- Risk: -50% per trade  
- Target Exit: +40-60% continuation  
- Max Concurrent: 4 positions  
- Time Horizon: 1-3 hours per trade  

---

## Implementation Checklist

- [x] Bot persona docs written (`BOT_PERSONAS_S4.md`)
- [x] Configuration files created (`s4_loser_reversal.json`, `s4_gainer_momentum.json`)
- [x] Bot README files written (strategy guides, example trades, expected performance)
- [x] Grafana dashboard template created (`S4_GRAFANA_DASHBOARD.json`)
- [ ] **TODO:** Deploy bot runners (Docker containers or systemd services)
- [ ] **TODO:** Connect Coinbase API feeds (Big Gainers/Losers data source)
- [ ] **TODO:** Wire up TimescaleDB for position tracking and PnL reporting
- [ ] **TODO:** Test paper-trading execution on small capital (0.001 BTC each) before full deployment
- [ ] **TODO:** Verify Grafana dashboard is live and ingesting trade data

---

## Expected Outcomes

### Loser Reversal Hunter
- **Win Rate:** ~55% (not all reversals work)
- **Avg Winner:** +35%
- **Avg Loser:** -30% (early cuts) to -50% (hard stop)
- **Risk/Reward:** 1:1.2
- **Monthly Target:** +10-15% (or larger swings with drawdowns)

### Gainer Momentum Catcher
- **Win Rate:** ~60% (momentum continuation is more reliable)
- **Avg Winner:** +45%
- **Avg Loser:** -20% to -50% (aggressive cuts)
- **Risk/Reward:** 1:1
- **Monthly Target:** +15-25%

### Season 4 Combined
- **Expected Portfolio Growth:** +15-25% per month (if both bots execute well)
- **Max Drawdown Budget:** 35% of portfolio before liquidate-all trigger
- **Time Horizon:** Fast money (trades complete in 1-4 hours)

---

## Risk Warnings

1. **50% per-trade risk is EXTREME.** If both bots enter on the same day and both hit -50%, portfolio drops 50% (not cumulative, but close).
2. **Coinbase feed latency matters.** Real alpha is in the first 60 seconds of Big Gainers/Losers refresh. Missed the window = missed the trade.
3. **Slippage on entry/exit.** Market orders into volatile coins can slip 2-5%. This kills the R:R on tight exits.
4. **Fee bleed.** Coinbase charges 0.5-1% per trade. Tight exits (1-2 hour trades) lose 1-2% to fees alone.
5. **Rug pulls and halts.** Altcoins can disappear or halt trading. Hard stops may not fill.

---

## Monitoring Strategy

**Grafana Dashboard:** `paper_trader_s4`
- Live position table (symbol, gain/loss, elapsed time)
- Daily PnL per bot
- Trade log (entry/exit prices, realized gains)
- Win rate (7-day rolling)
- Max drawdown tracker
- Coinbase feed monitor (last updated Big Gainers/Losers)

**Alert Triggers:**
- Daily loss > 5%
- Any single trade > -30% loss
- Portfolio drawdown > 25%
- Both bots open 7+ concurrent positions simultaneously (over-leverage)

---

## Deployment Steps (Next)

1. **Spin up bot runners:**
   ```bash
   docker-compose up -d loser_reversal_hunter gainer_momentum_catcher
   ```

2. **Seed Coinbase API feeds:**
   - Call Coinbase API every 5 minutes for Big Gainers/Losers
   - Store in TimescaleDB for historical replay

3. **Wire Grafana:**
   - Import `S4_GRAFANA_DASHBOARD.json` into Grafana
   - Verify data is flowing from TimescaleDB

4. **Test with 0.001 BTC:**
   - Run both bots with tiny capital for 24 hours
   - Verify entry/exit logic, fee calculations, position tracking
   - Check Grafana dashboard accuracy

5. **Go live with 0.015 BTC:**
   - Scale to full capital per bot
   - Monitor daily; adjust rules based on real market conditions

---

## Success Criteria

- **Both bots live and executing trades within 24 hours**
- **Grafana dashboard showing real position data**
- **No untracked losses or orphaned positions**
- **First week break-even or better (account for learning curve)**
- **Monthly target of +15-25% achieved by end of April**

---

## Notes for Future Seasons

- **Season 4 is the apex of degenerate trading.** If this blows up, Season 5 should dial it back (maybe 30% max risk per trade, not 50%).
- **Coinbase Big Gainers/Losers is finite data.** If crypto market becomes less volatile, these bots will struggle. Consider adding DexScreener feeds for Solana/pump.fun tokens as backup.
- **Multiple concurrent positions increase compounding but also drawdown speed.** 3-4 positions is the sweet spot; beyond that is diminishing returns.

> *"Season 4: Where boring risk management goes to die."*

---

**Status:** Ready for deployment  
**Capital:** 0.03 BTC total allocated  
**Approval:** Launch live on Coinbase paper trading  
**Monitoring:** 24/7 Grafana dashboard  
