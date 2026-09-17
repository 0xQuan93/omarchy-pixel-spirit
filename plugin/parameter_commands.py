"""Exact, typed percentage controls. No free-form command interpolation."""
import re
from decimal import Decimal
import shutil
import subprocess
from smart_commands import normalize


def proposal(message):
    text = normalize(message)
    found = re.fullmatch(
        r'(?:set|change|adjust|turn) (?:my |the )?'
        r'(volume|audio volume|sound volume|brightness|screen brightness|display brightness)'
        r' (?:to |at )?(\d{1,3})\s*(?:%|percent)', text)
    if not found:
        return None
    kind = 'volume' if 'volume' in found[1] else 'brightness'
    amount = int(found[2])
    minimum = 0 if kind == 'volume' else 1
    if not minimum <= amount <= 100:
        return {'text': f'Choose {kind} from {minimum} to 100 percent.',
                'action': '', 'emote': 'reading', 'route': 'local'}
    label = f'Set {kind} to {amount}%'
    return {'text': 'Ready: ' + label + '. Tap Run below.', 'emote': 'working',
            'action': f'param:{kind}:{amount}', 'actionLabel': label, 'route': 'local'}


def resolve(action):
    found = re.fullmatch(r'param:(volume|brightness):(0|[1-9]\d?|100)', action or '')
    if not found or (found[1] == 'brightness' and found[2] == '0'):
        raise ValueError('Unsupported percentage command.')
    kind, amount = found[1], found[2]
    if kind == 'volume':
        return ['wpctl', 'set-volume', '-l', '1', '@DEFAULT_AUDIO_SINK@', amount + '%']
    return ['omarchy', 'brightness', 'display', amount + '%']


def execute(action):
    argv = resolve(action)
    _, kind, amount = action.split(':')
    verification = 'state' if kind == 'volume' else 'process'
    def failed(text):
        return {'text': text, 'action': '', 'emote': 'reading', 'route': 'local',
                'ok': False, 'status': 'failed', 'verification': verification,
                'verified': False}
    if not shutil.which(argv[0]):
        return failed('This control needs ' + argv[0] + '.')
    try:
        subprocess.run(argv, capture_output=True, text=True, timeout=12, check=True)
    except (OSError, subprocess.SubprocessError):
        return failed(f'The {kind} command did not finish successfully. The requested state is unconfirmed.')
    if kind == 'brightness':
        return {'text': f'Brightness command finished ({amount}%).', 'action': '',
                'emote': 'working', 'route': 'local', 'ok': True,
                'status': 'completed', 'verification': 'process'}
    try:
        result = subprocess.run(['wpctl', 'get-volume', '@DEFAULT_AUDIO_SINK@'],
                                capture_output=True, text=True, timeout=2, check=True)
        match = re.fullmatch(r'Volume:\s+(\d+(?:\.\d+)?)(?:\s+\[MUTED\])?\s*', result.stdout)
    except (OSError, subprocess.SubprocessError):
        return failed('The volume command finished, but I could not confirm the requested level.')
    if not match or abs(Decimal(match[1]) - Decimal(amount) / 100) > Decimal('0.005'):
        return failed('The volume command finished, but the requested level was not confirmed. Check Sound settings.')
    return {'text': f'Volume confirmed at {amount}%.', 'action': '',
            'emote': 'working', 'route': 'local', 'ok': True,
            'status': 'verified', 'verification': 'state', 'verified': True}


def catalogue():
    entries = []
    for kind, minimum, tool, group in [('volume', 0, 'wpctl', 'Audio'),
                                        ('brightness', 1, 'omarchy', 'Display')]:
        available = bool(shutil.which(tool))
        entries.append({'id': f'param:{kind}:50', 'label': f'Set {kind} to 50%',
            'available': available, 'requires': tool,
            'availabilityReason': '' if available else tool + ' is not installed.',
            'sourceId': 'desktop.' + kind,
            'sourceLabel': 'Volume' if kind == 'volume' else 'Screen brightness',
            'operation': 'set', 'verification': 'state' if kind == 'volume' else 'process',
            'planSafe': True, 'group': group,
            'description': f'Use an exact percentage ({minimum}–100).',
            'examples': [f'set {kind} to 50 percent'], 'phraseCount': 0})
    return entries
