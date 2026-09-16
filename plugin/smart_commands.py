"""Portable, deterministic phrases for explicit desktop requests.

Only complete utterances match: quoting, explanation, negation, parameters and
compound commands stay in the normal conversation path. No phrase contains an
executable command. ``normalize`` is also the personal plugin bank's key format.
"""
import re
import unicodedata
from collections import defaultdict

_bank = defaultdict(set)


def _add(action, *phrases):
    _bank[action].update(phrases)


def _forms(action, verbs, targets):
    for verb in verbs:
        for target in targets:
            _add(action, verb + ' ' + target)


_OPEN = ('open', 'launch', 'show', 'bring up', 'pull up', 'start')
for _action, _targets in {
    'browser': ('browser', 'the browser', 'my browser', 'a browser', 'the web browser'),
    'terminal': ('terminal', 'the terminal', 'a terminal', 'a terminal window'),
    'files': ('files', 'my files', 'file manager', 'the file manager', 'file explorer', 'the file explorer'),
    'notes': ('notes', 'my notes', 'obsidian', 'the notes app'),
    'reminders': ('reminders', 'my reminders', 'timers', 'my timers', 'the reminders panel'),
}.items():
    _forms(_action, _OPEN, _targets)
_forms('reminders', ('check', 'view', 'show me'), ('my reminders', 'my timers', 'reminders', 'timers'))

_forms('pause_music', ('pause',), ('music', 'the music', 'my music', 'playback', 'the audio', 'the song', 'this song', 'the track'))
_forms('play_music', ('resume', 'continue', 'unpause'), ('music', 'the music', 'my music', 'playback', 'the audio', 'the song', 'the track'))
_add('play_music', 'play music', 'play the music', 'start the music again')
_add('play_pause', 'toggle playback', 'toggle the music', 'toggle media playback', 'play or pause the music')
for _action, _direction in (('next_track', 'next'), ('previous_track', 'previous')):
    _add(_action, _direction + ' track', _direction + ' song')
    _forms(_action, ('play', 'go to', 'skip to', 'switch to'),
           ('the ' + _direction + ' song', 'the ' + _direction + ' track', _direction + ' track'))
_add('next_track', 'skip track', 'skip song', 'skip this track', 'skip this song', 'skip the track', 'skip the song')
_add('previous_track', 'go back a song', 'go back one track', 'play the last song')
for _action, _verbs, _direction in (
    ('volume_down', ('lower', 'decrease', 'reduce', 'turn down'), 'down'),
    ('volume_up', ('raise', 'increase', 'turn up'), 'up'),
):
    _forms(_action, _verbs, ('volume', 'the volume', 'the sound', 'the audio', 'the music volume'))
    _add(_action, 'volume ' + _direction, 'turn the volume ' + _direction, 'turn the sound ' + _direction)
_add('volume_down', 'quieter', 'make it quieter', 'make the music quieter')
_add('volume_up', 'louder', 'make it louder', 'make the music louder')
_forms('mute', ('mute', 'silence'), ('the audio', 'the sound', 'the speakers', 'my speakers'))
_forms('unmute', ('unmute',), ('the audio', 'the sound', 'the speakers', 'my speakers'))
_add('mute', 'mute', 'mute audio', 'mute sound', 'sound off', 'turn off the sound')
_add('unmute', 'unmute', 'unmute audio', 'unmute sound', 'sound on', 'turn the sound back on')
_add('toggle_mute', 'toggle mute', 'toggle audio mute', 'toggle speaker mute')
for _action, _verbs, _direction in (
    ('brightness_down', ('lower', 'decrease', 'reduce', 'turn down'), 'down'),
    ('brightness_up', ('raise', 'increase', 'turn up'), 'up'),
):
    _forms(_action, _verbs, ('brightness', 'the brightness', 'screen brightness', 'the screen brightness', 'display brightness'))
    _add(_action, 'brightness ' + _direction, 'turn the brightness ' + _direction, 'turn screen brightness ' + _direction)
_add('brightness_down', 'dim the screen', 'dim my screen', 'dim the display', 'make the screen dimmer')
_add('brightness_up', 'brighten the screen', 'brighten my screen', 'brighten the display', 'make the screen brighter')
for _action, _direction in (('workspace_next', 'next'), ('workspace_previous', 'previous')):
    _add(_action, _direction + ' workspace', _direction + ' desktop')
    _forms(_action, ('go to', 'switch to', 'take me to', 'move to', 'change to'),
           ('the ' + _direction + ' workspace', 'the ' + _direction + ' desktop'))
_forms('dnd_on', ('enable', 'turn on', 'activate'), ('do not disturb', 'do not disturb mode', 'dnd'))
_forms('dnd_off', ('disable', 'turn off', 'deactivate'), ('do not disturb', 'do not disturb mode', 'dnd'))
_add('dnd_on', 'quiet notifications', 'mute notifications', 'pause notifications', 'silence notifications')
_add('dnd_off', 'resume notifications', 'unmute notifications', 'allow notifications', 'show notifications again')
_forms('power_saver', ('enable', 'turn on', 'use', 'switch to'), ('power saver', 'power saver mode', 'battery saver', 'battery saver mode'))
_forms('power_balanced', ('enable', 'use', 'switch to', 'return to'), ('balanced power', 'balanced power mode', 'balanced mode'))
_add('power_saver', 'save battery')
_add('power_balanced', 'disable power saver', 'turn off power saver', 'disable battery saver', 'turn off battery saver')

# An unspecified theme request opens the chooser; a named theme requires a
# separate parameter-aware path.
_forms('theme_picker', ('change', 'choose', 'pick', 'select', 'switch'), ('theme', 'the theme', 'my theme', 'a theme', 'a new theme'))
_forms('theme_picker', ('open', 'show', 'bring up'), ('themes', 'the theme picker', 'the theme chooser', 'theme selector'))
_add('theme_picker', 'change my desktop theme', 'change the desktop theme', 'change the omarchy theme', 'choose a different theme')
_add('background_next', 'next background', 'next wallpaper', 'cycle wallpaper', 'cycle backgrounds', 'cycle the wallpaper', 'switch to the next wallpaper')
_forms('background_picker', ('change', 'choose', 'pick', 'select'), ('wallpaper', 'the wallpaper', 'my wallpaper', 'the background', 'my background', 'desktop background'))
_forms('background_picker', ('open', 'show', 'bring up'), ('wallpapers', 'backgrounds', 'the wallpaper picker', 'the background picker'))
for _action, _targets in {
    'settings': ('settings', 'the settings', 'omarchy settings', 'system settings'),
    'settings_audio': ('audio settings', 'sound settings', 'volume settings'),
    'settings_bluetooth': ('bluetooth settings', 'bluetooth'),
    'settings_network': ('network settings', 'wifi settings', 'wi-fi settings', 'wireless settings'),
    'settings_display': ('display settings', 'monitor settings', 'screen settings'),
    'appearance': ('appearance settings', 'appearance'),
    'plugins': ('plugin settings', 'plugins', 'the plugin manager'),
    'keybindings': ('keybindings', 'keyboard shortcuts', 'keybinding settings'),
    'launcher': ('launcher', 'the launcher', 'app launcher', 'the app launcher', 'application launcher'),
    'clipboard': ('clipboard', 'the clipboard', 'clipboard history', 'my clipboard history'),
    'emoji': ('emoji picker', 'the emoji picker', 'emoji selector'),
    'font_picker': ('font picker', 'the font picker', 'fonts', 'font settings'),
    'bar_settings': ('bar settings', 'status bar settings'),
    'default_apps': ('default apps', 'default applications', 'default app settings'),
    'power_menu': ('power menu', 'the power menu'),
    'install_menu': ('install menu', 'the install menu', 'software installer'),
    'update_menu': ('update menu', 'the update menu', 'updates'),
    'learn_menu': ('learn menu', 'the learn menu', 'omarchy help', 'omarchy tutorials'),
    'capture_menu': ('capture menu', 'the capture menu', 'screenshot menu'),
    'recording_menu': ('recording menu', 'the recording menu', 'screen recording menu'),
    'about': ('about omarchy', 'omarchy information'),
}.items():
    _forms(_action, ('open', 'show', 'bring up'), _targets)
_forms('font_picker', ('change', 'choose', 'pick'), ('font', 'the font', 'my font', 'a font'))
_add('idle_inhibit', 'keep my screen awake', 'keep the screen awake', 'disable idle sleep', 'inhibit idle')
_add('idle_allow', 'allow idle sleep', 'enable idle sleep', 'allow the screen to sleep')
_add('bar_show', 'show the bar', 'show the status bar', 'show the top bar')
_add('bar_hide', 'hide the bar', 'hide the status bar', 'hide the top bar')
_add('nightlight_toggle', 'toggle night light', 'toggle nightlight', 'toggle night mode')

_GERUNDS = {
    'open': 'opening', 'launch': 'launching', 'show': 'showing', 'bring': 'bringing',
    'pull': 'pulling', 'start': 'starting', 'check': 'checking', 'view': 'viewing',
    'pause': 'pausing', 'resume': 'resuming', 'continue': 'continuing', 'unpause': 'unpausing',
    'play': 'playing', 'go': 'going', 'skip': 'skipping', 'switch': 'switching',
    'lower': 'lowering', 'decrease': 'decreasing', 'reduce': 'reducing', 'turn': 'turning',
    'raise': 'raising', 'increase': 'increasing', 'mute': 'muting', 'unmute': 'unmuting',
    'dim': 'dimming', 'brighten': 'brightening', 'take': 'taking', 'move': 'moving',
    'enable': 'enabling', 'disable': 'disabling', 'change': 'changing', 'choose': 'choosing',
    'pick': 'picking', 'select': 'selecting', 'toggle': 'toggling', 'cycle': 'cycling',
}
for _action, _phrases in tuple(_bank.items()):
    for _phrase in tuple(_phrases):
        _verb, _separator, _target = _phrase.partition(' ')
        if _separator and _verb in _GERUNDS:
            _gerund = _GERUNDS[_verb] + ' ' + _target
            _add(_action, 'would you mind ' + _gerund, 'do you mind ' + _gerund)


def normalize(message):
    """Return a bounded whole-request key, or an empty string for unsafe syntax.

    This does not authorize an action or validate a plugin. Callers must resolve
    the resulting key only against their fixed, validated action catalogue.
    """
    if not isinstance(message, str) or len(message) > 240:
        return ''
    text = unicodedata.normalize('NFKC', message).casefold().strip()
    text = text.replace('’', "'")
    if any(char in text for char in ('"', '“', '”', '`', '\n', '\r', ';', ':')):
        return ''
    if text.startswith("'") or text.endswith("'") or re.search(r"\s'|'\s", text):
        return ''
    text = re.sub(r'\s+', ' ', text)
    text = re.sub(r'[.!?]+$', '', text).strip()
    text = re.sub(r'^(?:(?:hey|hi|okay|ok)\s+)?wisp\s*,?\s+', '', text)
    prefix = (r"^(?:please|can you|could you|would you|will you|can we|could we|"
              r"i want you to|i need you to|i would like you to|"
              r"i was wondering if you could|let's|lets|let us|i'd like to|"
              r"i would like to|go ahead and)(?:,?\s+)")
    suffix = r"(?:,?\s+please|\s+now|\s+for me)$"
    for _ in range(8):
        stripped = re.sub(prefix, '', text)
        stripped = re.sub(suffix, '', stripped).strip()
        if stripped == text:
            break
        text = stripped
    return text


PHRASES = {action: tuple(sorted(phrases)) for action, phrases in _bank.items()}
LOOKUP = {}
for _action, _phrases in PHRASES.items():
    for _phrase in _phrases:
        _key = normalize(_phrase)
        if not _key or (_key in LOOKUP and LOOKUP[_key] != _action):
            raise ValueError('Ambiguous or invalid smart command phrase: ' + _phrase)
        LOOKUP[_key] = _action


def match(message, actions=None):
    """Return a fixed capability ID; optionally restrict to implemented actions."""
    action = LOOKUP.get(normalize(message), '')
    return action if actions is None or action in actions else ''
