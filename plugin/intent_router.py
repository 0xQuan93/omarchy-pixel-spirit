"""Bounded compositional proposals after the exact phrase bank has missed.

resolve(message, actions, labels, normalize, extra_targets=None) never executes,
stores data, or calls a model. Successful proposals still require explicit Run.

Extra targets are a list of records, for example::

    {'label': 'Cartoon player',
     'aliases': ['cartoon player', 'cartoons', 'toonami'],
     'verbs': {'open': 'cartoons_on', 'close': 'cartoons_close',
               'pause': 'cartoons_pause', 'resume': 'cartoons_resume',
               'hide': 'cartoons_hide'},
     'hide_without_stopping': True}

Aliases are bare names; a single the/my/this article is accepted by the parser.
Verbs use canonical keys listed in VERBS. IDs must exist in the supplied fixed
catalogue. The optional hide flag is an explicit semantic promise from the
adapter: its hide action leaves playback running. Extra aliases never silently
replace built-in aliases; conflicting valid actions produce a clarification.
"""
import re

VERBS = frozenset({'open', 'close', 'pause', 'resume', 'stop', 'hide',
                   'increase', 'decrease', 'mute', 'unmute', 'enable',
                   'disable', 'toggle', 'focus', 'configure'})
MAX_CHOICES = 4
MAX_TARGETS = 128
MAX_ALIASES = 12


def _target(label, aliases, **verbs):
    return {'label': label, 'aliases': aliases, 'verbs': verbs}


TARGETS = (
    _target('Browser', ('browser', 'web browser', 'internet browser'), open='browser', close='close_browser'),
    _target('Terminal', ('terminal', 'terminal window', 'command prompt'), open='terminal', close='close_terminal'),
    _target('Files', ('files', 'file manager', 'file browser', 'file explorer'), open='files', close='close_files'),
    _target('Notes', ('notes', 'notes app', 'note taking app', 'obsidian'), open='notes', close='close_notes'),
    _target('Reminders', ('reminders', 'reminder panel', 'timers'), open='reminders'),
    _target('Settings', ('settings', 'system settings', 'desktop settings'), open='settings', configure='settings'),
    _target('Audio settings', ('audio settings', 'sound settings', 'audio controls'), open='settings_audio', configure='settings_audio'),
    _target('Bluetooth settings', ('bluetooth settings', 'bluetooth controls'), open='settings_bluetooth', configure='settings_bluetooth'),
    _target('Network settings', ('network settings', 'wifi settings', 'wi-fi settings', 'wireless settings'), open='settings_network', configure='settings_network'),
    _target('Display settings', ('display settings', 'screen settings', 'monitor settings'), open='settings_display', configure='settings_display'),
    _target('Appearance settings', ('appearance', 'appearance settings'), open='appearance', configure='appearance'),
    _target('Theme chooser', ('themes', 'theme picker', 'theme chooser'), open='theme_picker'),
    _target('Wallpaper chooser', ('wallpapers', 'wallpaper picker', 'background picker'), open='background_picker'),
    _target('Font chooser', ('fonts', 'font picker', 'font chooser'), open='font_picker'),
    _target('Plugins', ('plugins', 'plugin manager', 'plugin settings'), open='plugins', configure='plugins'),
    _target('Keyboard shortcuts', ('keyboard shortcuts', 'keybindings', 'shortcut reference'), open='keybindings'),
    _target('App launcher', ('launcher', 'app launcher', 'application launcher'), open='launcher'),
    _target('Clipboard', ('clipboard', 'clipboard history', 'copy history'), open='clipboard'),
    _target('Emoji picker', ('emoji picker', 'emoji selector'), open='emoji'),
    _target('Bar', ('bar', 'top bar', 'status bar', 'desktop bar'), open='bar_show', hide='bar_hide', configure='bar_settings'),
    _target('Default apps', ('default apps', 'default applications'), open='default_apps', configure='default_apps'),
    _target('Power menu', ('power menu', 'power options'), open='power_menu'),
    _target('Learning resources', ('omarchy help', 'omarchy guides', 'learning resources'), open='learn_menu'),
    _target('Volume', ('volume', 'sound volume', 'audio volume', 'speaker volume', 'system volume'), increase='volume_up', decrease='volume_down', mute='mute', unmute='unmute', configure='settings_audio'),
    _target('Speakers', ('speakers', 'speaker audio', 'sound', 'audio output'), increase='volume_up', decrease='volume_down', mute='mute', unmute='unmute', configure='settings_audio'),
    _target('Microphone', ('microphone', 'mic', 'microphone input', 'audio input'), mute='mic_mute', unmute='mic_unmute', configure='settings_audio'),
    _target('Media playback', ('music', 'song', 'track', 'playback', 'media playback', 'music playback', 'audio playback'), pause='pause_music', resume='play_music', toggle='play_pause'),
    _target('Screen brightness', ('brightness', 'screen brightness', 'display brightness', 'monitor brightness'), increase='brightness_up', decrease='brightness_down', configure='settings_display'),
    _target('Keyboard brightness', ('keyboard brightness', 'keyboard backlight brightness'), increase='keyboard_brightness_up', decrease='keyboard_brightness_down'),
    _target('Keyboard lighting', ('keyboard lights', 'keyboard backlight', 'keyboard lighting'), enable='keyboard_brightness_restore', disable='keyboard_brightness_off'),
    _target('Bluetooth', ('bluetooth', 'bluetooth radio'), enable='bluetooth_on', disable='bluetooth_off', configure='settings_bluetooth'),
    _target('Night light', ('night light', 'nightlight', 'night light filter'), enable='nightlight_on', disable='nightlight_off', toggle='nightlight_toggle'),
    _target('Do Not Disturb', ('do not disturb', 'dnd', 'do not disturb mode'), enable='dnd_on', disable='dnd_off'),
    _target('Notifications', ('notifications', 'desktop notifications'), pause='dnd_on', resume='dnd_off', mute='dnd_on', unmute='dnd_off'),
    _target('Power saver', ('power saver', 'battery saver', 'power saver mode', 'battery saver mode'), enable='power_saver', disable='power_balanced'),
    _target('Focused window', ('current window', 'active window', 'focused window', 'current app', 'active app', 'focused app'), close='window_close'),
    _target('Next window', ('next window',), focus='window_next'),
    _target('Previous window', ('previous window',), focus='window_previous'),
    _target('Screen recording', ('screen recording',), stop='recording_stop'),
)

# Each pattern consumes the complete request. Relative controls allow only
# one small increment, never an ignored percentage, count, or timing qualifier.
_SMALL = r'(?: a little| a bit| a notch| one step| by one step| slightly)?'
_PATTERNS = (
    ('hide', re.compile(r'(?:hide|close|put away) (.+) without stopping (?:playback|the playback|the music|the stream|the video|it|them)'), True),
    ('hide', re.compile(r'(?:hide|close|put away) (.+) but keep (?:the video|the music|the stream|it|them) playing'), True),
    ('close', re.compile(r'shut (.+) down'), False),
    ('pause', re.compile(r'put (.+) on pause'), False),
    ('increase', re.compile(r'(?:turn|bump|bring) (.+?) up' + _SMALL), False),
    ('decrease', re.compile(r'(?:turn|bring) (.+?) down' + _SMALL), False),
    ('enable', re.compile(r'(?:turn|switch) (.+?)(?: back)? on'), False),
    ('disable', re.compile(r'(?:turn|switch) (.+) off'), False),
    ('increase', re.compile(r'(?:raise|increase|turn up|bump up) (.+?)' + _SMALL), False),
    ('decrease', re.compile(r'(?:lower|decrease|reduce|turn down) (.+?)' + _SMALL), False),
    ('open', re.compile(r'(?:bring|pull) (.+) up'), False),
    ('open', re.compile(r'(?:open|launch|start|show me|show|bring up|pull up|take me to|get me to) (.+)'), False),
    ('close', re.compile(r'(?:close|quit|exit|shut down) (.+)'), False),
    ('pause', re.compile(r'pause (.+)'), False),
    ('resume', re.compile(r'(?:resume|unpause|continue) (.+)'), False),
    ('stop', re.compile(r'stop (.+)'), False),
    ('hide', re.compile(r'(?:hide|put away) (.+)'), False),
    ('mute', re.compile(r'(?:mute|silence) (.+)'), False),
    ('unmute', re.compile(r'unmute (.+)'), False),
    ('enable', re.compile(r'(?:enable|activate|turn on|switch on) (.+)'), False),
    ('disable', re.compile(r'(?:disable|deactivate|turn off|switch off) (.+)'), False),
    ('toggle', re.compile(r'toggle (.+)'), False),
    ('focus', re.compile(r'(?:focus|select|switch to|go to) (.+)'), False),
    ('configure', re.compile(r'(?:configure|adjust|manage) (.+)'), False),
)
_ALIAS = re.compile(r"[a-z][a-z0-9]*(?:[ '-][a-z0-9]+)*")
_UNSAFE = re.compile(r'\b(?:not|never|no|dont|cannot|cant|without|if|unless|when|after|before|later|tomorrow|then|and|or|also|but|except|until|once|because|while)\b|n\x27t\b')
_PRONOUNS = frozenset({'it', 'that', 'this', 'them', 'that one', 'this one'})
_LEADING = re.compile(r'^(?:just|let me|help me|i want to|i need to) ')


def _safe_words(text):
    # "not" belongs to this explicit setting name, not a request negation.
    return not _UNSAFE.search(text.replace('do not disturb', 'dnd'))


def _catalogue(actions, labels, extra_targets):
    records = list(TARGETS)
    if isinstance(extra_targets, (list, tuple)):
        records.extend(extra_targets[:MAX_TARGETS])
    aliases = {}
    valid = []
    for record in records:
        if not isinstance(record, dict):
            continue
        names, verbs, label = record.get('aliases'), record.get('verbs'), record.get('label')
        if not isinstance(names, (list, tuple)) or not isinstance(verbs, dict):
            continue
        if not isinstance(label, str) or not label or len(label) > 80 or any(ord(c) < 32 for c in label):
            continue
        verbs = {verb: action for verb, action in verbs.items()
                 if verb in VERBS and isinstance(action, str) and action in actions
                 and isinstance(labels.get(action), str)}
        if not verbs:
            continue
        entry = {'label': label, 'verbs': verbs,
                 'hide_without_stopping': record.get('hide_without_stopping') is True}
        valid.append(entry)
        for name in names[:MAX_ALIASES]:
            if not isinstance(name, str) or len(name) > 80 or not _ALIAS.fullmatch(name) or not _safe_words(name):
                continue
            aliases.setdefault(name, []).append(entry)
    return aliases, valid


def _choices(ids, labels):
    result, seen = [], set()
    for action in ids:
        if action not in seen:
            result.append({'action': action, 'label': labels[action]})
            seen.add(action)
        if len(result) == MAX_CHOICES:
            break
    return result


def _clarify(text, choices, reason):
    return {'text': text, 'emote': 'reading', 'action': '', 'actionLabel': '',
            'route': 'local', 'matchType': 'clarify', 'choices': choices, 'reason': reason}


def resolve(message, actions, labels, normalize, extra_targets=None):
    """Return an exact compositional proposal/clarification, or no local match.

    Passed ``actions`` and ``labels`` are the caller's trusted fixed catalogue.
    Target aliases may only point into it. Executable availability and user
    confirmation remain the broker's responsibility; this function has no I/O.
    """
    if not isinstance(message, str) or len(message) > 240:
        return None
    if any(c in message for c in ('"', '“', '”', '`', '\n', '\r', ';', ':')):
        return None
    quoted = message.strip().replace('’', "'")
    if quoted.startswith("'") or quoted.endswith("'") or re.search(r"\s'|'\s", quoted):
        return None
    text = normalize(message)
    if not isinstance(text, str) or not text:
        return None
    for _ in range(2):
        text = _LEADING.sub('', text, count=1)
    aliases, records = _catalogue(actions, labels, extra_targets)
    parses = [(verb, pattern.fullmatch(text), preserving)
              for verb, pattern, preserving in _PATTERNS]
    parses = [(verb, found, preserving) for verb, found, preserving in parses if found]
    preserving = any(keep_playing for _, _, keep_playing in parses)
    if preserving:
        # The whole semantic clause identifies a hide request, not an ordinary
        # close request whose playback constraint can be discarded later.
        parses = [item for item in parses if item[2]]
    elif not _safe_words(text):
        return None
    ids, pronoun_ids, known_targets = [], [], []
    needs_target = False
    for verb, found, preserving_playback in parses:
        raw_target = found[1]
        target = raw_target if raw_target in _PRONOUNS else re.sub(r'^(?:the|my|this) ', '', raw_target, count=1)
        if not _safe_words(target):
            return None
        if target in _PRONOUNS:
            needs_target = True
            pronoun_ids.extend(r['verbs'][verb] for r in records if verb in r['verbs']
                               and (not preserving_playback or r['hide_without_stopping']))
            continue
        targets = aliases.get(target)
        if not targets:
            continue
        known_targets.extend(targets)
        ids.extend(r['verbs'][verb] for r in targets if verb in r['verbs']
                   and (not preserving_playback or r['hide_without_stopping']))
    if needs_target:
        return _clarify('Which target do you mean? Choose a command to review.',
                        _choices(pronoun_ids, labels), 'target-needed')
    choices = _choices(ids, labels)
    if len(choices) == 1:
        action = choices[0]['action']
        return {'text': 'Ready: ' + labels[action] + '. Review and tap Run.',
                'emote': 'working', 'action': action, 'actionLabel': labels[action],
                'route': 'local', 'matchType': 'composed', 'choices': [],
                'reason': 'explicit-target'}
    if choices:
        return _clarify('That request has more than one matching command. Choose one to review.',
                        choices, 'ambiguous-target')
    if known_targets:
        if preserving:
            return _clarify('I do not have a command that hides this target while keeping playback running.',
                            [], 'operation-unavailable')
        alternatives = _choices((a for r in known_targets for a in r['verbs'].values()), labels)
        return _clarify('I do not have that operation for this target. These commands are available to review.',
                        alternatives, 'operation-unavailable')
    return None
