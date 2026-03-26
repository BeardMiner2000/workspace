#!/usr/bin/env python3
import argparse
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path

WORKSPACE = Path('/Users/jl/.openclaw/workspace')
MEMORY_DIR = WORKSPACE / 'memory'
TODAY = datetime.now().strftime('%Y-%m-%d')
DAY_FILE = MEMORY_DIR / f'{TODAY}.md'
PROJECTS_DIR = MEMORY_DIR / 'projects'


def run(cmd, timeout=120):
    return subprocess.run(cmd, text=True, capture_output=True, check=False, timeout=timeout)


def ensure_rollup():
    cmds = [
        ['python3', 'scripts/session_memory.py', 'build-index', '--days', '14', '--limit', '20'],
        ['python3', 'scripts/chat_memory_rollup.py', '--projects-only'],
        ['python3', 'scripts/chat_pace.py', 'codified'],
    ]
    outputs = []
    for cmd in cmds:
        proc = run(cmd)
        outputs.append((cmd, proc.returncode, proc.stdout.strip(), proc.stderr.strip()))
    return outputs


def append_day_log(note):
    ts = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')
    block = f"\n## Rotation checkpoint ({ts})\n- {note}\n"
    if DAY_FILE.exists():
        with DAY_FILE.open('a') as f:
            f.write(block)
    else:
        DAY_FILE.write_text(f"# Session Log — {TODAY}\n{block}")


def top_projects(limit=5):
    if not PROJECTS_DIR.exists():
        return []
    files = sorted(PROJECTS_DIR.glob('*.md'), key=lambda p: p.stat().st_mtime, reverse=True)
    return [p.stem for p in files if p.name != 'README.md'][:limit]


def reset_pace(project=None):
    cmd = ['python3', 'scripts/chat_pace.py', 'reset', '--pace', 'low', '--codified']
    if project:
        cmd += ['--project', project]
    run(cmd)


def main():
    parser = argparse.ArgumentParser(description='Perform a chat rotation checkpoint and output a user-facing summary.')
    parser.add_argument('--reason', default='Rotation recommended by chat pace policy.')
    parser.add_argument('--project', default=None)
    args = parser.parse_args()

    outputs = ensure_rollup()
    append_day_log(args.reason)
    projects = top_projects()
    reset_pace(args.project)

    summary = {
        'rotated': True,
        'reason': args.reason,
        'projectsSaved': projects,
        'timestamp': datetime.now(timezone.utc).isoformat(),
        'commands': [
            {'cmd': ' '.join(cmd), 'code': code}
            for cmd, code, _out, _err in outputs
        ]
    }
    print(json.dumps(summary, indent=2))


if __name__ == '__main__':
    main()
