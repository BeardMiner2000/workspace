# 📊 Import Season 4 Grafana Dashboard

## Quick Import (2 minutes)

### Step 1: Copy Dashboard JSON
```bash
cat /Users/jl/.openclaw/workspace/paper-trader-league/infra/grafana/dashboards/season4-championship.json
```

### Step 2: Open Grafana
- Go to: **http://localhost:3000**
- Login (default: admin/admin)

### Step 3: Import Dashboard
1. Click **+** (top left)
2. Select **Import**
3. Paste the JSON from step 1
4. Click **Load**
5. Select **TimescaleDB** as datasource
6. Click **Import**

### Done! 🎉

You now have a live Season 4 dashboard with:
- ✅ All 12 bots with custom colors
- ✅ Emojis in legend (🚀 📈 💥 etc.)
- ✅ Real-time equity tracking
- ✅ PnL % charts
- ✅ Trade counts
- ✅ Auto-refresh every 10 seconds

---

## What You'll See

### Panel 1: Bot Equity (Main Leaderboard)
- **Lines:** One per bot, color-coded
- **Legend:** Shows emoji + bot name
- **Stats:** Mean, Max displayed in table
- **Refresh:** 10 seconds

### Panel 2: Realized PnL %
- **Bars:** Each bot's percentage gain/loss
- **Color:** Same as equity chart
- **Unit:** Percent

### Panel 3: Trade Count
- **Bars:** Cumulative trades per bot
- **Shows:** HFT bots vs. patient traders

---

## Bot Colors Used

| Bot | Color | Emoji |
|-----|-------|-------|
| Loser Reversal Hunter | 🔴 Red #FF6B6B | 🚀 |
| Gainer Momentum Catcher | 🟦 Teal #4ECDC4 | 📈 |
| Degen Ape 9000 | 🟨 Gold #FFD93D | 💥 |
| Pump Surfer | 🟥 Coral #FF8B94 | 🌊 |
| StormChaser Delta | 🟪 Purple #6C5CE7 | ⚡ |
| Chaos Prophet | 🟪 Lt Purple #A29BFE | 🌪️ |
| Aurora Quanta | 🟩 Green #00B894 | 🌍 |
| Vega Pulse | 🟧 Orange #FFA502 | 🌀 |
| Obsidian Flux | ⬛ Dark Slate #2C3E50 | 👻 |
| Phantom Lattice | 🟩 Mint #95E1D3 | 🪟 |
| Solstice Drift | 🟦 Lt Blue #74B9FF | 🌙 |
| Mercury Vanta | 🟥 Hot Pink #FD79A8 | 💎 |

---

## Customizing the Dashboard

### Change Refresh Rate
1. Click gear icon (top right)
2. **Refresh interval** → Select new rate
3. Default: 10 seconds

### Adjust Time Window
- **Top right:** Change from "now-72h" to any range
- For live: Set to "last 1h" with auto-refresh

### Add/Remove Panels
1. Click **+** icon on dashboard
2. Add new visualization
3. Write SQL query against `bot_metrics` table

---

## Useful SQL Queries

### Current Leaderboard (Last Snapshot)
```sql
SELECT DISTINCT ON (bot_id) 
  bot_id, equity_btc, realized_pnl_btc, trade_count
FROM bot_metrics
WHERE season_id = 'season-004'
ORDER BY bot_id, ts DESC;
```

### Drawdown Over Time
```sql
SELECT time, bot_id, drawdown_pct
FROM bot_metrics
WHERE season_id = 'season-004'
ORDER BY time DESC
LIMIT 1000;
```

### Trade History
```sql
SELECT created_at, bot_id, symbol, side, quantity, realized_pnl_btc
FROM bot_orders
WHERE season_id = 'season-004'
ORDER BY created_at DESC
LIMIT 100;
```

---

## Troubleshooting

### Colors Not Showing?
- Ensure **TimescaleDB datasource** is selected
- Check that data is flowing: Query `SELECT COUNT(*) FROM bot_metrics WHERE season_id = 'season-004'`
- Refresh browser (Ctrl+F5)

### No Data?
- Make sure bot executor is running
- Check `docker-compose logs bot_executor`
- Verify `season_id = 'season-004'` in database

### Emojis Not Showing in Legend?
- They should appear as-is in legend
- If not, it's a font issue (not critical)
- Colors will still be correct

---

## File Location

```
/Users/jl/.openclaw/workspace/paper-trader-league/infra/grafana/dashboards/season4-championship.json
```

This file is automatically provisioned by Docker if you update the docker-compose volumes.

---

**Ready to monitor the championship!** 🏆
