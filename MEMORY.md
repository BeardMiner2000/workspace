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

## Lessons Learned
- **Session rotation = memory loss.** Webchat sessions rotate and old ones get `.deleted` overnight. Always write key decisions to `memory/YYYY-MM-DD.md` during or right after a significant session. Don't trust the dashboard chat history to persist.
- Never commit secrets (.env files) — Coinbase API key lives only in paper-trader-league/.env
