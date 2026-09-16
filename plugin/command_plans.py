"""Reviewed, expiring local plans. Only fixed action IDs cross the process boundary."""
import fcntl
import json
import re
import secrets
import time
from pathlib import Path
from storage import get, put

# Focus-dependent window commands, toggles, destructive operations and arbitrary
# discovered targets deliberately require individual requests.
ALLOWED = frozenset({
    'browser', 'terminal', 'files', 'notes', 'settings', 'appearance',
    'theme_picker', 'background_picker', 'settings_audio', 'settings_bluetooth',
    'settings_network', 'settings_display', 'keybindings', 'about',
    'volume_up', 'volume_down', 'mute', 'unmute', 'brightness_up', 'brightness_down',
    'dnd_on', 'dnd_off', 'power_saver', 'power_balanced',
    'radio_random', 'radio_stop', 'cartoons_on', 'cartoons_off', 'cartoons_close',
    'cartoons_hide', 'cartoons_pause', 'cartoons_resume', 'cartoons_mute',
    'cartoons_unmute', 'cartoons_on_muted', 'q_cut', 'resonant', 'wanderer',
})
TTL = 300

def rewrite(actions):
    actions = list(actions)
    # Mute before loading any cartoon audio, even when another source opens first.
    if 'cartoons_on' in actions and 'cartoons_mute' in actions:
        actions[actions.index('cartoons_on')] = 'cartoons_on_muted'
        actions.remove('cartoons_mute')
    return actions

def proposal(message, base, actions, labels, normalize, match, resolve, available):
    from compound_commands import propose
    def clause(text):
        action = match(text)
        return action or resolve(text)
    reply = propose(message, clause, labels, ALLOWED & actions.keys(), normalize, rewrite)
    if not reply or not reply.get('steps'):
        return reply
    steps = reply['steps']
    if not all(available(step['action']) for step in steps):
        return dict(text='One of those controls is unavailable here. Nothing has run. Try each request separately.',
                    action='', steps=[], emote='idle', route='local')
    token = secrets.token_hex(16)
    base = Path(base)
    base.mkdir(parents=True, exist_ok=True)
    with (base / 'command-plan.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        put(base / 'command-plan.json', dict(token=token, created=time.time(),
            actions=[s['action'] for s in steps]), preserve_previous=False)
    reply.update(action='plan:' + token, actionLabel='Run ' + str(len(steps)) + ' steps',
                 text='Ready: review these steps, then tap Run plan. This plan expires in five minutes.')
    return reply

def execute(token, base, actions, labels, available, run_step):
    if not isinstance(token, str) or not re.fullmatch(r'plan:[0-9a-f]{32}', token):
        raise ValueError('Invalid command plan.')
    base = Path(base)
    base.mkdir(parents=True, exist_ok=True)
    with (base / 'command-plan.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        plan = get(base / 'command-plan.json', {})
        if not isinstance(plan, dict) or plan.get('token') != token[5:]:
            raise ValueError('This plan has expired or was already used. Ask again to prepare it.')
        # Claim before validation/effects: failed or interrupted plans never replay.
        put(base / 'command-plan.json', {}, preserve_previous=False)
        ids = plan.get('actions')
        created = plan.get('created')
        if (type(created) not in (int, float) or not 0 <= time.time()-created <= TTL
                or not isinstance(ids, list) or not 1 <= len(ids) <= 4
                or any(not isinstance(a, str) or a not in ALLOWED or a not in actions for a in ids)):
            raise ValueError('This plan is invalid or expired. Ask again to prepare it.')
        if not all(available(a) for a in ids):
            raise ValueError('A required control is unavailable. Nothing ran; prepare a new plan.')
    completed = []
    for action in ids:
        try:
            receipt = run_step(action)
            if not isinstance(receipt, dict) or receipt.get('error') or receipt.get('ok') is False:
                raise ValueError('The control did not confirm success.')
        except Exception:
            remaining = ids[len(completed)+1:]
            text = ('Completed: ' + '; '.join(completed) + '. ' if completed else 'No steps completed. ')
            text += 'Stopped at: ' + labels[action] + '.'
            if remaining: text += ' Not run: ' + '; '.join(labels[a] for a in remaining) + '.'
            return dict(text=text, action='', emote='idle', route='local', completed=completed, ok=False)
        completed.append(labels[action])
    return dict(text='Completed: ' + '; '.join(completed) + '.', action='',
                emote='working', route='local', completed=completed, ok=True)
