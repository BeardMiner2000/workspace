const express = require('express');
const fetch = require('node-fetch');
const path = require('path');

const app = express();
const PORT = process.env.PORT || 3001;

const GRAFANA_URL = process.env.GRAFANA_URL || 'http://localhost:3000';
const GRAFANA_API_KEY = process.env.GRAFANA_API_KEY || '';

app.use(express.static(path.join(__dirname, 'public')));

// Proxy dashboard data
app.get('/api/dashboard', async (req, res) => {
  try {
    const response = await fetch(`${GRAFANA_URL}/api/dashboards/db/master-summary`, {
      headers: {
        'Authorization': `Bearer ${GRAFANA_API_KEY}`,
        'Content-Type': 'application/json',
      },
    });
    const data = await response.json();
    res.json(data);
  } catch (error) {
    console.error('Error fetching dashboard:', error);
    res.status(500).json({ error: 'Failed to fetch dashboard' });
  }
});

// Proxy TimescaleDB query results
app.get('/api/query/:name', async (req, res) => {
  const queries = {
    'season-2-stats': 'SELECT COUNT(DISTINCT bot_id) as active_bots, SUM(equity_btc) as total_equity FROM (SELECT DISTINCT ON (bot_id) bot_id, equity_btc FROM bot_metrics WHERE season_id = \'season-002\' ORDER BY bot_id, ts DESC) t;',
    'season-3-stats': 'SELECT COUNT(DISTINCT bot_id) as active_bots, SUM(equity_btc) as total_equity FROM (SELECT DISTINCT ON (bot_id) bot_id, equity_btc FROM bot_metrics WHERE season_id = \'season-003\' ORDER BY bot_id, ts DESC) t;',
    'season-4-stats': 'SELECT COUNT(DISTINCT bot_id) as active_bots, SUM(equity_btc) as total_equity FROM (SELECT DISTINCT ON (bot_id) bot_id, equity_btc FROM bot_metrics WHERE season_id = \'season-004\' ORDER BY bot_id, ts DESC) t;',
    'global-stats': 'SELECT (SELECT SUM(equity_btc) FROM (SELECT DISTINCT ON (season_id, bot_id) season_id, bot_id, equity_btc FROM bot_metrics ORDER BY season_id, bot_id, ts DESC) t) as total_equity, (SELECT COUNT(*) FROM bot_orders WHERE status = \'filled\') as total_orders;',
  };

  const sql = queries[req.params.name];
  if (!sql) {
    return res.status(404).json({ error: 'Query not found' });
  }

  try {
    // In production, you'd query TimescaleDB directly or via Grafana's API
    res.json({ query: req.params.name, status: 'Use Grafana embedded dashboard or set up direct DB access' });
  } catch (error) {
    console.error('Error executing query:', error);
    res.status(500).json({ error: 'Failed to execute query' });
  }
});

app.listen(PORT, () => {
  console.log(`Public dashboard server running on port ${PORT}`);
  console.log(`Point your browser to http://localhost:${PORT}`);
  console.log(`Grafana: ${GRAFANA_URL}`);
});
