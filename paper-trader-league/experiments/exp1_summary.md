# Experiment 1 — Post-Mortem Summary

**Season:** season-001
**Duration:** ~30 hours (2026-03-18 18:36 UTC → 2026-03-20 00:32 UTC)
**Market:** Real Coinbase prices
**Starting capital:** 0.05 BTC per bot
**Fees:** 4.875 bps taker (Coinbase One)

## Market Conditions
- BTC range: $68,789 → $71,741 (+4.29% range, net slightly down from open)
- Flat to mildly bearish session — not trending, lots of chop

## Final Results

| Bot | Final Equity | PnL | Trades | Fees Paid | Drawdown |
|-----|-------------|-----|--------|-----------|----------|
| mercury_vanta | 0.05010 BTC | +0.00010 (+0.21%) | 44 | 0.0000205 BTC | 0.22% |
| aurora_quanta | 0.03224 BTC | -0.01775 (-35.5%) | 9,582 | 0.01200 BTC | 35.5% |
| stormchaser_delta | 0.00472 BTC | -0.04528 (-90.6%) | 2,655 | 0.00204 BTC | 90.6% |

## Key Findings
1. All losses were fee-driven, not market-driven — fake synthetic signals caused massive overtrading
2. aurora placed 9,582 orders in 30 hours = ~320 orders/hour = ~5/min — pure fee drain
3. stormchaser nearly wiped — down 90%. Short-selling added late but thresholds too tight, only 35 shorts / 5 covers attempted
4. mercury won by barely trading. 44 trades, lowest fees, only bot in the green

## Data Files
- exp1_bot_metrics.csv — 64,094 equity snapshots
- exp1_orders.csv — 12,284 order records
- exp1_market_marks.csv — 69,076 price marks
