"""Typed local discovery routes; saved bank data is never executable code."""
import subprocess
import shutil

import command_bank


def action_id(entry):
    return 'bank:' + entry['kind'] + ':' + entry['target']


def proposal(message, state_dir, bank=None):
    entry = (command_bank.match(message, state_dir=state_dir) if bank is None
             else bank['aliases'].get(command_bank.normalize(message)))
    if entry is None:
        return None
    return {'text': 'Ready: ' + entry['label'] + '. Tap Run below.',
            'emote': 'working', 'action': action_id(entry), 'actionLabel': entry['label'], 'route':'local'}


def execute(action, state_dir):
    parts = action.split(':') if isinstance(action, str) else []
    if len(parts) != 3 or parts[0] != 'bank':
        raise ValueError('Unsupported personal command.')
    entry = {'kind': parts[1], 'target': parts[2]}
    argv = command_bank.resolve(entry, state_dir=state_dir)
    if not shutil.which(argv[0]):
        raise ValueError('Omarchy is unavailable on this machine.')
    result = subprocess.run(argv, capture_output=True, text=True, timeout=60, check=True)
    if entry['kind'] == 'plugin' and result.stdout.strip() != 'ok':
        raise ValueError('That plugin could not be opened. Check that it is enabled.')
    return {'text': ('Theme command finished: ' if entry['kind'] == 'theme' else 'Open request accepted: ')
            + entry['target'], 'emote': 'working', 'action': '', 'route': 'local'}


def maintenance(message, state_dir, normalize):
    text = normalize(message)
    if text not in ('scan plugins', 'rescan plugins', 'refresh command bank',
                    'refresh my command bank', 'scan installed plugins',
                    'list my plugins', 'show my plugins', 'list themes', 'show themes'):
        return None
    bank = command_bank.scan(state_dir=state_dir)
    if text in ('list my plugins', 'show my plugins'):
        detail = '\n'.join(p['name'] + (' · open by name' if p['enabled'] and p['openable']
                          else ' · no automatic open route') for p in bank['plugins']) or 'No plugins found.'
    elif text in ('list themes', 'show themes'):
        detail = '\n'.join(bank['themes']) or 'No installed themes found.'
    else:
        detail = (f"Found {len(bank['plugins'])} plugins, {len(bank['themes'])} themes, "
                  f"and {len(bank['aliases'])} local phrases. "
                  'Say “list my plugins” or “list themes” to inspect them.')
    if bank.get('persistence_warning'):
        detail += '\nThe bank is usable now but could not be saved to the state directory.'
    return {'text': detail, 'emote': 'reading', 'action': '', 'route':'local'}
