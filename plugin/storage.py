"""Durable private JSON state; damaged saves never become a fresh companion."""
import json
import os
from pathlib import Path
import tempfile

RECOVERED = set()


class StateError(ValueError):
    pass


def validate(path, data, default):
    if not isinstance(data, type(default)):
        raise ValueError('Wrong state type')
    required = {
        'identity.json': {'name': str, 'seed': int, 'created': (int, float),
                          'class': str, 'interests': list, 'device': str, 'model': str},
        'growth.json': {'born': (int, float), 'updated': (int, float), 'xp': int,
                        'traits': dict, 'day': str, 'daily': int, 'journal': list, 'snapshot': dict},
        'room.json': {'bond': int, 'day': str, 'earned': list, 'activity': str,
                      'notes': list, 'message': str},
    }.get(path.name, {})
    if any(not isinstance(data.get(key), kind) for key, kind in required.items()):
        raise ValueError('Incomplete state')
    if path.name == 'growth.json':
        if data['xp'] < 0 or not all(isinstance(data['traits'].get(k), int) for k in ('Maker', 'Artist', 'Musician', 'Archivist')):
            raise ValueError('Invalid growth')
        snapshot = data['snapshot']
        if not all(isinstance(snapshot.get(k), dict) for k in ('files', 'repos', 'counts')) or not isinstance(snapshot.get('limited'), bool):
            raise ValueError('Invalid snapshot')
    if path.name == 'history.json' and any(not isinstance(v, dict) or not isinstance(v.get('content'), str) or v.get('role') not in ('user', 'assistant') for v in data):
        raise ValueError('Invalid history')
    return data


def get(path, default):
    path = Path(path)
    damaged = False
    for candidate in (path, path.with_name(path.name + '.bak')):
        try:
            data = validate(path, json.loads(candidate.read_text()), default)
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
            json.dump(data, stream)
            stream.flush()
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
