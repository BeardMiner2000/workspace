# MEMORY.md — Long-Term Memory

## Projects

### Still Mode (stillmode.app)
- **What:** macOS menubar focus app. 🌙 icon → pick one app → everything else hides + DND on. Click to exit and restore.
- **Code:** `workspace/stillmode/` — Swift/AppKit, compiles clean, no external deps
- **Launch plan:** $2.99, direct sale (NOT App Store — 30% cut + sandboxing conflicts with Accessibility entitlements). Use Gumroad or Lemon Squeezy.
- **Domain:** `stillmode.app` was the idea
- **Status:** Built March 20, 2026. Needs: Accessibility permission granted, end-to-end testing, notarization, sales page.
- **Built in:** Xcode, arm64, macOS 13+ target

### Paper Trader / Tuque
- Live trading experiment with multiple bot strategies on Coinbase
- Launch target: Monday March 24 2026
- Capital: 0.015 BTC per bot
- Stack: Docker + TimescaleDB + Grafana, `paper-trader-league/`

## Setup / Identity
- Name: Neon Cortex 🤖
- Signal connected and working (+14158272563 is JL's number)
- Model: Claude Sonnet via OpenClaw on JL's MacBook Pro

## NEW STANDARD (Mar 28, 2026) 🚀

### Paper Trader League - LIVE & OPERATIONAL

**All Three Seasons Running Continuously:**
- **Season 2:** 4 bots (obsidian_flux, solstice_drift, phantom_lattice, vega_pulse) — actively trading
- **Season 3:** 3 bots (degen_ape_9000, pump_surfer, chaos_prophet) — actively trading
- **Season 4:** 2 bots (loser_reversal_hunter, gainer_momentum_catcher) — running via backup executor (marks-only strategy)
  - Aggressive: 75% position size per trade if justified
  - Max concurrent: 2 positions per bot
  - Entry on timeframe-based thresholds (15m, 1h, 4h, 24h moves)

**Executor Status:**
- Season 2/3: Original data_ingest + trade_engine pipeline
- Season 4: `main_backup.py` executor (simpler, marks-only, proven working after 3 prior iterations)
  - No dependency on brittle Big Gainers/Losers feeds
  - Avoids micro-order spam with proper cooldowns

**Dashboard & Monitoring:**
- Grafana on localhost:3000
- New master-summary dashboard aggregates all three seasons
- Public web app ready for Render/Cloudflare hosting
- Import master-summary.json into Grafana to view

**Trading Metrics (as of 2026-03-28 15:10 UTC):**
- S2: 360-374 orders per bot, continuous trading
- S3: 33-183 orders per bot, continuous trading
- S4: 4-6 orders per bot (recent activity, backup executor just launched)

### What Works Now (Don't Break It)
1. Season 2/3 keep running via original pipeline — zero changes needed
2. Season 4 runs via backup executor — simpler, faster to debug if issues arise
3. Chat rotation + memory system fully automated
4. Public dashboard infrastructure ready for remote viewing

## Model Routing Strategy (Mar 25, 2026 — LIVE)
**Your arsenal:** Codex (primary), Sonnet (fallback), Haiku (subagents), + **Grok (free, web)**, Gemini (ready), local Llama (ready).

**Tier 1 (Free/Local)**
- **Grok** ✅ LIVE: web research, trends, current events, real-time data (free)
- **Gemini** 📋 Ready: simple summaries, categorization (needs API key)
- **Local Llama** 📋 Ready: file reading, regex, transforms (zero API cost)

**Tier 2 (Haiku — Fast & Cheap)**
- Analysis, filtering, categorization, quick decisions
- Default for all subagents

**Tier 3 (Heavy Lifting)**
- **Codex** as PRIMARY: code generation, complex reasoning, architecture
- **Sonnet** as FALLBACK: when Codex busy or need Anthropic-specific strengths
- **GPT-5.4 Turbo** as LAST RESORT: only when above unavailable

**Orchestration Rules:**
1. **Use Grok for web research** — free, real-time, no token budget impact
2. Batch periodic checks (email+calendar+weather in one heartbeat)
3. Use local tools (grep, jq, SQL) before calling any LLM
4. Context chunk: summaries (10-20 lines), never raw files
5. Monitor cost daily via `scripts/cost-tracker.sh summary`
6. Alert if any paid model hits >$5/day

## Lessons Learned
- **Session rotation = memory loss.** Webchat sessions rotate and old ones get `.deleted` overnight. Always write key decisions to `memory/YYYY-MM-DD.md` during or right after a significant session. Don't trust the dashboard chat history to persist.
- **Use indexed memory, not hope.** For older context: check `memory/chat-index.md`, then search session archives with `scripts/session_memory.py` / the session-logs skill before guessing what happened in prior chats.
- **Isolate LLM transcript summarization.** Directly invoking the active main-session lane can hit session-lock conflicts; higher-quality transcript summaries should run in isolated subagent/session flows.
- **Use pace-based chat rotation.** Low-work chats can stay open longer; medium/heavy technical chats should codify sooner and rotate earlier based on lightweight heuristic signals rather than vibes alone.
- **When JL’s intent is clear, act instead of permission-looping.** If JL asks for an analysis, projection, or follow-through that obviously implies doing the work, proceed directly and present the result rather than asking for confirmation first.
- Never commit secrets (.env files) — Coinbase API key lives only in paper-trader-league/.env
- **Token bleed from loose subagent spawning.** Haiku defaults prevent runaway costs. Always explicit upgrades to Codex/Sonnet.
