#!/usr/bin/env python3
import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

WORKSPACE = Path('/Users/jl/.openclaw/workspace')
SESSIONS_DIR = Path.home() / '.openclaw' / 'agents' / 'main' / 'sessions'
OUT_DIR = WORKSPACE / 'memory' / 'chat-summaries-llm'
SCRIPT = WORKSPACE / 'scripts' / 'session_memory.py'
DEFAULT_MODEL = os.environ.get('CHAT_MEMORY_LLM_MODEL', 'xai/grok-3-mini')

PROMPT = '''You are summarizing one internal OpenClaw chat transcript for durable memory retrieval.
Return strict JSON with this schema:
{
  "title": string,
  "summary": string,
  "projects": string[],
  "tags": string[],
  "decisions": string[],
  "todos": string[],
  "user_preferences": string[],
  "followups": string[],
  "importance": "low" | "medium" | "high"
}
Rules:
- Be concise and factual.
- Focus on decisions, durable context, project state, preferences, and follow-ups.
- Ignore chatter.
- Do not include secrets.
- If information is absent, use empty arrays.
- Output JSON only.
'''


def run(cmd, input_text=None):
    return subprocess.run(cmd, input=input_text, text=True, capture_output=True, check=False)


def get_transcript(session_id):
    path = SESSIONS_DIR / f'{session_id}.jsonl'
    if not path.exists():
        raise SystemExit(f'Session not found: {path}')
    chunks = []
    for line in path.read_text().splitlines():
        try:
            obj = json.loads(line)
        except Exception:
            continue
        if obj.get('type') != 'message':
            continue
        msg = obj.get('message') or {}
        role = msg.get('role')
        if role not in ('user', 'assistant'):
            continue
        text_parts = [c.get('text') for c in (msg.get('content') or []) if c.get('type') == 'text' and c.get('text')]
        if not text_parts:
            continue
        text = ' '.join(text_parts).strip()
        chunks.append(f'{role.upper()}: {text}')
    text = '\n\n'.join(chunks)
    return text[:30000]


def summarize(session_id, model):
    transcript = get_transcript(session_id)
    payload = f"{PROMPT}\n\nTranscript:\n{transcript}\n"
    cmd = [
        'openclaw', 'agent', '--local', '--json', '--agent', 'main',
        '--message', payload,
    ]
    proc = run(cmd)
    if proc.returncode != 0:
        sys.stderr.write(proc.stderr)
        raise SystemExit(proc.returncode)
    raw = proc.stdout.strip()
    parsed = json.loads(raw)
    text = parsed.get('reply', '') if isinstance(parsed, dict) else ''
    start = text.find('{')
    end = text.rfind('}')
    if start == -1 or end == -1 or end < start:
        raise SystemExit(f'Could not parse JSON from model output:\n{text[:1000]}')
    data = json.loads(text[start:end+1])
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out = OUT_DIR / f'{session_id}.json'
    out.write_text(json.dumps(data, indent=2))
    print(out)


def main():
    parser = argparse.ArgumentParser(description='LLM summarize one session transcript.')
    parser.add_argument('session_id')
    parser.add_argument('--model', default=DEFAULT_MODEL)
    args = parser.parse_args()
    summarize(args.session_id, args.model)


if __name__ == '__main__':
    main()
