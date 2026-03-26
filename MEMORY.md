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
- Never commit secrets (.env files) — Coinbase API key lives only in paper-trader-league/.env
- **Token bleed from loose subagent spawning.** Haiku defaults prevent runaway costs. Always explicit upgrades to Codex/Sonnet.
