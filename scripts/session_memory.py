#!/usr/bin/env python3
import argparse
import json
import re
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path

SESSIONS_DIR = Path.home() / '.openclaw' / 'agents' / 'main' / 'sessions'
WORKSPACE = Path('/Users/jl/.openclaw/workspace')
MEMORY_DIR = WORKSPACE / 'memory'
CHAT_INDEX = MEMORY_DIR / 'chat-index.md'
AUTO_SUMMARIES = MEMORY_DIR / 'chat-summaries'

STOPWORDS = {
    'the','a','an','and','or','but','if','then','else','for','to','of','in','on','at','by','with','from','up','down',
    'is','it','this','that','these','those','be','been','being','was','were','are','am','as','we','you','i','they','he','she',
    'do','did','does','done','can','could','should','would','will','just','about','into','over','under','than','too','very',
    'had','has','have','not','no','yes','so','let','lets','like','need','want','make','made','using','use','used','also',
    'work','working','project','chat','history','context','memory','session','sessions','thread','threads'
}

TOPIC_HINTS = {
    'stillmode': ['still mode', 'stillmode', 'notarization', 'popup window', 'multi-select', 'state persistence'],
    'paper-trader': ['paper trader', 'paper-trader', 'season 4', 'season4', 'grafana', 'bot', 'bots', 'trading'],
    'memory-system': ['memory', 'session history', 'chat index', 'context loss', 'history could be lost', 'save chat history'],
    'openclaw-setup': ['openclaw', 'signal', 'gateway', 'heartbeat', 'cron', 'config'],
}


def parse_ts(value):
    if not value:
        return None
    try:
        if value.endswith('Z'):
            value = value[:-1] + '+00:00'
        return datetime.fromisoformat(value)
    except Exception:
        return None


def text_chunks(obj):
    content = (obj.get('message') or {}).get('content') or []
    out = []
    for item in content:
        if item.get('type') == 'text' and item.get('text'):
            out.append(item['text'])
    return out


def iter_session_records(path):
    try:
        with path.open() as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    yield json.loads(line)
                except Exception:
                    continue
    except FileNotFoundError:
        return


def session_messages(path):
    out = []
    for rec in iter_session_records(path):
        if rec.get('type') != 'message':
            continue
        msg = rec.get('message') or {}
        role = msg.get('role')
        if role not in ('user', 'assistant'):
            continue
        texts = text_chunks(rec)
        if not texts:
            continue
        out.append({
            'timestamp': rec.get('timestamp'),
            'role': role,
            'text': re.sub(r'\s+', ' ', '\n'.join(texts)).strip(),
        })
    return out


def summarize_file(path):
    first_ts = None
    last_ts = None
    roles = Counter()
    snippets = []
    for rec in iter_session_records(path):
        ts = parse_ts(rec.get('timestamp'))
        if ts and first_ts is None:
            first_ts = ts
        if ts:
            last_ts = ts
        msg = rec.get('message') or {}
        role = msg.get('role')
        if role:
            roles[role] += 1
        if role in ('user', 'assistant'):
            for t in text_chunks(rec):
                t = re.sub(r'\s+', ' ', t).strip()
                if t:
                    snippets.append((role, t[:220]))
                if len(snippets) >= 4:
                    break
    return {
        'file': str(path),
        'name': path.name,
        'first_ts': first_ts,
        'last_ts': last_ts,
        'roles': roles,
        'snippets': snippets,
    }


def guess_tags(messages):
    joined = ' '.join(m['text'].lower() for m in messages)
    tags = []
    for tag, hints in TOPIC_HINTS.items():
        if any(h in joined for h in hints):
            tags.append(tag)
    words = re.findall(r"[a-zA-Z][a-zA-Z0-9_-]{2,}", joined)
    freq = Counter(w for w in words if w not in STOPWORDS)
    for word, _ in freq.most_common(6):
        if word not in tags:
            tags.append(word)
        if len(tags) >= 8:
            break
    return tags[:8]


def one_line_summary(messages):
    user_msgs = [m['text'] for m in messages if m['role'] == 'user']
    assistant_msgs = [m['text'] for m in messages if m['role'] == 'assistant']
    first_user = user_msgs[0][:180] if user_msgs else ''
    last_assistant = assistant_msgs[-1][:180] if assistant_msgs else ''
    if first_user and last_assistant:
        return f"Started with: {first_user} | Outcome: {last_assistant}"
    return first_user or last_assistant or 'No text summary available.'


def recent(days):
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    items = []
    for path in sorted(SESSIONS_DIR.glob('*.jsonl')):
        info = summarize_file(path)
        ts = info['last_ts'] or info['first_ts']
        if ts and ts >= cutoff:
            items.append(info)
    items.sort(key=lambda x: x['last_ts'] or x['first_ts'] or datetime.min.replace(tzinfo=timezone.utc), reverse=True)
    for item in items:
        ts = item['last_ts'] or item['first_ts']
        print(f"[{ts.isoformat() if ts else 'unknown'}] {item['name']}")
        print(f"  counts: user={item['roles'].get('user',0)} assistant={item['roles'].get('assistant',0)}")
        for role, text in item['snippets'][:2]:
            print(f"  {role}: {text}")
        print()


def find(query):
    terms = [t.lower() for t in query.split() if t.strip()]
    matches = []
    for path in sorted(SESSIONS_DIR.glob('*.jsonl')):
        hit_lines = []
        for rec in iter_session_records(path):
            role = (rec.get('message') or {}).get('role')
            if role not in ('user', 'assistant'):
                continue
            for text in text_chunks(rec):
                flat = re.sub(r'\s+', ' ', text).strip()
                low = flat.lower()
                if all(term in low for term in terms):
                    hit_lines.append((rec.get('timestamp'), role, flat[:300]))
                    if len(hit_lines) >= 5:
                        break
            if len(hit_lines) >= 5:
                break
        if hit_lines:
            matches.append((path, hit_lines))
    if not matches:
        print('No matches.')
        return
    for path, hit_lines in matches:
        print(f'== {path.name} ==')
        for ts, role, text in hit_lines:
            print(f'[{ts}] {role}: {text}')
        print()


def summarize_session(path):
    messages = session_messages(path)
    if not messages:
        return None
    first_ts = parse_ts(messages[0]['timestamp'])
    last_ts = parse_ts(messages[-1]['timestamp'])
    tags = guess_tags(messages)
    return {
        'session_id': path.stem,
        'path': str(path),
        'first_ts': first_ts.isoformat() if first_ts else None,
        'last_ts': last_ts.isoformat() if last_ts else None,
        'message_count': len(messages),
        'user_messages': sum(1 for m in messages if m['role']=='user'),
        'assistant_messages': sum(1 for m in messages if m['role']=='assistant'),
        'tags': tags,
        'summary': one_line_summary(messages),
        'highlights': [m for m in messages[:3]] + ([{'timestamp':'...','role':'...','text':'...'}] if len(messages) > 6 else []) + [m for m in messages[-3:]],
    }


def build_index(days=14, limit=20):
    AUTO_SUMMARIES.mkdir(parents=True, exist_ok=True)
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    summaries = []
    for path in sorted(SESSIONS_DIR.glob('*.jsonl')):
        info = summarize_session(path)
        if not info:
            continue
        ts = parse_ts(info['last_ts']) or parse_ts(info['first_ts'])
        if ts and ts < cutoff:
            continue
        out = AUTO_SUMMARIES / f"{path.stem}.json"
        out.write_text(json.dumps(info, indent=2))
        summaries.append(info)
    summaries.sort(key=lambda x: x['last_ts'] or '', reverse=True)
    lines = [
        '# Chat Index',
        '',
        'Compact index of notable conversations and workstreams.',
        '',
        '## How to use',
        '- Read this first when older chat context may matter.',
        '- Use the tags and search hints to locate the right transcript via `scripts/session_memory.py`.',
        '- Keep entries short; detailed facts belong in daily memory or `MEMORY.md`.',
        '',
        '## Auto-indexed recent sessions',
        ''
    ]
    for item in summaries[:limit]:
        day = (item['last_ts'] or item['first_ts'] or '')[:10]
        tags = ', '.join(f'`{t}`' for t in item['tags'][:6]) if item['tags'] else '`untagged`'
        lines.extend([
            f"- **{day} — {item['session_id']}**",
            f"  - Summary: {item['summary']}",
            f"  - Tags: {tags}",
            f"  - Search hints: {'; '.join(item['tags'][:4]) if item['tags'] else 'use transcript text search'}",
        ])
        if item['tags'] and ('stillmode' in item['tags'] or 'paper-trader' in item['tags'] or 'memory-system' in item['tags']):
            lines.append('')
    CHAT_INDEX.write_text('\n'.join(lines) + '\n')
    print(f'Wrote {CHAT_INDEX} with {min(len(summaries), limit)} entries; stored {len(summaries)} JSON summaries in {AUTO_SUMMARIES}')


def project(query, days=30, limit=8):
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    terms = [t.lower() for t in query.split() if t.strip()]
    hits = []
    for path in sorted((AUTO_SUMMARIES if AUTO_SUMMARIES.exists() else SESSIONS_DIR).glob('*.json' if AUTO_SUMMARIES.exists() else '*.jsonl')):
        if path.suffix == '.json':
            data = json.loads(path.read_text())
        else:
            data = summarize_session(path)
            if not data:
                continue
        ts = parse_ts(data.get('last_ts') or data.get('first_ts'))
        if ts and ts < cutoff:
            continue
        hay = ' '.join([data.get('summary','')] + data.get('tags', [])) .lower()
        score = sum(1 for term in terms if term in hay)
        if score > 0:
            hits.append((score, data))
    hits.sort(key=lambda x: (x[0], x[1].get('last_ts') or ''), reverse=True)
    if not hits:
        print('No project-context hits.')
        return
    for score, item in hits[:limit]:
        print(f"[{score}] {item['session_id']} :: {(item.get('last_ts') or item.get('first_ts') or '')[:10]}")
        print(f"  tags: {', '.join(item.get('tags', []))}")
        print(f"  summary: {item.get('summary', '')}")
        print()


def main():
    parser = argparse.ArgumentParser(description='Search, summarize, and index OpenClaw session archives.')
    sub = parser.add_subparsers(dest='cmd', required=True)

    p_recent = sub.add_parser('recent', help='List recent sessions')
    p_recent.add_argument('--days', type=int, default=7)

    p_find = sub.add_parser('find', help='Find text in session logs')
    p_find.add_argument('query')

    p_build = sub.add_parser('build-index', help='Build auto summaries + chat index')
    p_build.add_argument('--days', type=int, default=14)
    p_build.add_argument('--limit', type=int, default=20)

    p_project = sub.add_parser('project', help='Find likely prior sessions for a project/topic')
    p_project.add_argument('query')
    p_project.add_argument('--days', type=int, default=30)
    p_project.add_argument('--limit', type=int, default=8)

    args = parser.parse_args()
    if args.cmd == 'recent':
        recent(args.days)
    elif args.cmd == 'find':
        find(args.query)
    elif args.cmd == 'build-index':
        build_index(args.days, args.limit)
    elif args.cmd == 'project':
        project(args.query, args.days, args.limit)


if __name__ == '__main__':
    main()
