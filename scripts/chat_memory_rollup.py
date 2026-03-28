#!/usr/bin/env python3
"""
Chat memory rollup:
1. Rebuild local session index (session_memory.py build-index)
2. Find sessions not yet LLM-summarized
3. Prepare transcript-summary prompts for isolated summarizer runs
4. Regenerate project files from LLM summaries

Usage:
  python3 scripts/chat_memory_rollup.py [--llm-limit N] [--projects-only]

Important:
- Local indexing/tagging is fully automated here.
- Higher-quality LLM transcript summaries should run in isolated subagent/session flows.
- This script can still attempt a CLI-driven isolated call, but the reliable path in live use is:
  prepare prompts here -> spawn isolated summarizers from the current agent session ->
  persist JSON in memory/chat-summaries-llm/ -> rebuild projects.
"""
import argparse
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

WORKSPACE = Path('/Users/jl/.openclaw/workspace')
LOCAL_SUMMARIES = WORKSPACE / 'memory' / 'chat-summaries'
LLM_SUMMARIES = WORKSPACE / 'memory' / 'chat-summaries-llm'
PROJECTS_DIR = WORKSPACE / 'memory' / 'projects'
INDEX_SCRIPT = WORKSPACE / 'scripts' / 'session_memory.py'
LLM_SCRIPT = WORKSPACE / 'scripts' / 'llm_summarize_session.py'


def run(cmd, timeout=120):
    return subprocess.run(cmd, text=True, capture_output=True, check=False, timeout=timeout)


def build_index(days=14, limit=20):
    proc = run(['python3', str(INDEX_SCRIPT), 'build-index', '--days', str(days), '--limit', str(limit)])
    if proc.returncode != 0:
        print(f'[warn] build-index: {proc.stderr[:300]}', file=sys.stderr)
    return proc.stdout.strip()


def get_rollup_candidates(limit):
    proc = run(['python3', str(LLM_SCRIPT), 'check', '--limit', str(limit), str(LOCAL_SUMMARIES)])
    candidates = []
    skipped = []
    if proc.returncode != 0:
        return candidates, skipped
    for line in proc.stdout.strip().splitlines():
        line = line.strip()
        if not line:
            continue
        parts = line.split('\t', 2)
        if parts[0] == 'SUMMARIZE' and len(parts) >= 2:
            candidates.append(parts[1])
        elif parts[0] == 'SKIP' and len(parts) >= 3:
            skipped.append((parts[1], parts[2]))
        else:
            candidates.append(line)
    return candidates, skipped


def get_prompt(session_id):
    try:
        proc = run(['python3', str(LLM_SCRIPT), 'prompt', session_id], timeout=15)
    except subprocess.TimeoutExpired:
        return None, 'prompt timed out'
    if proc.returncode != 0:
        reason = (proc.stderr or proc.stdout).strip() or 'prompt failed'
        return None, reason
    return proc.stdout, None


def summarize_with_llm(session_id, model='anthropic/claude-haiku-4-5'):
    """Call openclaw agent in a new isolated session to avoid lock contention."""
    prompt, prompt_error = get_prompt(session_id)
    if not prompt:
        print(f'[warn] could not get prompt for {session_id}: {prompt_error}', file=sys.stderr)
        return False

    with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
        f.write(prompt)
        prompt_file = f.name

    try:
        cmd = [
            'openclaw', 'agent',
            '--agent', 'main',
            '--session-id', f'mem-rollup-{session_id[:8]}',
            '--message', prompt,
            '--json',
        ]
        try:
            proc = run(cmd, timeout=60)
        except subprocess.TimeoutExpired:
            print(f'[warn] LLM call timed out for {session_id}', file=sys.stderr)
            return False
        if proc.returncode != 0:
            print(f'[warn] LLM call failed for {session_id}: {proc.stderr[:200]}', file=sys.stderr)
            return False
        raw = proc.stdout.strip()
        try:
            outer = json.loads(raw)
            reply_text = outer.get('reply', raw) if isinstance(outer, dict) else raw
        except json.JSONDecodeError:
            reply_text = raw
        start = reply_text.find('{')
        end = reply_text.rfind('}')
        if start == -1 or end < start:
            print(f'[warn] no JSON in LLM response for {session_id}', file=sys.stderr)
            return False
        data = json.loads(reply_text[start:end + 1])
        LLM_SUMMARIES.mkdir(parents=True, exist_ok=True)
        (LLM_SUMMARIES / f'{session_id}.json').write_text(json.dumps(data, indent=2))
        print(f'  [llm] summarized {session_id}')
        return True
    finally:
        os.unlink(prompt_file)


def build_projects():
    PROJECTS_DIR.mkdir(parents=True, exist_ok=True)
    buckets = {}
    for path in sorted(LLM_SUMMARIES.glob('*.json')):
        try:
            data = json.loads(path.read_text())
        except Exception:
            continue
        if data.get('status') == 'skipped':
            continue
        projects = data.get('projects', [])
        if not isinstance(projects, list):
            continue
        for project in projects:
            key = project.strip().lower().replace(' ', '-').replace('/', '-')[:80]
            if not key:
                continue
            b = buckets.setdefault(key, {
                'name': project.strip(), 'sessions': [],
                'tags': set(), 'decisions': [], 'todos': [], 'followups': []
            })
            b['sessions'].append(path.stem)
            b['tags'].update(data.get('tags', []))
            b['decisions'].extend(data.get('decisions', []))
            b['todos'].extend(data.get('todos', []))
            b['followups'].extend(data.get('followups', []))
    written = []
    for key, info in buckets.items():
        def dedup(items):
            seen, out = set(), []
            for item in items:
                item = item.strip()
                if item and item not in seen:
                    seen.add(item)
                    out.append(item)
            return out

        lines = [
            f"# Project Memory - {info['name']}",
            '',
            f"Sessions: {', '.join(info['sessions'][:12])}",
            f"Tags: {', '.join(sorted(info['tags'])[:12])}",
            '',
            '## Decisions',
        ]
        decisions = dedup(info['decisions'])
        lines.extend([f'- {d}' for d in decisions[:12]] or ['- None captured yet'])
        lines += ['', '## Todos']
        todos = dedup(info['todos'])
        lines.extend([f'- {t}' for t in todos[:12]] or ['- None captured yet'])
        lines += ['', '## Follow-ups']
        followups = dedup(info['followups'])
        lines.extend([f'- {f}' for f in followups[:12]] or ['- None captured yet'])
        out = PROJECTS_DIR / f'{key}.md'
        out.write_text('\n'.join(lines) + '\n')
        written.append(out.name)
    return written


def main():
    parser = argparse.ArgumentParser(description='Roll up chat memory: index + LLM summaries + project files.')
    parser.add_argument('--days', type=int, default=14)
    parser.add_argument('--limit', type=int, default=20)
    parser.add_argument('--llm-limit', type=int, default=3)
    parser.add_argument('--model', default='anthropic/claude-haiku-4-5')
    parser.add_argument('--projects-only', action='store_true', help='Skip indexing + LLM, just rebuild project files')
    args = parser.parse_args()

    if not args.projects_only:
        msg = build_index(args.days, args.limit)
        print(msg)

        unsummarized, skipped = get_rollup_candidates(args.llm_limit)
        created = []
        for sid in unsummarized:
            ok = summarize_with_llm(sid, args.model)
            if ok:
                created.append(sid)
        print(f'LLM summaries created: {len(created)}')
        if created:
            print('  ' + ', '.join(created))
        print(f'Sessions skipped: {len(skipped)}')
        for sid, reason in skipped[:10]:
            print(f'  {sid}: {reason}')
    else:
        print('[projects-only mode]')

    projects = build_projects()
    print(f'Project files updated: {len(projects)}')
    if projects:
        print('  ' + ', '.join(projects[:10]))


if __name__ == '__main__':
    main()
