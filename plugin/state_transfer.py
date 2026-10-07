#!/usr/bin/env python3
"""Preview, export, and import a bounded, local Wisp state transfer.

The format is one JSON document with fixed logical sections. It never extracts
archive member paths, imports executable code, or copies machine observation
history into the new machine's active snapshot.
"""

import argparse
import copy
import datetime
import fcntl
import json
import os
from pathlib import Path
import re
import stat
import tempfile
import time

from storage import MAX_STATE_BYTES, get, validate


FORMAT = 'wisp-state-transfer'
VERSION = 1
SECTIONS = ('identity', 'growth', 'room', 'settings', 'chat')
DEFAULT_SECTIONS = SECTIONS[:1]
FILES = {
    'identity': ('identity.json',),
    'growth': ('growth.json',),
    'room': ('room.json',),
    'settings': ('awareness-settings.json', 'position.json'),
    'chat': ('history.json', 'learned-phrases.json'),
}
MAX_TRANSFER_BYTES = 96 * 1024 * 1024
MAX_SMALL_BYTES = 4 * 1024 * 1024
BACKUP_PREFIX = 'transfer-backup-'


def default_state_dir():
    return Path(os.environ.get('XDG_STATE_HOME', str(Path.home() / '.local/state'))) / 'pixel-spirit'


def _strict_json(raw):
    def unique(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError('Duplicate JSON key')
            result[key] = value
        return result

    def invalid(value):
        raise ValueError('Invalid JSON number: ' + value)

    return json.loads(raw, object_pairs_hook=unique, parse_constant=invalid)


def _encoded(value):
    raw = (json.dumps(value, ensure_ascii=False, allow_nan=False, separators=(',', ':')) + '\n').encode('utf-8')
    if len(raw) > MAX_TRANSFER_BYTES:
        raise ValueError('Transfer is too large')
    return raw


def _read_regular(path, limit):
    fd = os.open(path, os.O_RDONLY | os.O_NONBLOCK | os.O_NOFOLLOW)
    with os.fdopen(fd, 'rb') as stream:
        info = os.fstat(stream.fileno())
        if not stat.S_ISREG(info.st_mode) or info.st_size > limit:
            raise ValueError('Invalid or oversized file: ' + path.name)
        raw = stream.read(limit + 1)
    if len(raw) > limit:
        raise ValueError('Oversized file: ' + path.name)
    return raw


def _existing(base, name, default):
    path = base / name
    if not os.path.lexists(path) and not os.path.lexists(base / (name + '.bak')):
        return None
    return get(path, default)


def _validate_learned(data):
    from learned_phrases import MAX_ENTRIES, MAX_BYTES, _valid

    if (type(data) is not dict or data.get('version') != 1
            or type(data.get('entries')) is not list
            or len(data['entries']) > MAX_ENTRIES
            or any(not _valid(item) for item in data['entries'])
            or len(_encoded(data)) > MAX_BYTES):
        raise ValueError('Invalid learned phrase bank')


def _validate_position(data):
    if type(data) is not dict or set(data) - {'x', 'y', 'hidden', 'voice', 'movement'}:
        raise ValueError('Invalid position settings')
    if ('x' in data and (type(data['x']) not in (int, float) or not 0 <= data['x'] <= 100000)
            or 'y' in data and (type(data['y']) not in (int, float) or not 0 <= data['y'] <= 100000)
            or any(key in data and type(data[key]) is not bool for key in ('hidden', 'voice'))
            or 'movement' in data and data['movement'] not in ('stay', 'roam', 'follow')):
        raise ValueError('Invalid position settings')
    validate(Path('position.json'), data, {})


def _validate_part(section, data, notes_included):
    if section in ('identity', 'growth', 'room'):
        name = FILES[section][0]
        validate(Path(name), data, {})
        if len(_encoded(data)) > MAX_STATE_BYTES:
            raise ValueError(section + ' exceeds its state-file limit')
        if section == 'identity':
            if (not re.fullmatch(r'[^\W_][\w -]{0,23}', data['name'], re.UNICODE)
                    or data['name'] != ' '.join(data['name'].split())
                    or data['class'] not in ('Auto', 'Maker', 'Artist', 'Musician', 'Archivist')
                    or any(item not in ('Maker', 'Artist', 'Musician', 'Archivist') for item in data['interests'])
                    or data['device'] not in ('portable', 'stationary')
                    or not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.:/-]{0,99}', data['model'])
                    or not 0 <= data['seed'] < 65536):
                raise ValueError('Invalid companion identity')
        if section == 'growth':
            if (set(data['traits']) != {'Maker', 'Artist', 'Musician', 'Archivist'}
                    or not 0 <= data['daily'] <= 24
                    or len(data['journal']) > 60
                    or any(item['xp'] < 0 for item in data['journal'])):
                raise ValueError('Invalid growth history')
        if section == 'room':
            notes = data['notes']
            if (data['activity'] not in ('rest', 'read', 'play', 'garden')
                    or len(data['message']) > 4096
                    or len(notes) > 12 or any(len(item['text']) > 4096 for item in notes)):
                raise ValueError('Invalid room state or notes')
            if not notes_included and notes:
                raise ValueError('Transfer claims to exclude notes but contains them')
    elif section == 'settings':
        if type(data) is not dict or not data or set(data) - {'awareness', 'position'}:
            raise ValueError('Invalid settings section')
        if 'awareness' in data:
            validate(Path('awareness-settings.json'), data['awareness'], {})
        if 'position' in data:
            _validate_position(data['position'])
    elif section == 'chat':
        if type(data) is not dict or not data or set(data) - {'history', 'learned'}:
            raise ValueError('Invalid chat section')
        if 'history' in data:
            validate(Path('history.json'), data['history'], [])
            if len(data['history']) > 8 or len(_encoded(data['history'])) > MAX_SMALL_BYTES:
                raise ValueError('Chat history exceeds its transfer limit')
        if 'learned' in data:
            _validate_learned(data['learned'])


def _parse_sections(value, default=DEFAULT_SECTIONS):
    if value is None:
        return tuple(default)
    names = value.split(',') if isinstance(value, str) else value
    if (not isinstance(names, (tuple, list)) or not names
            or any(type(name) is not str or name not in SECTIONS for name in names)
            or len(set(names)) != len(names)):
        raise ValueError('Choose distinct sections from: ' + ', '.join(SECTIONS))
    return tuple(name for name in SECTIONS if name in names)


def build_transfer(state_dir=None, sections=None, include_notes=False, include_chat=False):
    base = Path(state_dir) if state_dir is not None else default_state_dir()
    selected = _parse_sections(sections)
    if include_chat and 'chat' not in selected:
        selected += ('chat',)
    if include_notes and 'room' not in selected:
        raise ValueError('Room must be selected to include notes')
    data = {}
    for section in selected:
        if section in ('identity', 'growth', 'room'):
            value = _existing(base, FILES[section][0], {})
            if value is not None:
                value = copy.deepcopy(value)
                if section == 'growth':
                    value['snapshot'] = {'files': {}, 'repos': {},
                                         'counts': {key: 0 for key in value['traits']},
                                         'limited': False}
                    for key in ('presence_seconds', 'presence_last', 'presence_day', 'presence_daily'):
                        value.pop(key, None)
                if section == 'room' and not include_notes:
                    value['notes'] = []
                data[section] = value
        elif section == 'settings':
            values = {}
            for name, key in (('awareness-settings.json', 'awareness'), ('position.json', 'position')):
                value = _existing(base, name, {})
                if value is not None:
                    values[key] = value
            if values:
                data[section] = values
        else:
            values = {}
            for name, key, default in (('history.json', 'history', []),
                                       ('learned-phrases.json', 'learned', {})):
                value = _existing(base, name, default)
                if value is not None:
                    values[key] = value
            if values:
                data[section] = values
    if not data:
        raise ValueError('No saved state exists for the selected sections')
    included = [name for name in SECTIONS if name in data]
    result = {'format': FORMAT, 'version': VERSION,
              'created': datetime.datetime.now(datetime.timezone.utc).isoformat(),
              'sections': included, 'notesIncluded': bool(include_notes and 'room' in data),
              'data': data}
    validate_transfer(result)
    return result


def validate_transfer(transfer):
    if (type(transfer) is not dict
            or set(transfer) != {'format', 'version', 'created', 'sections', 'notesIncluded', 'data'}
            or transfer['format'] != FORMAT or type(transfer['version']) is not int
            or transfer['version'] != VERSION
            or type(transfer['created']) is not str or len(transfer['created']) > 64
            or type(transfer['notesIncluded']) is not bool
            or type(transfer['data']) is not dict):
        raise ValueError('Unsupported or malformed Wisp transfer')
    try:
        datetime.datetime.fromisoformat(transfer['created'])
    except ValueError as error:
        raise ValueError('Invalid transfer date') from error
    names = transfer['sections']
    if (type(names) is not list or not names or names != list(_parse_sections(names))
            or set(transfer['data']) != set(names)
            or transfer['notesIncluded'] and 'room' not in names):
        raise ValueError('Invalid transfer sections')
    for name in names:
        _validate_part(name, transfer['data'][name], transfer['notesIncluded'])
    _encoded(transfer)
    return transfer


def load_transfer(path):
    raw = _read_regular(Path(path), MAX_TRANSFER_BYTES)
    return validate_transfer(_strict_json(raw))


def preview(transfer):
    validate_transfer(transfer)
    data = transfer['data']
    room = data.get('room', {})
    growth = data.get('growth', {})
    chat = data.get('chat', {})
    privacy = ['Identity includes the companion name and preferences.']
    if 'growth' in data:
        privacy.append('Growth history can contain file names.')
    if 'room' in data:
        privacy.append('Room messages can contain personal text.' +
                       (' Notes are included.' if transfer['notesIncluded'] else ' Notes are excluded.'))
    if 'chat' in data:
        privacy.append('Chat can contain personal text.')
    behavior = []
    if 'growth' in data:
        behavior.append('Growth observation paths and presence counters reset.')
    if 'settings' in data:
        behavior.append('Awareness and voice restart off; screen position resets.')
    if not behavior:
        behavior.append('Other Wisp state stays untouched.')
    return {
        'version': transfer['version'], 'created': transfer['created'],
        'sections': transfer['sections'], 'notesIncluded': transfer['notesIncluded'],
        'noteCount': len(room.get('notes', [])),
        'growthJournalEntries': len(growth.get('journal', [])),
        'chatEntries': len(chat.get('history', [])),
        'learnedPhrases': len(chat.get('learned', {}).get('entries', [])),
        'privacy': ' '.join(privacy),
        'importBehavior': ' '.join(behavior),
    }


def _fsync_directory(directory):
    fd = os.open(directory, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def _atomic_bytes(path, raw, replace=True):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    fd, temporary = tempfile.mkstemp(prefix='.' + path.name + '.transfer-', dir=path.parent)
    try:
        with os.fdopen(fd, 'wb') as stream:
            stream.write(raw)
            stream.flush()
            os.fsync(stream.fileno())
        if replace:
            if os.path.lexists(path) and path.is_symlink():
                raise ValueError('Refusing to replace symlink: ' + path.name)
            os.replace(temporary, path)
        else:
            os.link(temporary, path)
        _fsync_directory(path.parent)
    finally:
        Path(temporary).unlink(missing_ok=True)


def export_transfer(path, state_dir=None, sections=None, include_notes=False, include_chat=False):
    transfer = build_transfer(state_dir, sections, include_notes, include_chat)
    _atomic_bytes(path, _encoded(transfer), replace=False)
    return preview(transfer)


def _prepared_files(transfer, state_dir, sections=None, skip_notes=False):
    selected = _parse_sections(sections, transfer['sections'])
    if not set(selected).issubset(transfer['sections']):
        raise ValueError('A selected section is absent from the transfer')
    data = transfer['data']
    prepared = {}
    for section in selected:
        value = copy.deepcopy(data[section])
        if section == 'growth':
            # Do not compare the new machine's files to old-machine observations.
            value['snapshot'] = {'files': {}, 'repos': {}, 'counts': {key: 0 for key in value['traits']}, 'limited': False}
            value['updated'] = time.time()
            for key in ('presence_seconds', 'presence_last', 'presence_day', 'presence_daily'):
                value.pop(key, None)
            prepared['growth.json'] = value
        elif section == 'room':
            if not transfer['notesIncluded'] or skip_notes:
                current = _existing(state_dir, 'room.json', {})
                value['notes'] = [] if current is None else current['notes']
            prepared['room.json'] = value
        elif section == 'identity':
            prepared['identity.json'] = value
        elif section == 'settings':
            if 'awareness' in value:
                settings = value['awareness']
                settings.update(enabled=False, titles=False, mouse_gestures=False,
                                activity_responses=False, quiet_until=0)
                settings['revision'] = settings.get('revision', 0) + 1
                prepared['awareness-settings.json'] = settings
            if 'position' in value:
                position = value['position']
                position.update(x=24, y=70, hidden=False, voice=False)
                prepared['position.json'] = position
        elif section == 'chat':
            if 'history' in value:
                prepared['history.json'] = value['history']
            if 'learned' in value:
                prepared['learned-phrases.json'] = value['learned']
    for name, value in prepared.items():
        _validate_part({'identity.json': 'identity', 'growth.json': 'growth',
                        'room.json': 'room'}.get(name, 'settings' if name in FILES['settings'] else 'chat'),
                       value if name not in FILES['settings'] + FILES['chat'] else
                       ({'awareness' if name == 'awareness-settings.json' else 'position': value}
                        if name in FILES['settings'] else
                        {'history' if name == 'history.json' else 'learned': value}),
                       True)
    return prepared


def _backup_files(base, names):
    base.mkdir(parents=True, exist_ok=True, mode=0o700)
    backup = Path(tempfile.mkdtemp(prefix=BACKUP_PREFIX, dir=base))
    originals = {}
    try:
        for name in names:
            for suffix in ('', '.bak'):
                filename = name + suffix
                path = base / filename
                raw = _read_regular(path, MAX_STATE_BYTES) if os.path.lexists(path) else None
                originals[filename] = raw
                if raw is not None:
                    _atomic_bytes(backup / filename, raw, replace=False)
        _atomic_bytes(backup / 'manifest.json', _encoded({
            'format': 'wisp-transfer-backup', 'version': 1,
            'files': sorted(originals),
            'absent': sorted(name for name, raw in originals.items() if raw is None),
        }), replace=False)
        return backup, originals
    except BaseException:
        for path in backup.iterdir():
            path.unlink()
        backup.rmdir()
        raise


def _restore_originals(base, originals):
    for filename, raw in originals.items():
        path = base / filename
        if raw is None:
            path.unlink(missing_ok=True)
        else:
            _atomic_bytes(path, raw)


def restore_backup(backup_dir, state_dir=None, apply=False):
    """Restore an import's retained pre-import files after a crash or bad result."""
    base = Path(state_dir) if state_dir is not None else default_state_dir()
    backup = Path(backup_dir)
    if (backup.is_symlink() or not backup.is_dir() or not backup.name.startswith(BACKUP_PREFIX)
            or backup.parent.resolve() != base.resolve()):
        raise ValueError('Choose a Wisp transfer backup directly inside the state directory')
    manifest = _strict_json(_read_regular(backup / 'manifest.json', MAX_SMALL_BYTES))
    allowed = {name + suffix for names in FILES.values() for name in names for suffix in ('', '.bak')}
    if (type(manifest) is not dict
            or set(manifest) != {'format', 'version', 'files', 'absent'}
            or manifest['format'] != 'wisp-transfer-backup' or manifest['version'] != 1
            or type(manifest['files']) is not list or not manifest['files']
            or manifest['files'] != sorted(set(manifest['files']))
            or not set(manifest['files']).issubset(allowed)
            or type(manifest['absent']) is not list
            or manifest['absent'] != sorted(set(manifest['absent']))
            or not set(manifest['absent']).issubset(manifest['files'])):
        raise ValueError('Invalid Wisp transfer backup')
    originals = {}
    for name in manifest['files']:
        path = backup / name
        if name in manifest['absent']:
            if os.path.lexists(path):
                raise ValueError('An absent backup file unexpectedly exists: ' + name)
            originals[name] = None
        else:
            originals[name] = _read_regular(path, MAX_STATE_BYTES)
    result = {'willRestore': manifest['files'], 'from': str(backup)}
    if not apply:
        return result
    with (base / 'transfer.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        safety, current = _backup_files(base, sorted({name.removesuffix('.bak') for name in originals}))
        try:
            _restore_originals(base, originals)
        except BaseException as error:
            try:
                _restore_originals(base, current)
            except BaseException as rollback_error:
                raise RuntimeError('Restore and rollback failed. Current state is backed up at '
                                   + str(safety) + ': ' + str(rollback_error)) from error
            raise
    result.update(applied=True, safetyBackup=str(safety))
    return result


def import_transfer(transfer, state_dir=None, sections=None, skip_notes=False, apply=False):
    validate_transfer(transfer)
    base = Path(state_dir) if state_dir is not None else default_state_dir()
    prepared = _prepared_files(transfer, base, sections, skip_notes)
    comparisons = (('identity.json', 'name', 'identity'),
                   ('growth.json', 'xp', 'earned XP'),
                   ('room.json', 'bond', 'room bond'))
    conflicts = []
    for filename, field, label in comparisons:
        if filename not in prepared:
            continue
        current = _existing(base, filename, {})
        if current is not None and current.get(field) != prepared[filename].get(field):
            conflicts.append({'item': label, 'current': current.get(field),
                              'incoming': prepared[filename].get(field)})
    result = {'willReplace': sorted(prepared), 'willPreserve': 'other Wisp state files',
              'conflicts': conflicts, 'preview': preview(transfer)}
    if not apply:
        return result
    base.mkdir(parents=True, exist_ok=True, mode=0o700)
    with (base / 'transfer.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        # Rebuild after taking the transfer lock; a different transfer may have run.
        prepared = _prepared_files(transfer, base, sections, skip_notes)
        backup, originals = _backup_files(base, prepared)
        try:
            for name, value in prepared.items():
                raw = _encoded(value)
                _atomic_bytes(base / (name + '.bak'), raw)
                _atomic_bytes(base / name, raw)
        except BaseException as error:
            try:
                _restore_originals(base, originals)
            except BaseException as rollback_error:
                raise RuntimeError('Import and rollback failed. Previous state is backed up at '
                                   + str(backup) + ': ' + str(rollback_error)) from error
            raise
    result['backup'] = str(backup)
    result['applied'] = True
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('operation', choices=('preview', 'export', 'inspect', 'import', 'restore'))
    parser.add_argument('file', nargs='?', help='transfer file, or backup directory for restore')
    parser.add_argument('--state-dir', type=Path, default=None)
    parser.add_argument('--sections', help='comma-separated identity,growth,room,settings,chat')
    parser.add_argument('--include-notes', action='store_true', help='include room note text on export')
    parser.add_argument('--include-chat', action='store_true', help='include chat history and learned phrases on export')
    parser.add_argument('--skip-notes', action='store_true', help='keep destination notes on import')
    parser.add_argument('--apply', action='store_true', help='apply an import after its preview')
    args = parser.parse_args(argv)
    if args.operation in ('export', 'inspect', 'import', 'restore') and not args.file:
        parser.error('This operation requires a file or backup directory')
    if args.operation == 'preview':
        result = preview(build_transfer(args.state_dir, args.sections,
                                        args.include_notes, args.include_chat))
    elif args.operation == 'export':
        result = export_transfer(args.file, args.state_dir, args.sections,
                                 args.include_notes, args.include_chat)
        result['file'] = str(Path(args.file))
    elif args.operation == 'restore':
        result = restore_backup(args.file, args.state_dir, args.apply)
    else:
        transfer = load_transfer(args.file)
        result = preview(transfer) if args.operation == 'inspect' else import_transfer(
            transfer, args.state_dir, args.sections, args.skip_notes, args.apply)
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    try:
        main()
    except (OSError, ValueError, TypeError, RuntimeError) as error:
        raise SystemExit('Wisp state transfer: ' + str(error)) from error
