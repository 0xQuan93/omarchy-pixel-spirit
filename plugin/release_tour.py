"""A small, explicit tour of Wisp changes for an existing companion."""
from pathlib import Path

from storage import get, put


VERSION = '2.2.0'
CARDS = (
    {'title': 'See what Wisp knows',
     'text': 'Current machine readings now show their source, check time, and whether Wisp verified a result or only sent a request.',
     'destination': 'chat'},
    {'title': 'Find your Omarchy path',
     'text': 'Commands now show the native menu or shortcut where one is known. The first-use guide offers a small task you can choose.',
     'destination': 'tools'},
    {'title': 'Keep useful flows',
     'text': 'Save a reviewed plan as a routine, then return to it from More. Each use gets a fresh preview and a separate Run.',
     'destination': 'routines'},
    {'title': 'Choose your signals',
     'text': 'Settings now explains each optional observation, its retention, and its switch. Awareness remains under your control.',
     'destination': 'settings'},
)


def _path(base):
    return Path(base) / 'release-tour.json'


def _seen(base):
    data = get(_path(base), {})
    if type(data) is not dict or set(data) not in (set(), {'version', 'seen'}):
        raise ValueError('The tour preference is damaged. It was preserved.')
    if not data:
        return ''
    if (data['version'] != 1 or type(data['seen']) is not str
            or len(data['seen']) > 32):
        raise ValueError('The tour preference is damaged. It was preserved.')
    return data['seen']


def status(base, existing=True):
    try:
        seen = _seen(base)
        error = ''
    except (OSError, ValueError) as problem:
        seen, error = '', str(problem)
    return {'version': VERSION, 'unseen': bool(existing and not error and seen != VERSION),
            'cards': list(CARDS), 'error': error}


def mark_seen(base):
    put(_path(base), {'version': 1, 'seen': VERSION})
    return status(base)
