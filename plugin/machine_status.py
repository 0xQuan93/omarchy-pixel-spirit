"""On-demand, read-only answers about a few current machine controls.

Only complete present-tense questions match. No background sampling, user text in
command arguments, model call, or saved machine snapshot is involved.
"""

from pathlib import Path
import re
import subprocess
import time


POWER_SUPPLIES = Path('/sys/class/power_supply')
MAX_SUPPLIES = 32
EVIDENCE_TTL_MS = 5000

_QUESTIONS = (
    ('volume', (
        r"what(?: is|'s) (?:my|the) (?:current )?(?:(?:output|speaker|system|audio) )?volume(?: (?:level|percentage))?(?: at)?",
        r"what (?:my|the) (?:current )?(?:(?:output|speaker|system|audio) )?volume(?: (?:level|percentage))? is",
        r"what (?:level|percentage) is (?:my|the) (?:(?:output|speaker|system|audio) )?volume(?: at)?",
    )),
    ('mute', (
        r"is (?:my|the) (?:(?:output|speaker|system|desktop) )?(?:audio|sound|volume) muted",
        r"are (?:my|the) speakers muted",
        r"is (?:my|the) (?:(?:speaker|audio) )?output muted",
        r"(?:if|whether) (?:my|the) (?:(?:output|speaker|system|desktop) )?(?:audio|sound|volume) is muted",
    )),
    ('profile', (
        r"what(?: is|'s) (?:my|the) (?:current )?power (?:profile|mode)",
        r"what (?:my|the) (?:current )?power (?:profile|mode) is",
        r"(?:which|what) power (?:profile|mode) (?:am i|is my (?:computer|system|machine)) (?:using|on)",
    )),
    ('power_saver', (
        r"is (?:my )?(?:power saver|battery saver)(?: mode)? (?:on|enabled|active)",
        r"(?:if|whether) (?:my )?(?:power saver|battery saver)(?: mode)? is (?:on|enabled|active)",
        r"am i (?:using|on|in) (?:power saver|battery saver)(?: mode)?",
        r"is my (?:computer|laptop|system) in (?:power saver|battery saver) mode",
    )),
    ('battery', (
        r"what(?: is|'s) (?:my|the) (?:current )?battery (?:level|charge|percentage)(?: at)?",
        r"what (?:my|the) (?:current )?battery (?:level|charge|percentage) is",
        r"what(?: is|'s) (?:my|the) battery at",
        r"what percentage is (?:my|the) battery(?: at)?",
        r"how much battery (?:do i have|is left)",
        r"how (?:full|charged) is (?:my|the) battery",
    )),
    ('battery_overview', (
        r"how(?: is|'s) (?:my|the) battery",
    )),
    ('charging', (
        r"is (?:my|the) (?:battery|laptop) charging",
        r"(?:if|whether) (?:my|the) (?:battery|laptop) is charging",
    )),
    ('external', (
        r"am i plugged in",
        r"is (?:my|the) (?:computer|laptop|machine) plugged in",
        r"(?:am i|is (?:my|the) (?:computer|laptop|machine)) on (?:ac|external|wall) power",
        r"is (?:ac|external|wall) power connected",
    )),
)
_QUESTIONS = tuple((kind, tuple(re.compile(pattern) for pattern in patterns))
                   for kind, patterns in _QUESTIONS)
_OTHER_LIVE_QUESTIONS = tuple(re.compile(pattern) for pattern in (
    r"is (?:do not disturb|dnd)(?: mode)? (?:on|off|enabled|active)",
    r"(?:if|whether) (?:do not disturb|dnd)(?: mode)? is (?:on|off|enabled|active)",
    r"how(?: is|'s) (?:my|the) (?:computer|machine|laptop|system) doing",
    r"what(?: is|'s) (?:my|the) (?:current )?(?:computer|machine|laptop|system) (?:status|state)",
    r"is (?:my|the) (?:wifi|wi-fi|internet|network) (?:connected|online)",
    r"what(?: is|'s) (?:my|the) (?:current )?(?:wifi|wi-fi|internet|network) (?:status|state)",
    r"what app is (?:active|focused|open)",
))
_VOLUME = re.compile(r'Volume:\s+(\d+(?:\.\d+)?)(?:\s+(\[MUTED\]))?\s*')


def _question(message):
    if not isinstance(message, str):
        return ''
    question = re.sub(r'\s+', ' ', message.strip().casefold().replace('’', "'"))
    question = question.rstrip('?.!').strip()
    question = re.sub(r'^please,? ', '', question)
    question = re.sub(r'^(?:can|could|would) you (?:please )?tell me ', '', question)
    return question


def question_kind(message):
    """Return a supported state question, without guessing intent from keywords."""
    question = _question(message)
    for kind, patterns in _QUESTIONS:
        if any(pattern.fullmatch(question) for pattern in patterns):
            return kind
    return None


def requires_freshness(message):
    """Keep a few unsupported live machine questions out of the reply cache."""
    question = _question(message)
    return any(pattern.fullmatch(question) for pattern in _OTHER_LIVE_QUESTIONS)


def _command(argv):
    try:
        return subprocess.run(argv, capture_output=True, text=True, timeout=2,
                              check=True).stdout.strip()[:128]
    except (OSError, UnicodeError, subprocess.SubprocessError):
        return None


def read_output_volume():
    value = _command(['wpctl', 'get-volume', '@DEFAULT_AUDIO_SINK@'])
    match = _VOLUME.fullmatch(value) if value is not None else None
    if not match:
        return None
    level = float(match[1])
    if level > 10:
        return None
    return round(level * 100), bool(match[2])


def read_power_profile():
    value = _command(['powerprofilesctl', 'get'])
    return value if value in {'balanced', 'performance', 'power-saver'} else None


def _attribute(path):
    try:
        with path.open(encoding='utf-8') as stream:
            return stream.read(65).strip()
    except (OSError, UnicodeError):
        return None


def read_power_supplies(root=POWER_SUPPLIES):
    """Return battery records and AC state; None means a reading is unknown."""
    try:
        supplies = sorted(root.iterdir(), key=lambda path: path.name)
    except OSError:
        return {'batteries': None, 'external': None}
    if len(supplies) > MAX_SUPPLIES:
        return {'batteries': None, 'external': None}
    batteries = []
    external = []
    unknown_type = False
    for supply in supplies:
        kind = _attribute(supply / 'type')
        if kind is None:
            unknown_type = True
            continue
        if kind == 'Battery':
            if _attribute(supply / 'present') == '0':
                continue
            charge = _attribute(supply / 'capacity')
            capacity = int(charge) if charge and charge.isdecimal() and 0 <= int(charge) <= 100 else None
            state = _attribute(supply / 'status')
            if state not in {'Charging', 'Discharging', 'Full', 'Not charging'}:
                state = None
            name = supply.name if re.fullmatch(r'[A-Za-z0-9_-]{1,24}', supply.name) else 'Battery'
            batteries.append({'name': name, 'capacity': capacity, 'status': state})
        else:
            online = _attribute(supply / 'online')
            if online in {'0', '1'}:
                external.append(online == '1')
            else:
                external.append(None)
    if True in external:
        connected = True
    elif external and all(value is False for value in external) and not unknown_type:
        connected = False
    else:
        connected = None
    if connected is False and any(battery['status'] == 'Charging' for battery in batteries):
        connected = None
    return {'batteries': batteries if not unknown_type else None,
            'external': connected}


def _battery_text(batteries):
    if batteries is None:
        return 'I cannot read the battery status right now.'
    if not batteries:
        return 'I could not find a battery on this machine.'
    if len(batteries) == 1:
        battery = batteries[0]
        if battery['capacity'] is None:
            return 'I found a battery, but I cannot read its charge level.'
        return f"Battery charge is {battery['capacity']}%."
    readings = [f"{battery['name']} {battery['capacity']}%" if battery['capacity'] is not None
                else f"{battery['name']} unknown" for battery in batteries]
    return 'Battery charge by device: ' + ', '.join(readings) + '.'


def _charging_text(batteries):
    if batteries is None:
        return 'I cannot read whether the battery is charging right now.'
    if not batteries:
        return 'I could not find a battery on this machine.'
    if len(batteries) != 1:
        return 'I cannot give one charging state for multiple batteries.'
    state = batteries[0]['status']
    return {
        'Charging': 'The battery reports that it is charging.',
        'Discharging': 'The battery reports that it is discharging.',
        'Full': 'The battery reports that it is full.',
        'Not charging': 'The battery reports that it is not charging.',
    }.get(state, 'I cannot confirm whether the battery is charging right now.')


def reply(message):
    kind = question_kind(message)
    if kind is None:
        return None
    unknown = False
    source_id, source_label = {
        'volume': ('desktop.audio-output', 'Audio output'),
        'mute': ('desktop.audio-output', 'Audio output'),
        'profile': ('desktop.power-profile', 'Power profile'),
        'power_saver': ('desktop.power-profile', 'Power profile'),
        'battery': ('desktop.battery', 'Battery'),
        'battery_overview': ('desktop.battery', 'Battery'),
        'charging': ('desktop.battery', 'Battery'),
        'external': ('desktop.external-power', 'External power'),
    }[kind]
    if kind in {'volume', 'mute'}:
        reading = read_output_volume()
        if reading is None:
            unknown = True
            text = 'I cannot read the current output volume or mute state right now.'
        elif kind == 'mute':
            text = 'The audio output is muted.' if reading[1] else 'The audio output is not muted.'
        else:
            text = f'Output volume is {reading[0]}%.'
            if reading[1]:
                text += ' It is muted.'
    elif kind in {'profile', 'power_saver'}:
        profile = read_power_profile()
        if profile is None:
            unknown = True
            text = 'I cannot read the current power profile right now.'
        elif kind == 'power_saver':
            text = 'Power saver is on.' if profile == 'power-saver' else f'Power saver is off; the current profile is {profile}.'
        else:
            text = f'The current power profile is {profile}.'
    else:
        readings = read_power_supplies()
        if kind in {'battery', 'battery_overview'}:
            unknown = readings['batteries'] is None or not readings['batteries'] or any(
                battery['capacity'] is None for battery in readings['batteries'])
            text = _battery_text(readings['batteries'])
            if kind == 'battery_overview' and readings['batteries']:
                text += ' This charge reading does not measure battery health.'
        elif kind == 'charging':
            unknown = (readings['batteries'] is None or len(readings['batteries']) != 1
                       or readings['batteries'][0]['status'] is None)
            text = _charging_text(readings['batteries'])
        elif readings['external'] is None:
            unknown = True
            text = 'I cannot confirm whether external power is connected right now.'
        else:
            text = ('External power is connected.' if readings['external']
                    else 'External power is not connected.')
    observed = time.time_ns() // 1_000_000
    return {'text': text, 'emote': 'reading', 'action': '', 'route': 'local',
            'evidence': {'sourceId': source_id, 'sourceLabel': source_label,
                         'observedAtMs': observed, 'expiresAtMs': observed + EVIDENCE_TTL_MS,
                         'status': 'unknown' if unknown else 'verified', 'verification': 'state',
                         'unknownReason': text if unknown else ''}}
