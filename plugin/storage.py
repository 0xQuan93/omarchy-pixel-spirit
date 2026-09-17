"""Durable private JSON state; damaged saves never become a fresh companion."""
import json
import math
import stat
import os
from pathlib import Path
import tempfile

RECOVERED = set()
# Up to 17,000 growth path records fit with generous filename headroom.
MAX_STATE_BYTES = 32 * 1024 * 1024


def number(v):
    return (type(v) is int and 0 <= v <= 2**63 - 1) or (type(v) is float and math.isfinite(v) and v >= 0)


def file_mtime(v):
    # Files archived before the Unix epoch have legitimate negative mtimes.
    return type(v) is int and -(2**63) <= v <= 2**63 - 1


def json_values(v, depth=0):
    if depth > 64:
        raise ValueError('State nesting is too deep')
    if isinstance(v, dict):
        for key, item in v.items():
            if not isinstance(key, str): raise ValueError('Invalid state key')
            json_values(item, depth + 1)
    elif isinstance(v, (list, tuple)):
        for item in v: json_values(item, depth + 1)
    elif isinstance(v, float) and not math.isfinite(v):
        raise ValueError('Nonfinite state number')
    elif v is not None and not isinstance(v, (str, int, float, bool)):
        raise ValueError('Invalid state value')


def records(rows, fields):
    return isinstance(rows, list) and all(isinstance(row, dict) and all(
        isinstance(row.get(key), kind) for key, kind in fields.items()) for row in rows)


def numeric_map(v):
    return isinstance(v, dict) and all(number(item) for item in v.values())


def settings_valid(v):
    return (isinstance(v, dict) and all(type(v.get(k)) is bool for k in ('enabled', 'titles'))
        and number(v.get('quiet_until'))
        and all(k not in v or type(v[k]) is bool for k in ('command_hints','mouse_gestures','activity_responses'))
        and ('revision' not in v or type(v['revision']) is int and v['revision'] >= 0))



class StateError(ValueError):
    pass


def validate(path, data, default):
    json_values(data)
    if not isinstance(data, type(default)):
        raise ValueError('Wrong state type')
    required = {
        'awareness-settings.json': {'enabled': bool, 'titles': bool, 'quiet_until': (int,float)},
        'awareness.json': {'sampled': (int,float), 'since': (int,float), 'snapshot': dict,
                           'seconds': dict, 'events': list, 'reflections': list,
                           'last_attempt': (int,float), 'last_key': str, 'error': str},
        'identity.json': {'name': str, 'seed': int, 'created': (int, float),
                          'class': str, 'interests': list, 'device': str, 'model': str},
        'growth.json': {'born': (int, float), 'updated': (int, float), 'xp': int,
                        'traits': dict, 'day': str, 'daily': int, 'journal': list, 'snapshot': dict},
        'room.json': {'bond': int, 'day': str, 'earned': list, 'activity': str,
                      'notes': list, 'message': str},
    }.get(path.name, {})
    if any(not isinstance(data.get(key), kind) for key, kind in required.items()):
        raise ValueError('Incomplete state')
    if path.name == 'awareness-settings.json' and not settings_valid(data):
        raise ValueError('Invalid awareness settings')
    if path.name == 'awareness.json':
        if (not all(number(data[k]) for k in ('sampled','since','last_attempt'))
            or not number(data.get('last_delivered', 0)) or not numeric_map(data['seconds'])
            or not records(data['events'], {}) or not records(data['reflections'], {'text':str})):
            raise ValueError('Invalid awareness state')
        pending = data.get('pending')
        if pending is not None and (not isinstance(pending, dict) or not number(pending.get('expires'))
            or not settings_valid(pending.get('settings')) or not isinstance(pending.get('context'), dict)
            or not records([pending.get('reflection')], {'id':str,'text':str})):
            raise ValueError('Invalid pending reflection')
    if path.name == 'identity.json':
        if (not number(data['created']) or type(data['seed']) is not int
            or not all(isinstance(item,str) for item in data['interests'])):
            raise ValueError('Invalid identity')
    if path.name == 'growth.json':
        if (not all(number(data[k]) for k in ('xp','daily','born','updated'))
            or not all(type(data['traits'].get(k)) is int and data['traits'][k] >= 0
                       for k in ('Maker','Artist','Musician','Archivist'))
            or not records(data['journal'], {'text':str,'at':(int,float),'xp':int})):
            raise ValueError('Invalid growth')
        snapshot = data['snapshot']
        if (not all(isinstance(snapshot.get(k), dict) for k in ('files','repos','counts'))
            or not isinstance(snapshot.get('limited'), bool) or not numeric_map(snapshot['counts'])
            or not all(isinstance(meta,list) and len(meta)==3 and file_mtime(meta[0]) and number(meta[1])
                       and isinstance(meta[2],str) for meta in snapshot['files'].values())
            or not all(isinstance(refs,dict) and all(isinstance(refs.get(k),str) for k in ('head','upstream'))
                       for refs in snapshot['repos'].values())):
            raise ValueError('Invalid snapshot')
        if (not numeric_map(data.get('presence_seconds',{}))
            or not all(number(data.get(k,0)) for k in ('presence_last','presence_daily'))):
            raise ValueError('Invalid presence history')
    if path.name == 'room.json':
        if (not number(data['bond']) or not all(isinstance(item,str) for item in data['earned'])
            or not records(data['notes'], {'text':str,'at':(int,float)})):
            raise ValueError('Invalid room')
    if path.name == 'history.json' and any(not isinstance(v, dict) or not isinstance(v.get('content'), str) or v.get('role') not in ('user', 'assistant') for v in data):
        raise ValueError('Invalid history')
    return data


def get(path, default):
    path = Path(path)
    damaged = False
    for candidate in (path, path.with_name(path.name + '.bak')):
        try:
            fd = os.open(candidate, os.O_RDONLY | os.O_NONBLOCK | os.O_NOFOLLOW)
            with os.fdopen(fd, 'rb') as stream:
                info = os.fstat(stream.fileno())
                if not stat.S_ISREG(info.st_mode) or info.st_size > MAX_STATE_BYTES:
                    raise ValueError('Invalid state file')
                raw = stream.read(MAX_STATE_BYTES + 1)
            if len(raw) > MAX_STATE_BYTES:
                raise ValueError('State file is too large')
            data = validate(path, json.loads(raw), default)
        except FileNotFoundError:
            continue
        except (OSError, ValueError, TypeError, RecursionError):
            damaged = True
            continue
        if candidate != path:
            RECOVERED.add(path.name)
        return data
    if damaged:
        raise StateError(f'Cannot read {path.name} or its backup. Saved files were preserved; restore a backup before continuing.')
    return default


def atomic_write(path, data):
    fd, tmp = tempfile.mkstemp(dir=path.parent)
    try:
        with os.fdopen(fd, 'w') as stream:
            json.dump(data, stream, allow_nan=False)
            stream.flush()
            if os.fstat(stream.fileno()).st_size > MAX_STATE_BYTES:
                raise ValueError('State file is too large')
            os.fsync(stream.fileno())
        os.replace(tmp, path)
        directory = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY)
        try:
            os.fsync(directory)
        finally:
            os.close(directory)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)


def put(path, data, preserve_previous=True):
    path = Path(path)
    validate(path, data, data)
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    previous = get(path, [] if isinstance(data, list) else {})
    backup = previous if preserve_previous and previous else data
    atomic_write(path.with_name(path.name + '.bak'), backup)
    atomic_write(path, data)
