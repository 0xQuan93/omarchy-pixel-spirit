"""Explicit preference for a very small, exact-request speed path.

Only fixed public controls can use this path. A model, discovered command,
personal alias, routine, or approximate intent never supplies its authority.
"""
from pathlib import Path

from storage import get, put
from smart_commands import match


VERSION = 1
FAST_ACTIONS = frozenset({
    'volume_up', 'volume_down', 'mute', 'unmute',
    'pause_music', 'play_music',
})
DEFAULT = {'version': VERSION, 'fastActions': False}


def _path(base):
    return Path(base) / 'interaction-settings.json'


def settings(base):
    value = get(_path(base), DEFAULT)
    if (type(value) is not dict or set(value) != set(DEFAULT)
            or type(value['version']) is not int or value['version'] != VERSION
            or type(value['fastActions']) is not bool):
        raise ValueError('Interaction settings are damaged or from a newer Wisp. They were preserved.')
    return value


def configure(base, value):
    if value not in ('on', 'off'):
        raise ValueError('Choose on or off for quick actions.')
    result = {'version': VERSION, 'fastActions': value == 'on'}
    put(_path(base), result)
    return dict(result, text=('Quick actions are on for exact volume, speaker mute, and playback requests.'
                              if result['fastActions'] else 'Quick actions are off. Commands wait for Run.'))


def eligible(base, message, action, registry, description=None):
    """Recheck the action and source before allowing an already requested Run."""
    if not settings(base)['fastActions'] or action not in FAST_ACTIONS or match(message) != action:
        return False
    info = description if description is not None else registry.describe(action)
    if not info['available']:
        return False
    # Unknown player readiness is sufficient for a reviewed proposal, but not
    # for a direct request. Do not infer a target player from nearby apps.
    if action in {'pause_music', 'play_music'}:
        if info['readiness']['connected'] is not True:
            return False
        from capabilities import ACTIONS
        from readiness import check
        return check(action, ACTIONS[action])['suggestable'] is True
    return True
