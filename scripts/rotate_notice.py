#!/usr/bin/env python3
import argparse
import json
from pathlib import Path

PROJECTS_DIR = Path('/Users/jl/.openclaw/workspace/memory/projects')

NICE_NAMES = {
    'chat-memory-system': 'chat memory system',
    'openclaw-workspace': 'OpenClaw workspace',
    'project-memory': 'project memory',
    'tuque-strategy-optimizer': 'Tuque strategy optimizer',
    'tuque_dashboard': 'Tuque dashboard',
    'stillmode': 'Still Mode',
    'paper-trader': 'Paper Trader',
}

OPENERS = {
    'chat-memory-system': 'Continue the chat-memory automation work',
    'openclaw-workspace': 'Continue OpenClaw workspace/setup improvements',
    'project-memory': 'Continue project-memory automation',
    'tuque-strategy-optimizer': 'Resume Tuque strategy optimizer analysis',
    'tuque_dashboard': 'Resume Tuque dashboard investigation',
    'stillmode': 'Resume Still Mode release prep',
    'paper-trader': 'Continue Paper Trader monitoring or strategy work',
}


def pretty(name):
    return NICE_NAMES.get(name, name.replace('-', ' '))


def opener(name):
    return OPENERS.get(name, f'Resume {pretty(name)}')


def main():
    parser = argparse.ArgumentParser(description='Generate a human-friendly rotation notice.')
    parser.add_argument('--json', dest='as_json', action='store_true')
    parser.add_argument('projects', nargs='*')
    args = parser.parse_args()

    projects = args.projects
    if not projects:
        files = sorted(PROJECTS_DIR.glob('*.md'), key=lambda p: p.stat().st_mtime, reverse=True)
        projects = [p.stem for p in files if p.name != 'README.md'][:5]

    bullets = [pretty(p) for p in projects[:5]]
    openers = [opener(p) for p in projects[:3]]

    text = "Rotation checkpoint saved. Start a fresh chat when you want.\n\nSaved context:\n"
    text += '\n'.join(f'- {b}' for b in bullets)
    if openers:
        text += "\n\nSuggested fresh-chat openers:\n"
        text += '\n'.join(f'- {o}' for o in openers)

    out = {
        'projects': projects[:5],
        'text': text
    }
    if args.as_json:
        print(json.dumps(out, indent=2))
    else:
        print(text)


if __name__ == '__main__':
    main()
