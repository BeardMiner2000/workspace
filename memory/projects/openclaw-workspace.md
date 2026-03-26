# Project Memory — OpenClaw workspace

Sessions: bafb85d8-3393-4e67-b28a-7b361e15ed7a
Tags: automation, chat-index, cron, heartbeat, memory, project-context, session-history, summarization

## Decisions
- Treat workspace files as durable memory rather than relying on chat thread history
- Use memory/YYYY-MM-DD.md for raw daily continuity and MEMORY.md for durable long-term context
- Add memory/chat-index.md as a compact cheat sheet for important conversations and workstreams
- Use scripts/session_memory.py to search and index historical session transcripts
- Use memory/projects/ for project-specific rollups
- Run higher-quality transcript summaries through isolated subagent/session flows rather than the active main-session lane

## Todos
- Persist LLM-generated transcript summaries into memory/chat-summaries-llm/
- Rebuild memory/projects/ from structured summary files
- Continue refining automation so heartbeat/rollup runs can refresh memory artifacts regularly

## Follow-ups
- Integrate the isolated summarization path into the regular chat-memory rollup flow
