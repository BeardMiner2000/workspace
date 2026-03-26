#!/usr/bin/env python3
import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

STATE_PATH = Path('/Users/jl/.openclaw/workspace/memory/chat-pace-state.json')


def now_utc():
    return datetime.now(timezone.utc)


def now_iso():
    return now_utc().isoformat()


def parse_iso(value):
    if not value:
        return None
    try:
        if value.endswith('Z'):
            value = value[:-1] + '+00:00'
        return datetime.fromisoformat(value)
    except Exception:
        return None


def minutes_since(value):
    dt = parse_iso(value)
    if not dt:
        return None
    return int((now_utc() - dt).total_seconds() // 60)


def load_state():
    return json.loads(STATE_PATH.read_text())


def save_state(state):
    STATE_PATH.write_text(json.dumps(state, indent=2) + '\n')


def classify(cur):
    score = 0
    score += min(cur.get('toolSignals', 0), 6)
    score += min(cur.get('longMessages', 0), 4)
    score += min(cur.get('decisionSignals', 0), 4)
    score += min(cur.get('recoverySignals', 0), 3)
    score += min(cur.get('projectSwitches', 0) * 2, 4)
    if score >= 10:
        return 'heavy'
    if score >= 4:
        return 'medium'
    return 'low'


def current_out(state):
    cur = state['current']
    pace = classify(cur)
    policy = state['policy'][pace]
    started = minutes_since(cur.get('threadStartedAt'))
    since_codified = minutes_since(cur.get('lastCodifiedAt'))
    return {
        'pace': pace,
        'codifyEveryMinutes': policy['codifyEveryMinutes'],
        'rotateAfterMinutes': policy['rotateAfterMinutes'],
        'minutesSinceThreadStart': started,
        'minutesSinceCodified': since_codified,
        'current': cur,
    }


def assess(state):
    out = current_out(state)
    cur = out['current']
    pace = out['pace']
    codify_every = out['codifyEveryMinutes']
    rotate_after = out['rotateAfterMinutes']
    started = out['minutesSinceThreadStart']
    since_codified = out['minutesSinceCodified']
    reasons = []
    action = 'stay'

    if cur.get('projectSwitches', 0) > 0:
        reasons.append('project switch detected')
        action = 'rotate'
    elif started is not None and started >= rotate_after:
        reasons.append(f'thread age {started}m >= rotate threshold {rotate_after}m')
        action = 'rotate'
    elif since_codified is None and started is not None and started >= codify_every:
        reasons.append(f'no codify yet and thread age {started}m >= codify threshold {codify_every}m')
        action = 'codify'
    elif since_codified is not None and since_codified >= codify_every:
        reasons.append(f'last codify {since_codified}m ago >= codify threshold {codify_every}m')
        action = 'codify'

    if pace == 'heavy' and cur.get('decisionSignals', 0) > 0:
        if action == 'stay':
            action = 'codify'
        reasons.append('heavy pace with active decisions')

    if cur.get('recoverySignals', 0) >= 2 and action == 'stay':
        action = 'codify'
        reasons.append('multiple recovery/continue signals')

    if not reasons:
        reasons.append('within current pace thresholds')

    return {
        'action': action,
        'pace': pace,
        'codifyEveryMinutes': codify_every,
        'rotateAfterMinutes': rotate_after,
        'minutesSinceThreadStart': started,
        'minutesSinceCodified': since_codified,
        'reasons': reasons,
    }


def status():
    state = load_state()
    print(json.dumps(current_out(state), indent=2))


def cmd_assess():
    state = load_state()
    print(json.dumps(assess(state), indent=2))


def bump(args):
    state = load_state()
    cur = state['current']
    if cur['threadStartedAt'] is None:
        cur['threadStartedAt'] = now_iso()
    if args.tool:
        cur['toolSignals'] += args.tool
    if args.long:
        cur['longMessages'] += args.long
    if args.decision:
        cur['decisionSignals'] += args.decision
    if args.recovery:
        cur['recoverySignals'] += args.recovery
    if args.project and args.project != cur.get('lastProject'):
        if cur.get('lastProject') is not None:
            cur['projectSwitches'] += 1
        cur['lastProject'] = args.project
    cur['pace'] = classify(cur)
    save_state(state)
    print(json.dumps(cur, indent=2))


def codified():
    state = load_state()
    state['current']['lastCodifiedAt'] = now_iso()
    save_state(state)
    print('ok')


def reset(args):
    state = load_state()
    state['current'] = {
        'pace': args.pace,
        'threadStartedAt': now_iso(),
        'lastCodifiedAt': now_iso() if args.codified else None,
        'lastProject': args.project,
        'projectSwitches': 0,
        'toolSignals': 0,
        'longMessages': 0,
        'decisionSignals': 0,
        'recoverySignals': 0,
        'notes': 'Heuristic state for chat rotation and codification cadence.'
    }
    save_state(state)
    print(json.dumps(state['current'], indent=2))


def main():
    parser = argparse.ArgumentParser(description='Track chat pace and recommend codify/rotate cadence.')
    sub = parser.add_subparsers(dest='cmd', required=True)

    sub.add_parser('status')
    sub.add_parser('assess')

    p_bump = sub.add_parser('bump')
    p_bump.add_argument('--tool', type=int, default=0)
    p_bump.add_argument('--long', type=int, default=0)
    p_bump.add_argument('--decision', type=int, default=0)
    p_bump.add_argument('--recovery', type=int, default=0)
    p_bump.add_argument('--project')

    sub.add_parser('codified')

    p_reset = sub.add_parser('reset')
    p_reset.add_argument('--pace', default='low')
    p_reset.add_argument('--project')
    p_reset.add_argument('--codified', action='store_true')

    args = parser.parse_args()
    if args.cmd == 'status':
        status()
    elif args.cmd == 'assess':
        cmd_assess()
    elif args.cmd == 'bump':
        bump(args)
    elif args.cmd == 'codified':
        codified()
    elif args.cmd == 'reset':
        reset(args)


if __name__ == '__main__':
    main()
