---
name: auto-session-cycler
description: "On heartbeat, if rotation is due, checkpoint memory and ask the current session to roll into a fresh /new session"
metadata: { "openclaw": { "emoji": "♻️", "events": ["message:received"], "requires": { "config": ["workspace.dir"], "bins": ["python3"] } } }
---

# Auto Session Cycler

Listens for heartbeat/system reminder messages. When chat pace says rotation is due, it:
- runs the existing rotation checkpoint script
- posts a short summary
- instructs the current session to issue `/new`

This preserves the existing memory tooling and uses native OpenClaw session reset behavior.
