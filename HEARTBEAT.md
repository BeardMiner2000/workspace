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

### Paper Trader League — Season 4 🏆 CHAMPIONSHIP LIVE
- **Status:** 🟢 **ACTIVE & EXECUTING** — 12 bots trading continuously
- **Start Time:** 2026-03-26 03:02:24 UTC (March 25, 20:02 PDT)
- **End Time:** 2026-03-29 03:02:24 UTC (March 29, 20:02 PDT) — 72 hours
- **Capital:** 487.5 USDT per bot (0.0075 BTC equivalent, $65k/BTC) = 5,850 USDT total
- **Activity:** 156+ orders executed, all 12 bots actively trading
- **Leader:** Mercury Vanta (18 trades, HFT), Aurora Quanta (16 trades, macro)
- **Monitoring:** Grafana http://localhost:3000/d/season4-championship
- **Winner:** Highest BTC equity at end (no liquidation required)

## Periodic reminders
- After any significant work session, write a summary to `memory/YYYY-MM-DD.md`
- If a webchat session feels long or substantive, write key decisions/context to memory before it rotates
- If a conversation creates a new durable preference/process/project milestone, update `MEMORY.md` or `memory/chat-index.md` too
- When resuming older work or when the prompt mentions prior context, search historical session logs via `scripts/session_memory.py` before relying on memory alone
- During heartbeats, if there has been meaningful recent activity, run `python3 scripts/chat_memory_rollup.py --llm-limit 1` to refresh local summaries, selective LLM summaries, and project memory
- If a project is being resumed, use `python3 scripts/session_memory.py project "<topic>"` or `./scripts/project_context.sh "<topic>"` to pull likely prior context before starting

## Smart Batching Rules (Cost Control)
- **Bundle periodic checks:** Email + Calendar + Weather in ONE heartbeat turn, not separate cron jobs
- **Rotate what you check:** Email (every heartbeat) → Calendar (every other) → Weather (if going out)
- **Use local tools first:** grep, jq, SQL queries before calling any LLM
- **Context chunking:** Never pass raw CSVs/files. Query → summarize (10-20 lines) → pass to LLM
- **Subagent defaults:** Always use haiku unless you explicitly need Codex/Sonnet (tag with `model=` when spawning)
- **Use pace-aware chat rotation:** low pace can stay open much longer; heavy technical work should codify earlier and rotate sooner

## Chat Pace Policy
- Track heuristic state in `memory/chat-pace-state.json`
- Use `scripts/chat_pace.py status` to inspect current cadence
- Use `scripts/chat_pace.py assess` to decide stay vs codify vs rotate
- Use `scripts/chat_pace.py bump ...` during heavier work if useful (tool/log/decision/recovery/project signals)
- Use `scripts/chat_pace.py codified` after a memory rollup
- Preferred cadence:
  - low pace → codify ~3h, rotate ~4h
  - medium pace → codify ~75m, rotate ~105m
  - heavy pace → codify ~40m, rotate ~75m
- On project switch or major milestone, codify immediately even if the timer has not elapsed

## Cost Tracking
- Run `./scripts/cost-tracker.sh summary` during heartbeats to monitor daily usage
- Alert threshold: Pause and check if any single model hits >$5/day
- When approaching limit: Switch to free models (Gemini, Grok) or use local Llama
