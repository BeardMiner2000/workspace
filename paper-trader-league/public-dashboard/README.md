# Paper Trader League - Public Dashboard

Clean, graphical master dashboard that aggregates all three trading seasons (Season 2, 3, 4) in real-time.

## What's Included

- **Master Summary Dashboard** (`infra/grafana/dashboards/master-summary.json`)
  - All-season equity overview
  - Combined trading metrics
  - Per-season bot status tables
  - Recent orders feed
  - Daily order volume trends

- **Public Web App** (this directory)
  - Lightweight Node/Express server
  - Simple, responsive UI
  - Directs to Grafana or proxies API calls
  - Easy to deploy to Render/Cloudflare/self-hosted

## Quick Start (Local)

```bash
# Install dependencies
npm install

# Start with local Grafana
GRAFANA_URL=http://localhost:3000 npm start

# Visit http://localhost:3001
```

## Deploy to Render (30 seconds)

1. Push to GitHub:
```bash
git add public-dashboard/
git commit -m "Add public dashboard"
git push origin main
```

2. Go to [render.com](https://render.com)
3. Create Web Service from your repo
4. Set start command: `npm start`
5. Add env vars:
   - `GRAFANA_URL=http://localhost:3000`
   - `GRAFANA_API_KEY=<your-api-key>`
6. Deploy!

Your dashboard will be at: `https://paper-trader-dashboard.onrender.com`

## Deploy to Cloudflare Pages (1 minute)

1. Connect GitHub repo to [pages.cloudflare.com](https://pages.cloudflare.com)
2. Set build output to `public/`
3. Deploy

## Self-Host with Nginx (see HOSTING.md)

---

## Features

✅ Real-time season metrics  
✅ Equity growth charts  
✅ Per-bot performance tables  
✅ Recent order feed (all seasons)  
✅ Daily order volume trends  
✅ Mobile responsive  
✅ Dark theme  
✅ Zero JavaScript bloat  

---

## Import Master Dashboard into Grafana

1. Go to Grafana: `http://localhost:3000`
2. Click "Dashboards" → "New" → "Import"
3. Upload `infra/grafana/dashboards/master-summary.json`
4. Select TimescaleDB as data source
5. Done!

---

## Architecture

```
Public Web App (Node/Express)
        ↓
    http://localhost:3001
        ↓
   Serve static HTML/CSS
        ↓
   User's Browser
        ↓
   Points to Grafana at :3000
        ↓
   TimescaleDB queries
```

---

## Environment Variables

| Var | Default | Notes |
|-----|---------|-------|
| `PORT` | 3001 | Express server port |
| `GRAFANA_URL` | http://localhost:3000 | Grafana instance URL |
| `GRAFANA_API_KEY` | (empty) | Optional: for API proxying |

---

## Customization

Edit `public/index.html` to:
- Change colors (CSS variables)
- Add your logo
- Adjust layout
- Add custom sections

See HOSTING.md for detailed guides.
