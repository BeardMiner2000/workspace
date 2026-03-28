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
DEFAULT_MODEL = os.environ.get('CHAT_MEMORY_LLM_MODEL', 'xai/grok-3-mini')
SUMMARY_PROMPT_MARKERS = (
    'You are summarizing one internal OpenClaw chat transcript for durable memory retrieval.',
    'Return strict JSON with this schema:',
    'Transcript:',
    'Transcript to summarize:',
)
SUMMARY_JSON_KEYS = (
    '"title"',
    '"summary"',
    '"projects"',
    '"tags"',
    '"decisions"',
    '"todos"',
    '"user_preferences"',
    '"followups"',
    '"importance"',
)

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


def session_messages(session_id):
    path = SESSIONS_DIR / f'{session_id}.jsonl'
    if not path.exists():
        raise SystemExit(f'Session not found: {path}')
    messages = []
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
        messages.append({'role': role, 'text': '\n'.join(text_parts).strip()})
    return messages


def get_transcript(session_id):
    chunks = []
    for message in session_messages(session_id):
        text = ' '.join(message['text'].split()).strip()
        chunks.append(f"{message['role'].upper()}: {text}")
    return '\n\n'.join(chunks)[:30000]


def _looks_like_summary_json(text):
    normalized = text.strip()
    if normalized.startswith('```json'):
        normalized = normalized[7:]
    if normalized.endswith('```'):
        normalized = normalized[:-3]
    return normalized.count('{') > 0 and normalized.count('}') > 0 and all(key in normalized for key in SUMMARY_JSON_KEYS)


def inspect_session(session_id):
    messages = session_messages(session_id)
    if not messages:
        return {'action': 'skip', 'reason': 'no user/assistant messages'}

    first_user = next((m['text'] for m in messages if m['role'] == 'user'), '')
    assistant_texts = [m['text'] for m in messages if m['role'] == 'assistant']
    all_text = '\n\n'.join(m['text'] for m in messages)

    prompt_hits = sum(marker in all_text for marker in SUMMARY_PROMPT_MARKERS)
    has_summary_prompt = prompt_hits >= 2 or '[Subagent Task]: You are summarizing one internal OpenClaw chat transcript' in first_user
    has_summary_result = any(_looks_like_summary_json(text) for text in assistant_texts)

    if has_summary_prompt and has_summary_result:
        return {'action': 'skip', 'reason': 'recursive summary transcript'}
    if has_summary_prompt:
        return {'action': 'skip', 'reason': 'summary prompt transcript'}
    if has_summary_result and len(messages) <= 3:
        return {'action': 'skip', 'reason': 'summary result transcript'}
    return {'action': 'summarize', 'reason': 'eligible'}


def already_summarized(session_id):
    return (OUT_DIR / f'{session_id}.json').exists()


def write_result(session_id, data):
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out = OUT_DIR / f'{session_id}.json'
    out.write_text(json.dumps(data, indent=2))
    return out


def write_skip_result(session_id, reason):
    return write_result(session_id, {
        'session_id': session_id,
        'status': 'skipped',
        'skip_reason': reason,
    })


def summarize(session_id, model):
    inspection = inspect_session(session_id)
    if inspection['action'] == 'skip':
        out = write_skip_result(session_id, inspection['reason'])
        print(out)
        return

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
    out = write_result(session_id, data)
    print(out)


def print_prompt(session_id):
    inspection = inspect_session(session_id)
    if inspection['action'] == 'skip':
        raise SystemExit(f"Skip {session_id}: {inspection['reason']}")
    transcript = get_transcript(session_id)
    print(f"{PROMPT}\n\nTranscript:\n{transcript}\n")


def check_candidates(limit, local_summaries_dir):
    local_dir = Path(local_summaries_dir)
    found = 0
    for path in sorted(local_dir.glob('*.json'), key=lambda f: f.stat().st_mtime, reverse=True):
        session_id = path.stem
        if already_summarized(session_id):
            continue
        inspection = inspect_session(session_id)
        if inspection['action'] == 'skip':
            write_skip_result(session_id, inspection['reason'])
            print(f"SKIP\t{session_id}\t{inspection['reason']}")
            continue
        print(f"SUMMARIZE\t{session_id}")
        found += 1
        if found >= limit:
            break


def main():
    parser = argparse.ArgumentParser(description='Prepare or apply LLM session summaries.')
    sub = parser.add_subparsers(dest='cmd')

    p_summarize = sub.add_parser('summarize', help='Summarize a session transcript.')
    p_summarize.add_argument('session_id')
    p_summarize.add_argument('--model', default=DEFAULT_MODEL)

    p_prompt = sub.add_parser('prompt', help='Print the summarization payload for a session')
    p_prompt.add_argument('session_id')

    p_check = sub.add_parser('check', help='Print rollup candidates and skipped sessions')
    p_check.add_argument('--limit', type=int, default=5)
    p_check.add_argument('local_summaries_dir', nargs='?', default=str(WORKSPACE / 'memory' / 'chat-summaries'))

    args = parser.parse_args()
    cmd = args.cmd or 'summarize'
    if cmd == 'summarize':
        summarize(args.session_id, args.model)
    elif cmd == 'prompt':
        print_prompt(args.session_id)
    elif cmd == 'check':
        check_candidates(args.limit, args.local_summaries_dir)


if __name__ == '__main__':
    main()
