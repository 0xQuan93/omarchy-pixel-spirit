"""Saved, reviewed command recipes made only from registered action IDs.

Saving reads an existing one-use plan; preparing a routine creates a fresh one-use
plan. This module never executes a command or accepts argv from saved state.
"""
import fcntl
import math
import re
import secrets
import time
import unicodedata
from pathlib import Path

from storage import get, put

VERSION = 1
MAX_ROUTINES = 24
ID = re.compile(r'[0-9a-f]{16}')
FINGERPRINT = re.compile(r'[0-9a-f]{64}')


def _name(value):
    if not isinstance(value, str):
        raise ValueError('Give this routine a short name.')
    value = unicodedata.normalize('NFC', value).strip()
    if not 1 <= len(value) <= 64 or not all(char.isprintable() for char in value):
        raise ValueError('Routine names must be one to 64 printable characters.')
    return value


def _path(base):
    return Path(base) / 'reviewed-routines.json'


def _read(base):
    path = _path(base)
    data = get(path, {})
    if data == {} and not path.exists() and not path.with_name(path.name + '.bak').exists():
        return []
    if (not isinstance(data, dict) or type(data.get('version')) is not int
            or data['version'] != VERSION or set(data) != {'version', 'items'}):
        raise ValueError('Saved routines use an unsupported or damaged format. They were preserved.')
    items = data['items']
    if not isinstance(items, list) or len(items) > MAX_ROUTINES:
        raise ValueError('Saved routines are invalid. They were preserved.')
    seen_ids, seen_names = set(), set()
    for item in items:
        if not isinstance(item, dict) or set(item) != {'id', 'name', 'actions', 'fingerprints', 'createdAt'}:
            raise ValueError('Saved routines are invalid. They were preserved.')
        ident, actions, fingerprints = item['id'], item['actions'], item['fingerprints']
        try:
            name = _name(item['name'])
        except ValueError:
            raise ValueError('Saved routines are invalid. They were preserved.') from None
        if (not isinstance(ident, str) or not ID.fullmatch(ident) or ident in seen_ids
                or name.casefold() in seen_names or not isinstance(actions, list)
                or not 1 <= len(actions) <= 4
                or any(not isinstance(action, str) or not 1 <= len(action) <= 160 for action in actions)
                or len(set(actions)) != len(actions)
                or not isinstance(fingerprints, dict) or set(fingerprints) != set(actions)
                or any(not isinstance(value, str) or not FINGERPRINT.fullmatch(value)
                       for value in fingerprints.values())
                or type(item['createdAt']) not in (int, float)
                or not math.isfinite(item['createdAt']) or item['createdAt'] < 0):
            raise ValueError('Saved routines are invalid. They were preserved.')
        seen_ids.add(ident)
        seen_names.add(name.casefold())
    return items


def _write(base, items):
    put(_path(base), {'version': VERSION, 'items': items}, preserve_previous=False)


def _locked(base):
    base = Path(base)
    base.mkdir(parents=True, exist_ok=True, mode=0o700)
    lock = (base / 'reviewed-routines.lock').open('a')
    fcntl.flock(lock, fcntl.LOCK_EX)
    return lock


def list_saved(base, registry=None):
    """Show saved names and current readiness without exposing stored argv."""
    items = _read(base)
    result = []
    for item in items:
        ready, reason = None, 'Current controls were not checked.'
        if registry is not None:
            ready, reason = True, ''
            if registry.rewrite_plan(item['actions']) != tuple(item['actions']):
                ready, reason = False, 'The saved steps need a fresh review.'
            for action in item['actions']:
                if not ready:
                    break
                try:
                    fingerprint = registry.fingerprint(action)
                    if action not in registry.plan_allowed() or fingerprint != item['fingerprints'][action]:
                        ready, reason = False, 'A control changed. Review and save this routine again.'
                        break
                    info = registry.describe(action)
                    if not info['available']:
                        ready, reason = False, info['availabilityReason'] or 'A control is unavailable.'
                        break
                except ValueError:
                    ready, reason = False, 'A control is no longer registered.'
                    break
        result.append({'id': item['id'], 'name': item['name'], 'steps': len(item['actions']),
                       'ready': ready, 'reason': reason})
    return {'routines': result}


def save_pending(base, token, name, registry):
    """Capture only the IDs and fingerprints of the plan currently on screen."""
    from command_plans import pending
    name = _name(name)
    base = Path(base)
    base.mkdir(parents=True, exist_ok=True, mode=0o700)
    # Hold the same lock used by plan replacement and execution through the
    # saved-routine write. A plan cannot disappear after validation but before
    # its IDs are captured.
    with (base / 'command-plan.lock').open('a') as plan_lock:
        fcntl.flock(plan_lock, fcntl.LOCK_EX)
        actions = pending(base, token, registry)
        with _locked(base):
            items = _read(base)
            if len(items) >= MAX_ROUTINES:
                raise ValueError('The routine shelf is full. Remove one before saving another.')
            if any(item['name'].casefold() == name.casefold() for item in items):
                raise ValueError('A routine already has that name.')
            ident = secrets.token_hex(8)
            while any(item['id'] == ident for item in items):
                ident = secrets.token_hex(8)
            items.append({'id': ident, 'name': name, 'actions': list(actions),
                          'fingerprints': {action: registry.fingerprint(action) for action in actions},
                          'createdAt': time.time()})
            _write(base, items)
    return {'savedId': ident, 'text': 'Saved “' + name + '”. Run still requires your review.',
            **list_saved(base, registry)}


def prepare(base, ident, actions, labels, registry):
    """Revalidate a saved recipe and return a fresh one-use plan preview."""
    if not isinstance(ident, str) or not ID.fullmatch(ident):
        raise ValueError('Unknown routine.')
    item = next((entry for entry in _read(base) if entry['id'] == ident), None)
    if item is None:
        raise ValueError('That routine was removed.')
    for action in item['actions']:
        try:
            fingerprint = registry.fingerprint(action)
            if action not in registry.plan_allowed() or fingerprint != item['fingerprints'][action]:
                raise ValueError('A routine control changed. Review and save it again.')
            if not registry.describe(action)['available']:
                raise ValueError('A routine control is unavailable. Nothing has run.')
        except ValueError as error:
            if str(error) == 'Unknown fixed capability.':
                raise ValueError('A routine control is no longer registered.') from None
            raise
    from command_plans import prepare_steps
    preview = prepare_steps(item['actions'], base, actions, labels, registry)
    preview['routineName'] = item['name']
    return preview


def remove(base, ident, registry=None):
    if not isinstance(ident, str) or not ID.fullmatch(ident):
        raise ValueError('Unknown routine.')
    with _locked(base):
        items = _read(base)
        kept = [item for item in items if item['id'] != ident]
        if len(kept) == len(items):
            raise ValueError('That routine was already removed.')
        _write(base, kept)
    return {'text': 'Removed the routine.', **list_saved(base, registry)}
