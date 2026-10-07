"""Bounded, read-only readiness checks for a few stateful desktop controls.

The result is advisory until Run. The fixed broker command and its own receipt
remain the final authority. No player metadata, microphone audio, or prompt is
retained; one registry instance may reuse one probe for related controls.
"""
import json
import re
import shutil
import subprocess


MEDIA_ACTIONS = frozenset({'pause_music', 'play_music', 'play_pause',
                           'next_track', 'previous_track'})
MIC_ACTIONS = frozenset({'mic_mute', 'mic_unmute'})
MAX_STATUS_BYTES = 8192
PROBE_TIMEOUT = 1
_VOLUME = re.compile(r'Volume:\s+\d+(?:\.\d+)?(?:\s+\[MUTED\])?\s*')


def _media_status():
    try:
        result = subprocess.run(['omarchy', 'shell', 'media', 'status'],
                                capture_output=True, text=True, timeout=PROBE_TIMEOUT,
                                check=True)
        if len(result.stdout) > MAX_STATUS_BYTES:
            return None
        data = json.loads(result.stdout)
        if (not isinstance(data, dict) or type(data.get('hasPlayer')) is not bool
                or type(data.get('playing')) is not bool):
            return None
        # The shell status can contain track metadata. Keep only control facts.
        return {key: data.get(key) for key in ('hasPlayer', 'playing',
                                              'canGoNext', 'canGoPrevious', 'canTogglePlaying')}
    except (OSError, UnicodeError, ValueError, TypeError, subprocess.SubprocessError):
        return None


def _microphone_present():
    try:
        result = subprocess.run(['wpctl', 'get-volume', '@DEFAULT_AUDIO_SOURCE@'],
                                capture_output=True, text=True, timeout=PROBE_TIMEOUT,
                                check=True)
        return bool(_VOLUME.fullmatch(result.stdout[:128]))
    except (OSError, UnicodeError, TypeError, subprocess.SubprocessError):
        return False


def check(action, argv, cache=None):
    """Return installed/connected/actionable without executing the control.

    Unknown connection state permits a normal Run attempt so older shell APIs
    still work, but unsolicited hints require a confirmed connection.
    """
    cache = cache if cache is not None else {}
    if not shutil.which(argv[0]):
        return {'installed': False, 'connected': None, 'actionable': False,
                'suggestable': False, 'reason': argv[0] + ' is not installed.'}
    if action in MEDIA_ACTIONS:
        if 'media' not in cache:
            cache['media'] = _media_status()
        state = cache['media']
        if state is None:
            return {'installed': True, 'connected': None, 'actionable': True,
                    'suggestable': False,
                    'reason': 'Current player state could not be checked; Run will ask the desktop.'}
        if not state['hasPlayer']:
            return {'installed': True, 'connected': False, 'actionable': False,
                    'suggestable': False, 'reason': 'No controllable media player is open.'}
        if action == 'pause_music':
            suggestable = state['playing'] and state['canTogglePlaying'] is True
        elif action == 'play_music':
            suggestable = not state['playing'] and state['canTogglePlaying'] is True
        elif action in {'next_track', 'previous_track'}:
            key = 'canGoNext' if action == 'next_track' else 'canGoPrevious'
            if type(state[key]) is not bool:
                return {'installed': True, 'connected': None, 'actionable': True,
                        'suggestable': False,
                        'reason': 'Track controls could not be checked; Run will ask the desktop.'}
            suggestable = state[key]
        else:
            suggestable = state['canTogglePlaying'] is True
        # Omarchy can fall back to a different source player when the selected
        # player cannot handle an action. The active-player snapshot is enough
        # to choose useful tips, but not enough to deny an explicit request.
        return {'installed': True, 'connected': True, 'actionable': True,
                'suggestable': suggestable, 'reason': ''}
    if action in MIC_ACTIONS:
        if 'microphone' not in cache:
            cache['microphone'] = _microphone_present()
        if cache['microphone']:
            return {'installed': True, 'connected': True, 'actionable': True,
                    'suggestable': True, 'reason': ''}
        return {'installed': True, 'connected': None, 'actionable': True,
                'suggestable': False,
                'reason': 'Default microphone state could not be checked; Run will ask the desktop.'}
    return {'installed': True, 'connected': None, 'actionable': True,
            'suggestable': True, 'reason': ''}
