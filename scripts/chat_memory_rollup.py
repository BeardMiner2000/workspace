#!/usr/bin/env python3
import argparse
import json
import subprocess
from pathlib import Path

WORKSPACE = Path('/Users/jl/.openclaw/workspace')
LOCAL_SUMMARIES = WORKSPACE / 'memory' / 'chat-summaries'
LLM_SUMMARIES = WORKSPACE / 'memory' / 'chat-summaries-llm'
PROJECTS_DIR = WORKSPACE / 'memory' / 'projects'
INDEX_SCRIPT = WORKSPACE / 'scripts' / 'session_memory.py'
LLM_SCRIPT = WORKSPACE / 'scripts' / 'llm_summarize_session.py'


def run(cmd):
    return subprocess.run(cmd, text=True, capture_output=True, check=False)


def build_index(days=14, limit=20):
    proc = run(['python3', str(INDEX_SCRIPT), 'build-index', '--days', str(days), '--limit', str(limit)])
    if proc.returncode != 0:
        raise SystemExit(proc.stderr)
    return proc.stdout.strip()


def ensure_llm(limit=3, model=None):
    LLM_SUMMARIES.mkdir(parents=True, exist_ok=True)
    local = sorted(LOCAL_SUMMARIES.glob('*.json'), key=lambda p: p.stat().st_mtime, reverse=True)
    created = []
    for path in local:
        sid = path.stem
        out = LLM_SUMMARIES / f'{sid}.json'
        if out.exists():
            continue
        cmd = ['python3', str(LLM_SCRIPT), sid]
        if model:
            cmd += ['--model', model]
        proc = run(cmd)
        if proc.returncode == 0:
            created.append(sid)
        if len(created) >= limit:
            break
    return created


def build_projects():
    PROJECTS_DIR.mkdir(parents=True, exist_ok=True)
    buckets = {}
    for path in sorted(LLM_SUMMARIES.glob('*.json')):
        data = json.loads(path.read_text())
        for project in data.get('projects', []):
            key = project.strip().lower().replace(' ', '-').replace('/', '-')[:80]
            buckets.setdefault(key, {'name': project.strip(), 'sessions': [], 'tags': set(), 'decisions': [], 'todos': [], 'followups': []})
            buckets[key]['sessions'].append(path.stem)
            buckets[key]['tags'].update(data.get('tags', []))
            buckets[key]['decisions'].extend(data.get('decisions', []))
            buckets[key]['todos'].extend(data.get('todos', []))
            buckets[key]['followups'].extend(data.get('followups', []))
    written = []
    for key, info in buckets.items():
        lines = [
            f"# Project Memory — {info['name']}",
            '',
            f"- Sessions: {', '.join(info['sessions'][:12])}",
            f"- Tags: {', '.join(sorted(info['tags'])[:12])}",
            '',
            '## Decisions',
        ]
        decisions = []
        seen = set()
        for item in info['decisions']:
            item = item.strip()
            if item and item not in seen:
                decisions.append(item)
                seen.add(item)
        if decisions:
            lines.extend([f'- {d}' for d in decisions[:12]])
        else:
            lines.append('- None captured yet')
        lines += ['', '## Todos']
        todos = []
        seen = set()
        for item in info['todos']:
            item = item.strip()
            if item and item not in seen:
                todos.append(item)
                seen.add(item)
        if todos:
            lines.extend([f'- {t}' for t in todos[:12]])
        else:
            lines.append('- None captured yet')
        lines += ['', '## Follow-ups']
        followups = []
        seen = set()
        for item in info['followups']:
            item = item.strip()
            if item and item not in seen:
                followups.append(item)
                seen.add(item)
        if followups:
            lines.extend([f'- {f}' for f in followups[:12]])
        else:
            lines.append('- None captured yet')
        out = PROJECTS_DIR / f'{key}.md'
        out.write_text('\n'.join(lines) + '\n')
        written.append(out.name)
    return written


def main():
    parser = argparse.ArgumentParser(description='Roll up chat memory, LLM summaries, and project memory.')
    parser.add_argument('--days', type=int, default=14)
    parser.add_argument('--limit', type=int, default=20)
    parser.add_argument('--llm-limit', type=int, default=3)
    parser.add_argument('--model', default=None)
    args = parser.parse_args()

    msg = build_index(args.days, args.limit)
    created = ensure_llm(args.llm_limit, args.model)
    projects = build_projects()
    print(msg)
    print(f'LLM summaries created: {len(created)}')
    if created:
        print('  ' + ', '.join(created))
    print(f'Project files updated: {len(projects)}')
    if projects:
        print('  ' + ', '.join(projects[:10]))


if __name__ == '__main__':
    main()
