#!/usr/bin/env python3
import argparse
import json
import re
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path

SESSIONS_DIR = Path.home() / '.openclaw' / 'agents' / 'main' / 'sessions'


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
        if len(snippets) >= 4 and last_ts:
            pass
    return {
        'file': str(path),
        'name': path.name,
        'first_ts': first_ts,
        'last_ts': last_ts,
        'roles': roles,
        'snippets': snippets,
    }


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


def main():
    parser = argparse.ArgumentParser(description='Search and summarize OpenClaw session archives.')
    sub = parser.add_subparsers(dest='cmd', required=True)

    p_recent = sub.add_parser('recent', help='List recent sessions')
    p_recent.add_argument('--days', type=int, default=7)

    p_find = sub.add_parser('find', help='Find text in session logs')
    p_find.add_argument('query')

    args = parser.parse_args()
    if args.cmd == 'recent':
        recent(args.days)
    elif args.cmd == 'find':
        find(args.query)


if __name__ == '__main__':
    main()
