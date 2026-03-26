# CHAT_MEMORY_SYSTEM.md

A lightweight system for keeping chat context from evaporating.

## Goal

Make past conversations easy to recover and reuse without dumping entire transcripts into every prompt.

## Principles

1. **Chats are not durable memory.** Workspace files are.
2. **Daily notes capture raw context.** `memory/YYYY-MM-DD.md`
3. **Long-term memory captures stable truths.** `MEMORY.md`
4. **Session logs are the source archive.** They are searchable when we need exact historical context.
5. **Indexes beat full transcript loading.** Keep summaries and pointers so future work can find the right conversation fast.

## Files

### 1) Raw daily memory
- Path: `memory/YYYY-MM-DD.md`
- Purpose: short summaries of meaningful work, decisions, blockers, and follow-ups from the day

### 2) Long-term memory
- Path: `MEMORY.md`
- Purpose: stable preferences, project state, durable lessons, identity, recurring rules

### 3) Chat index / cheat sheet
- Path: `memory/chat-index.md`
- Purpose: compact directory of important conversations with tags, date, topic, and where to look next

### 4) Session archive search tool
- Path: `scripts/session_memory.py`
- Purpose: search `~/.openclaw/agents/main/sessions/*.jsonl` and output compact context from old chats

## Operating Process

### During substantial chats
When a conversation contains decisions, project updates, new preferences, or context likely to matter later:

1. Add a short entry to today's `memory/YYYY-MM-DD.md`
2. If it is durable, also update `MEMORY.md`
3. Add or refresh one line in `memory/chat-index.md` if the chat is notable and likely to be revisited

### Before resuming work on something non-trivial
Check context in this order:

1. `MEMORY.md` for durable truths
2. Today's and yesterday's `memory/YYYY-MM-DD.md`
3. `memory/chat-index.md` for likely relevant older conversations
4. Session archive search via `scripts/session_memory.py` when needed

### When historical context is specifically needed
Use the session archive search script instead of guessing.

Examples:

```bash
python3 scripts/session_memory.py find "still mode notarization"
python3 scripts/session_memory.py find "paper trader season 4"
python3 scripts/session_memory.py recent --days 7
```

## What goes in the chat index

Use one bullet per notable thread/workstream:
- date or date range
- topic
- compact summary
- tags
- suggested search terms

Do **not** copy giant transcripts into the index.

## Heuristics for saving chat memory

Save a memory/index entry when a chat includes:
- a decision
- a plan
- a project milestone
- a preference or rule
- a bug/root cause
- a promised follow-up
- a naming/branding choice
- anything JL explicitly says to remember

Skip routine banter or one-off trivia.

## Why this structure works

- `MEMORY.md` stays small and useful
- daily notes preserve chronology
- chat index gives fast routing
- raw session logs remain searchable for exact details

This avoids both failure modes:
- losing context entirely
- stuffing every transcript into permanent memory
