# HEARTBEAT.md

## Active Projects

### Still Mode (macOS) 🚀 TESTING PHASE
- **Status:** v1.0 UI bugs fixed (popup window, multi-select, state persistence). Ready for final user testing.
- **Location:** `workspace/stillmode/`
- **Build:** `/Users/jl/Library/Developer/Xcode/DerivedData/StillMode-.../Build/Products/Release/StillMode.app`
- **Latest fixes:** Popup window stays open, checkboxes persist, multi-select works
- **Next steps:** JL final testing → Code signing → Notarization → Gumroad setup

### Still Mode (iOS) 📋 PROTOTYPE READY
- **Status:** MVP code complete, ready for Xcode integration
- **Location:** `StillModeIOS/`
- **Ready when:** Launch macOS first, then iOS as v1.1

### Paper Trader League — Season 4 🎯 LIVE
- **Status:** Two new bots deployed (Loser Reversal Hunter, Gainer Momentum Catcher)
- **Capital:** 0.03 BTC total (0.015 BTC each)
- **Strategy:** Extreme volatility (50% risk per trade) on Coinbase Big Gainers/Losers
- **Dashboard:** Grafana `paper_trader_s4` (live PnL, positions, trade log)
- **Launch:** March 25, 2026, 15:57 PDT
- **Target:** +15-25% monthly gains

## Periodic reminders
- After any significant work session, write a summary to `memory/YYYY-MM-DD.md` (done)
- If a webchat session feels long or substantive, write key decisions/context to memory before it rotates (done)

## Smart Batching Rules (Cost Control)
- **Bundle periodic checks:** Email + Calendar + Weather in ONE heartbeat turn, not separate cron jobs
- **Rotate what you check:** Email (every heartbeat) → Calendar (every other) → Weather (if going out)
- **Use local tools first:** grep, jq, SQL queries before calling any LLM
- **Context chunking:** Never pass raw CSVs/files. Query → summarize (10-20 lines) → pass to LLM
- **Subagent defaults:** Always use haiku unless you explicitly need Codex/Sonnet (tag with `model=` when spawning)

## Cost Tracking
- Run `./scripts/cost-tracker.sh summary` during heartbeats to monitor daily usage
- Alert threshold: Pause and check if any single model hits >$5/day
- When approaching limit: Switch to free models (Gemini, Grok) or use local Llama
