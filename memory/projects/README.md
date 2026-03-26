# Project Memory

This folder holds compact project-specific rollups derived from chat summaries.

## Purpose

When resuming a project, these files should answer:
- what the project is
- what was decided
- what still needs doing
- which chat sessions are relevant

## Workflow

1. Rebuild recent chat index:
   - `python3 scripts/session_memory.py build-index --days 14 --limit 20`
2. Create or refresh LLM summaries for uncataloged sessions:
   - `python3 scripts/chat_memory_rollup.py --llm-limit 3`
3. Inspect the project helper:
   - `./scripts/project_context.sh "still mode"`
4. Read the corresponding file(s) in this folder.

## Notes

These are derived artifacts, not canonical truth. If a project file looks stale, regenerate the rollup and inspect the underlying daily memory/session summaries.
