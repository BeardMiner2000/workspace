#!/usr/bin/env python3
import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path

REGISTRY = Path('/Users/jl/.openclaw/workspace/memory/session-registry.json')


def now_iso():
    return datetime.now(timezone.utc).isoformat()


def slugify(text):
    text = text.strip().lower()
    text = re.sub(r'[^a-z0-9]+', '-', text)
    return text.strip('-') or 'work-chat'


def load():
    return json.loads(REGISTRY.read_text())


def save(data):
    REGISTRY.write_text(json.dumps(data, indent=2) + '\n')


def ensure_entry(data, project):
    slug = slugify(project)
    for item in data['workChats']:
        if item['slug'] == slug:
            return item
    item = {
        'slug': slug,
        'project': project,
        'status': 'active',
        'createdAt': now_iso(),
        'updatedAt': now_iso(),
        'notes': [],
        'resumePrompt': f'Resume {project}',
        'freshChatOpeners': [
            f'Resume {project}',
            f"What's the current state of {project}?",
            f'Continue work on {project}'
        ]
    }
    data['workChats'].append(item)
    return item


def start(args):
    data = load()
    item = ensure_entry(data, args.project)
    item['status'] = 'active'
    item['updatedAt'] = now_iso()
    if args.note:
        item['notes'].append(args.note)
    data['currentWork'] = item['slug']
    save(data)
    print(json.dumps({
        'action': 'start',
        'currentWork': data['currentWork'],
        'project': item['project'],
        'message': f"Current work chat is now '{item['project']}'. Use this as the primary active thread.",
        'resumePrompt': item['resumePrompt'],
        'freshChatOpeners': item['freshChatOpeners'][:3]
    }, indent=2))


def resume(args):
    data = load()
    item = ensure_entry(data, args.project)
    item['status'] = 'active'
    item['updatedAt'] = now_iso()
    data['currentWork'] = item['slug']
    save(data)
    print(json.dumps({
        'action': 'resume',
        'currentWork': data['currentWork'],
        'project': item['project'],
        'message': f"Resume '{item['project']}' in the active chat. Ignore heartbeat/subagent clutter unless explicitly needed.",
        'resumePrompt': item['resumePrompt'],
        'freshChatOpeners': item['freshChatOpeners'][:3]
    }, indent=2))


def rotate(args):
    data = load()
    slug = data.get('currentWork')
    item = None
    if slug:
        for w in data['workChats']:
            if w['slug'] == slug:
                item = w
                break
    if item:
        item['status'] = 'rotated'
        item['updatedAt'] = now_iso()
    data['currentWork'] = None
    save(data)
    print(json.dumps({
        'action': 'rotate',
        'rotatedProject': item['project'] if item else None,
        'message': 'Current work chat rotated. Start or resume a project to choose the next active work chat.'
    }, indent=2))


def ls():
    data = load()
    print(json.dumps(data, indent=2))


def main():
    parser = argparse.ArgumentParser(description='Friendly work-chat registry on top of OpenClaw sessions.')
    sub = parser.add_subparsers(dest='cmd', required=True)

    p_start = sub.add_parser('start')
    p_start.add_argument('project')
    p_start.add_argument('--note')

    p_resume = sub.add_parser('resume')
    p_resume.add_argument('project')

    sub.add_parser('rotate')
    sub.add_parser('list')

    args = parser.parse_args()
    if args.cmd == 'start':
        start(args)
    elif args.cmd == 'resume':
        resume(args)
    elif args.cmd == 'rotate':
        rotate(args)
    elif args.cmd == 'list':
        ls()


if __name__ == '__main__':
    main()
