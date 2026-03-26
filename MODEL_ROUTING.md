# MODEL_ROUTING.md — Your LLM Strategy (Mar 25, 2026)

## Quick Reference

**Default when spawning:**
- Main session: **Codex** (openai-codex/gpt-5.4) — heavy reasoning, code, complex tasks
- Subagents: **Haiku** (anthropic/claude-haiku-4-5) — analysis, filtering, summaries
- Web research: **Grok** (xai/grok) — free, real-time, trends, current events
- Fallback chain: Codex → Sonnet → GPT-5.4 → Haiku

**To override:** `sessions_spawn(..., model="grok")` or `sessions_spawn(..., model="haiku")`

---

## The Tiers

### Tier 1: Free / No API Cost
Use these first when relevant. No token budget impact.

| Model | Use Case | Pro | Con | Status |
|-------|----------|-----|-----|--------|
| **Grok** | Web research, trends, real-time events, current news | Free, latest info, good reasoning | Rate limits | ✅ LIVE |
| **Gemini** | Simple summaries, categorization, lookups | Free, good at summaries | Can be slow | 📋 Ready (needs key) |
| **Local Llama** | File reading, regex, basic transforms | Zero API cost | No internet, limited reasoning | 📋 Ready (needs setup) |

**Decision rule:** 
- Web research / trends / current events → **Grok** (free tier available)
- Simple summarization / categorization → **Gemini** (when available)
- Local file work / regex / transforms → **Local Llama** (zero cost)

---

### Tier 2: Haiku (Fast & Cheap)
Anthropic's lightweight model. ~95% cheaper than Sonnet, fast enough for most analysis.

| Use Case | Why Haiku |
|----------|-----------|
| CSV analysis & summaries | Fast, accurate for structured data |
| Text filtering & categorization | Cheap, good recall |
| Multi-choice logic | Reliable, quick |
| Subagent analysis tasks | Default to this |

**When NOT to use Haiku:**
- Code generation (use Codex)
- Multi-step architecture (use Sonnet)
- Very complex reasoning (use Sonnet)

---

### Tier 3: Heavy Lifting

#### **Codex (Primary)**
OpenAI's code-specialized Codex. Your strongest tool for:
- Code generation & refactoring
- Complex multi-step reasoning
- Architecture & design decisions
- Anything that needs "deep thinking"

**Cost:** Higher than Haiku/Sonnet, but worth it for tasks that need it.

**When to use:** Code work, system design, or problems that need creative problem-solving.

---

#### **Sonnet (Anthropic Fallback)**
Claude's mid-tier reasoning model. Use when:
- Codex is unavailable (check Anthropic status)
- Need Anthropic-specific capabilities (e.g., artifact handling)
- Task is reasoning-heavy but not code-focused

**Cost:** Moderate. Less than Codex, more than Haiku.

---

#### **GPT-5.4 (Last Resort)**
Use only if Codex and Sonnet are both unavailable.

---

## Cost Management Rules

### 1. **Always Default to Haiku for Subagents**
```bash
# ✅ Good — uses haiku by default
sessions_spawn(task="analyze this CSV", runtime="subagent")

# ❌ Bad — wastes Sonnet on simple analysis
sessions_spawn(task="analyze this CSV", runtime="subagent", model="sonnet")
```

### 2. **Explicit Upgrades Only**
```bash
# ✅ Good — explicit upgrade for code generation
sessions_spawn(task="write a new API endpoint", runtime="subagent", model="codex")

# ❌ Bad — no reason to use Sonnet here
sessions_spawn(task="grep for 'TODO' comments", runtime="subagent", model="sonnet")
```

### 3. **Batch Periodic Checks**
**Wrong:**
- 3 separate cron jobs (email + calendar + weather)
- 3 separate LLM calls

**Right:**
- 1 heartbeat that checks all 3 in one turn
- 1 LLM call for combined summary

### 4. **Use Local Tools First**
Before calling ANY LLM:
```bash
# ✅ Use grep, jq, SQL first
grep "pattern" file.txt | wc -l
jq '.[] | select(.status=="active")' data.json
sqlite3 db.sql "SELECT * WHERE date > '2026-03-25'" | head -20

# Then pass SUMMARY to LLM (10-20 lines max), not raw file
```

### 5. **Context Chunking**
Never pass raw 64K-row CSVs to LLM. Instead:
```bash
# Get summary stats
sqlite3 trades.db "SELECT COUNT(*), AVG(price), MIN(price), MAX(price) FROM trades WHERE date='2026-03-25'"
# → Pass this tiny summary to Haiku, not the full CSV
```

---

## Daily Cost Monitoring

Run at least once per day:
```bash
./scripts/cost-tracker.sh summary
```

Output shows:
- API calls per model
- Estimated daily cost
- Alerts if any model exceeds budget threshold

**Alert thresholds:**
- OpenAI (Codex): $10/day max
- Anthropic (Sonnet/Haiku): $10/day max
- Free models: unlimited

When approaching limit:
1. Switch to free models (Grok, Gemini)
2. Use local Llama for text work
3. Batch remaining tasks into one efficient call

---

## Decision Tree (Quick)

```
Task is...
├─ Web search / trends / current events?
│  └─ → 🆓 Grok (free, live info)
├─ Summary / categorization?
│  └─ → Gemini (free) or Haiku (cheap)
├─ File reading / regex / transform?
│  └─ → Local Llama or shell tools
├─ Code generation?
│  └─ → Codex
├─ Complex reasoning?
│  ├─ Code-heavy?
│  │  └─ → Codex
│  └─ Non-code?
│     └─ → Sonnet
└─ Subagent analysis?
   └─ → Haiku (default)
```

---

## Examples in Practice

### Example 1: Paper Trader Analysis
_Task: "Analyze bot performance and suggest improvements"_

**Right way:**
1. Query TimescaleDB for stats (not full data dump)
2. Spawn subagent with Haiku to analyze summary
3. If architecture changes needed, upgrade to Codex in new session

**Wrong way:**
- Dump 1000 rows of raw trade data to Sonnet
- Spawn multiple subagents with different models
- No local queries—just raw API calls

---

### Example 2: Still Mode Bug Fix
_Task: "Fix popup window not staying open"_

**Right way:**
1. Read the relevant Swift file locally (no LLM needed)
2. Identify the bug with grep/regex
3. Spawn Codex to generate the fix
4. Test locally

**Wrong way:**
- Spawn Haiku to "understand the codebase"
- Ask Gemini to "summarize the Swift code"
- Waste multiple LLM calls on reading work

---

## When Anthropic Is Down

Anthropic occasionally has outages (like Mar 25). Your fallback chain handles it:

1. Codex available? Use it.
2. Codex down? Fall back to Sonnet.
3. Sonnet down? Fall back to GPT-5.4.
4. All paid models down? Use Grok or Gemini.

No manual intervention needed—the routing handles it.

---

## Practical Examples With Grok

### Example 3: Breaking News Research
_Task: "What's the latest on AI regulation in EU?"_

**Right way:**
```bash
sessions_spawn(task="Find latest EU AI regulation news", model="grok", runtime="subagent")
```
→ Grok fetches real-time web data (free), responds with current info

**Wrong way:**
- Use Sonnet (outdated training data, costs money)
- Use local Llama (no internet, can't access news)

### Example 4: Tech Trends Check
_Task: "What's trending in crypto today?"_

**Right way:**
```bash
sessions_spawn(task="Check trending crypto news and analysis", model="grok", runtime="subagent")
```
→ Grok has real-time market data

**Wrong way:**
- Use Codex (overkill, costs $)
- Use Haiku (outdated, no live data)

---

## Final Rules

✅ **DO:**
- Use **Grok** for web research, trends, current events (free!)
- Default **Haiku** for subagents (analysis, filtering)
- Explicit `model=` when upgrading to Codex/Sonnet
- Batch checks (heartbeat, not cron)
- Use shell/SQL before LLM calls
- Monitor cost daily

❌ **DON'T:**
- Use Sonnet for simple analysis
- Pass raw files to LLMs
- Spawn multiple subagents for one task
- Rely on dashboard history to persist (write to memory!)
- Ignore cost alerts
- Use paid models for web research (Grok is free and better)

---

_Last updated: Mar 25, 2026 — Grok integrated and live._
