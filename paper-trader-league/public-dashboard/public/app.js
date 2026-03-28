const REFRESH_MS = 30000;
const palette = ['#4dd0e1', '#ffb84d', '#5ef2a3', '#ff7c7c', '#9a8cff', '#73a1ff'];

const state = {
  selectedSeasonId: null,
  data: null,
};

function formatNumber(value, digits = 4) {
  const numeric = Number(value || 0);
  return numeric.toFixed(digits);
}

function formatSigned(value, digits = 4) {
  const numeric = Number(value || 0);
  const prefix = numeric > 0 ? '+' : '';
  return `${prefix}${numeric.toFixed(digits)}`;
}

function formatInt(value) {
  return new Intl.NumberFormat().format(Number(value || 0));
}

function formatTimestamp(value) {
  if (!value) {
    return '--';
  }
  return new Date(value).toLocaleString();
}

function sideClass(side) {
  return String(side || '').toLowerCase();
}

function statusText(text) {
  return String(text || '--').replaceAll('_', ' ');
}

function metricCard(label, value, subtle) {
  return `
    <article class="metric-card">
      <div class="metric-label">${label}</div>
      <div class="metric-value">${value}</div>
      <div class="metric-subtle">${subtle}</div>
    </article>
  `;
}

function renderOverview(summary, seasonCount) {
  document.getElementById('overviewCards').innerHTML = [
    metricCard('Total Equity', `${formatNumber(summary.total_equity_btc)} BTC`, `${seasonCount} tracked seasons`),
    metricCard('Realized PnL', `${formatSigned(summary.total_realized_pnl_btc)} BTC`, 'Latest per-bot snapshot'),
    metricCard('Trades', formatInt(summary.total_trades), 'Filled and open orders recorded'),
    metricCard('Active Bots', formatInt(summary.total_bots), 'Bots with current metrics'),
    metricCard('Last Metric', formatTimestamp(summary.last_metric_at), 'Most recent server-side datapoint'),
  ].join('');
}

function renderSeasonTabs(seasons) {
  const container = document.getElementById('seasonTabs');
  container.innerHTML = seasons
    .map((season) => `
      <button class="season-tab ${season.season_id === state.selectedSeasonId ? 'active' : ''}" data-season-id="${season.season_id}">
        ${season.season_id}
      </button>
    `)
    .join('');

  Array.from(container.querySelectorAll('[data-season-id]')).forEach((button) => {
    button.addEventListener('click', () => {
      const seasonId = button.getAttribute('data-season-id');
      if (seasonId && seasonId !== state.selectedSeasonId) {
        state.selectedSeasonId = seasonId;
        loadDashboard();
      }
    });
  });
}

function renderSeasonSummary(selectedSeason) {
  const container = document.getElementById('seasonSummary');
  if (!selectedSeason) {
    container.innerHTML = '<p class="empty">No season data available yet.</p>';
    return;
  }

  container.innerHTML = `
    <article class="season-card">
      <p class="season-kicker">Season</p>
      <strong>${selectedSeason.season_id}</strong>
      <p class="season-kicker">Status: ${selectedSeason.status || 'unknown'}</p>
    </article>
    <article class="season-card">
      <p class="season-kicker">Total Equity</p>
      <strong>${formatNumber(selectedSeason.total_equity_btc)} BTC</strong>
      <p class="season-kicker">${formatInt(selectedSeason.active_bots)} active bots</p>
    </article>
    <article class="season-card">
      <p class="season-kicker">Realized PnL</p>
      <strong class="${Number(selectedSeason.total_realized_pnl_btc) >= 0 ? 'positive' : 'negative'}">${formatSigned(selectedSeason.total_realized_pnl_btc)} BTC</strong>
      <p class="season-kicker">${formatInt(selectedSeason.total_trades)} total trades</p>
    </article>
    <article class="season-card">
      <p class="season-kicker">Last Update</p>
      <strong>${formatTimestamp(selectedSeason.last_metric_at)}</strong>
      <p class="season-kicker">Base asset: ${selectedSeason.base_asset || 'BTC'}</p>
    </article>
  `;
}

function renderLeaderboard(leaderboard) {
  const body = document.getElementById('leaderboardRows');
  if (!leaderboard.length) {
    body.innerHTML = '<tr><td colspan="6" class="empty">No leaderboard rows yet.</td></tr>';
    return;
  }

  body.innerHTML = leaderboard
    .map((row) => `
      <tr>
        <td>
          <div class="bot-cell">
            <strong>${row.bot_name || row.bot_id}</strong>
            <span class="mono">${row.bot_id}</span>
          </div>
        </td>
        <td class="mono">${formatNumber(row.equity_btc)} BTC</td>
        <td class="mono ${Number(row.realized_pnl_btc) >= 0 ? 'positive' : 'negative'}">${formatSigned(row.realized_pnl_btc)} BTC</td>
        <td class="mono">${formatInt(row.trade_count)}</td>
        <td class="mono">${Number(row.drawdown_pct || 0).toFixed(2)}%</td>
        <td class="mono">${formatTimestamp(row.ts)}</td>
      </tr>
    `)
    .join('');
}

function renderOrders(orders) {
  const body = document.getElementById('orderRows');
  if (!orders.length) {
    body.innerHTML = '<tr><td colspan="7" class="empty">No orders available yet.</td></tr>';
    return;
  }

  body.innerHTML = orders
    .map((order) => `
      <tr>
        <td class="mono">${formatTimestamp(order.ts)}</td>
        <td class="mono">${order.bot_id}</td>
        <td class="mono">${order.symbol}</td>
        <td><span class="pill ${sideClass(order.side)}">${statusText(order.side)}</span></td>
        <td class="mono">${statusText(order.status)}</td>
        <td class="mono">${formatNumber(order.executed_quantity || order.requested_quantity)}</td>
        <td class="mono">${formatNumber(order.executed_price || order.request_price)}</td>
      </tr>
    `)
    .join('');
}

function renderChart(history) {
  const wrap = document.getElementById('equityChart');
  if (!history.length) {
    wrap.innerHTML = '<p class="empty">No equity history available yet.</p>';
    return;
  }

  const width = 1120;
  const height = 320;
  const padding = { top: 20, right: 24, bottom: 36, left: 56 };
  const bots = Array.from(new Set(history.map((point) => point.bot_id)));
  const grouped = new Map(bots.map((bot) => [bot, history.filter((point) => point.bot_id === bot)]));
  const values = history.map((point) => Number(point.equity_btc || 0));
  const timestamps = Array.from(new Set(history.map((point) => point.ts)));
  const timestampIndex = new Map(timestamps.map((timestamp, index) => [timestamp, index]));
  const minValue = Math.min(...values);
  const maxValue = Math.max(...values);
  const span = maxValue - minValue || 1;
  const totalPoints = Math.max(timestamps.length - 1, 1);

  const xForIndex = (index) => padding.left + (index / totalPoints) * (width - padding.left - padding.right);
  const yForValue = (value) => padding.top + ((maxValue - value) / span) * (height - padding.top - padding.bottom);

  const lines = bots.map((bot, botIndex) => {
    const points = grouped.get(bot).map((point) => `${xForIndex(timestampIndex.get(point.ts) || 0)},${yForValue(Number(point.equity_btc || 0))}`);
    return `<polyline class="chart-line" stroke="${palette[botIndex % palette.length]}" points="${points.join(' ')}"></polyline>`;
  }).join('');

  const tickValues = [maxValue, minValue + span * 0.5, minValue];
  const grid = tickValues.map((value) => {
    const y = yForValue(value);
    return `
      <line class="chart-grid" x1="${padding.left}" x2="${width - padding.right}" y1="${y}" y2="${y}"></line>
      <text class="chart-label" x="10" y="${y + 4}">${value.toFixed(4)} BTC</text>
    `;
  }).join('');

  wrap.innerHTML = `
    <svg class="chart-svg" viewBox="0 0 ${width} ${height}" role="img" aria-label="Equity chart">
      ${grid}
      ${lines}
    </svg>
    <div class="chart-legend">
      ${bots.map((bot, index) => `
        <span class="legend-item">
          <span class="legend-swatch" style="background:${palette[index % palette.length]}"></span>
          ${bot}
        </span>
      `).join('')}
    </div>
  `;
}

function showError(message) {
  const errorCard = document.getElementById('errorCard');
  errorCard.textContent = message;
  errorCard.classList.remove('hidden');
  document.getElementById('statusChip').textContent = 'Degraded';
}

function clearError() {
  const errorCard = document.getElementById('errorCard');
  errorCard.textContent = '';
  errorCard.classList.add('hidden');
}

async function loadDashboard() {
  const params = new URLSearchParams();
  if (state.selectedSeasonId) {
    params.set('season_id', state.selectedSeasonId);
  }

  try {
    document.getElementById('statusChip').textContent = 'Refreshing';
    const response = await fetch(`/api/dashboard?${params.toString()}`);
    const payload = await response.json();
    if (!response.ok) {
      throw new Error(payload.detail || payload.error || 'Dashboard request failed');
    }

    state.data = payload;
    state.selectedSeasonId = payload.meta.selected_season_id || state.selectedSeasonId;
    renderOverview(payload.summary, payload.seasons.length);
    renderSeasonTabs(payload.seasons);
    renderSeasonSummary(payload.selectedSeason);
    renderLeaderboard(payload.leaderboard);
    renderOrders(payload.recentOrders);
    renderChart(payload.equityHistory);

    document.getElementById('statusChip').textContent = 'Live';
    document.getElementById('sourceChip').textContent = payload.meta.data_source || '--';
    document.getElementById('updatedChip').textContent = formatTimestamp(payload.meta.generated_at);
    clearError();
  } catch (error) {
    showError(error.message);
  }
}

loadDashboard();
setInterval(loadDashboard, REFRESH_MS);
