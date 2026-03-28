---
name: auto-rotate-new
description: "When a fresh /new session starts, post a short human summary of what was saved and which projects can be resumed"
metadata: { "openclaw": { "emoji": "🧭", "events": ["command:new"], "requires": { "config": ["workspace.dir"] } } }
---

# Auto Rotate New

When `/new` is issued, generate a short, plain-language summary of:
- what was saved
- which projects the user can return to
- suggested fresh-chat openers

This complements the bundled `session-memory` hook by making the fresh-session landing clearer for humans.
