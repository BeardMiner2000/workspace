# Hosting the Public Dashboard

## Option 1: Render (Recommended for Beginners)

### Step 1: Prepare Your Repository
1. Commit your public-dashboard folder to GitHub:
```bash
cd /Users/jl/.openclaw/workspace/paper-trader-league
git add public-dashboard/
git commit -m "Add public dashboard"
git push origin main
```

### Step 2: Create Render Web Service
1. Go to [render.com](https://render.com)
2. Sign up with GitHub account
3. Click "New +" → "Web Service"
4. Connect your GitHub repo
5. Select the repository containing public-dashboard
6. Configure:
   - **Name:** `paper-trader-dashboard`
   - **Environment:** Node
   - **Build Command:** `npm install`
   - **Start Command:** `npm start`
   - **Plan:** Free tier is fine for testing

### Step 3: Set Environment Variables
In Render dashboard, go to Environment and add:
```
GRAFANA_URL=http://your-grafana-public-url:3000
GRAFANA_API_KEY=your-grafana-api-key-here
PORT=3000
```

### Step 4: Deploy
Click "Create Web Service" and wait for deployment (~2 minutes)

Your dashboard will be available at: `https://paper-trader-dashboard.onrender.com`

---

## Option 2: Cloudflare Pages + Workers

### Step 1: Set Up Cloudflare Pages
1. Go to [pages.cloudflare.com](https://pages.cloudflare.com)
2. Connect your GitHub repo
3. Select `public-dashboard` as the build output directory
4. Deploy

### Step 2: Create Cloudflare Worker for API Proxy (Optional)
If you want to proxy Grafana API calls:

**wrangler.toml:**
```toml
name = "paper-trader-proxy"
main = "src/index.ts"
compatibility_date = "2024-01-01"

[env.production]
route = "api.example.com/*"
```

**src/index.ts:**
```typescript
export default {
  async fetch(request: Request) {
    if (request.url.includes('/api/')) {
      const grafanaUrl = 'http://your-grafana-url:3000';
      const path = new URL(request.url).pathname.replace('/api/', '/api/');
      return fetch(grafanaUrl + path, {
        headers: {
          'Authorization': `Bearer ${GRAFANA_API_KEY}`,
        }
      });
    }
    return fetch(request);
  }
};
```

---

## Option 3: Self-Hosted via Nginx Reverse Proxy

If you want to host on your own server:

### Step 1: Install Node on Server
```bash
curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash -
sudo apt-get install -y nodejs
```

### Step 2: Deploy Dashboard
```bash
git clone <your-repo> /opt/paper-trader-dashboard
cd /opt/paper-trader-dashboard/public-dashboard
npm install
pm2 start server.js --name "paper-trader-dashboard"
```

### Step 3: Nginx Config
```nginx
server {
  listen 80;
  server_name dashboard.yourdomain.com;

  location / {
    proxy_pass http://localhost:3001;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
  }

  location /grafana/ {
    proxy_pass http://localhost:3000/;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
  }
}
```

---

## Grafana Authentication for Remote Access

To allow public access safely:

1. **Create API Token in Grafana:**
   - Go to `http://localhost:3000/org/apikeys`
   - Click "New API key"
   - Select "Viewer" role
   - Copy the token

2. **Enable Anonymous Access (Optional):**
   - Edit `/etc/grafana/grafana.ini`:
   ```ini
   [auth.anonymous]
   enabled = true
   org_role = Viewer
   ```

3. **Set CORS Headers (if needed):**
   ```nginx
   add_header 'Access-Control-Allow-Origin' '*';
   add_header 'Access-Control-Allow-Methods' 'GET, OPTIONS';
   ```

---

## Quick Local Testing

```bash
cd public-dashboard
npm install
GRAFANA_URL=http://localhost:3000 npm start
# Visit http://localhost:3001
```

---

## Troubleshooting

**"Cannot connect to Grafana"**
- Check that Grafana is running: `docker compose ps grafana`
- Verify URL is correct
- Check API key has correct permissions

**"Dashboard not found"**
- Ensure master-summary.json is imported in Grafana
- Check dashboard UID matches in queries

**"Port already in use"**
- Change PORT env var: `PORT=3002 npm start`

---

## Next Steps

1. **Custom Branding:** Edit `public/index.html` to add your logo/colors
2. **Real-time Updates:** Wire up WebSocket connection to TimescaleDB for live data
3. **Mobile App:** Build React Native app wrapping the dashboard
4. **Alerts:** Add Slack/email notifications for trading milestones
