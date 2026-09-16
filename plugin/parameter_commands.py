"""Exact, typed percentage controls. No free-form command interpolation."""
import re
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
    if not shutil.which(argv[0]):
        raise ValueError('This control needs ' + argv[0] + '.')
    subprocess.run(argv, capture_output=True, text=True, timeout=12, check=True)
    _, kind, amount = action.split(':')
    return {'text': f'{kind.capitalize()} set to {amount}%.', 'action': '',
            'emote': 'working', 'route': 'local'}


def catalogue():
    return [{'id': f'param:{kind}:50', 'label': f'Set {kind} to 50%',
             'available': bool(shutil.which(tool)), 'requires': tool,
             'group': group, 'description': f'Use an exact percentage ({minimum}–100).',
             'examples': [f'set {kind} to 50 percent'], 'phraseCount': 0}
            for kind, minimum, tool, group in [('volume', 0, 'wpctl', 'Audio'),
                                               ('brightness', 1, 'omarchy', 'Display')]]
