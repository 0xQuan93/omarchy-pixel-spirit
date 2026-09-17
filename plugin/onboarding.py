"""Read-only first-run summary and an explicit completion preference.

The caller supplies the registered catalogue and optional scanner result. This
module does not discover applications, inspect transcripts, load an identity,
change awareness consent, start services, call a model, or download anything.
Call status before identity creation during first restore to detect a new user.
"""
import json
import os
from pathlib import Path
import stat
import tempfile

VERSION = 2
MAX_ENTRIES = 4096
MAX_STATE_BYTES = 4096


def _preference(base):
    try:
        fd = os.open(base / 'onboarding.json', os.O_RDONLY | os.O_NONBLOCK | os.O_NOFOLLOW)
        with os.fdopen(fd, 'rb') as stream:
            info = os.fstat(stream.fileno())
            if not stat.S_ISREG(info.st_mode) or info.st_size > MAX_STATE_BYTES:
                return {}
            value = json.loads(stream.read(MAX_STATE_BYTES + 1))
        return value if isinstance(value, dict) else {}
    except (OSError, ValueError, RecursionError):
        return {}


def _name(value):
    if not isinstance(value, str) or not value or len(value) > 80:
        return 'Local controls'
    # Source labels are display names, not executable requirements or paths.
    if '/' in value or '\\' in value or any(ord(c) < 32 for c in value):
        return 'Local controls'
    return value.strip() or 'Local controls'


def status(base, catalogue_entries, scan=None):
    """Summarize supplied capabilities without probing or writing the machine.

    Missing/unknown availability is counted as unavailable. Duplicate action IDs
    count once. Source counts describe registered commands, including unavailable
    ones; availableCount separately describes controls currently available.
    """
    base = Path(base)
    preference = _preference(base)
    completed = preference.get('version') == VERSION and preference.get('completed') is True
    # An existing or damaged identity remains an upgrade, never a fresh install.
    has_identity = any(os.path.lexists(base / name) for name in ('identity.json', 'identity.json.bak'))
    entries = catalogue_entries if isinstance(catalogue_entries, (list, tuple)) else ()
    seen, groups = set(), {}
    available = unavailable = 0
    for entry in entries[:MAX_ENTRIES]:
        if not isinstance(entry, dict):
            continue
        ident = entry.get('id')
        if not isinstance(ident, str) or not ident or len(ident) > 200 or ident in seen:
            continue
        seen.add(ident)
        if entry.get('available') is True:
            available += 1
        else:
            unavailable += 1
        source = _name(entry.get('sourceLabel', 'Local controls'))
        groups[source] = groups.get(source, 0) + 1
    scan = scan if isinstance(scan, dict) else {}
    counts = {key: min(len(scan[key]), MAX_ENTRIES) if isinstance(scan.get(key), list) else 0
              for key in ('plugins', 'themes')}
    text = (f'{available} local commands are available. Review them in Commands; '
            'a local model is optional for conversation.' if available else
            'No local controls are available yet. Review unavailable controls in Commands; '
            'a local model is optional for conversation.')
    return {'version': VERSION, 'completed': completed,
            'showSetup': not completed and not has_identity,
            'availableCount': available, 'unavailableCount': unavailable,
            'sources': [{'name': name, 'count': count} for name, count in sorted(groups.items())],
            'modelOptional': True, 'localCommandsUsable': available > 0,
            'pluginCount': counts['plugins'], 'themeCount': counts['themes'], 'text': text}


def finish(base):
    """Persist completion only in response to the user's setup button."""
    base = Path(base)
    base.mkdir(parents=True, exist_ok=True, mode=0o700)
    preference = {'version': VERSION, 'completed': True}
    fd, temporary = tempfile.mkstemp(prefix='.onboarding-', dir=base)
    try:
        with os.fdopen(fd, 'w') as stream:
            json.dump(preference, stream)
            stream.write('\n')
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, base / 'onboarding.json')
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)
    return preference
