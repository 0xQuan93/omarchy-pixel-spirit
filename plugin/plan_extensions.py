"""Typed plan capabilities from the existing bounded local discovery inventory."""
import hashlib
import command_bank
import parameter_commands

def discover(base, bank=None):
    actions,labels,metadata={}, {}, {}
    if bank is None:bank=command_bank.scan(state_dir=base)
    for entry in bank['aliases'].values():
        kind,target=entry['kind'],entry['target']
        action='bank:'+kind+':'+target
        if len(action)>160 or action in actions:continue
        if kind=='theme':argv=['omarchy','theme','set',target]
        elif kind=='plugin':argv=['omarchy','shell','shell','summon',target,'{}']
        else:continue
        actions[action]=argv;labels[action]=entry['label']
        metadata[action]=dict(sourceId='omarchy.theme' if kind=='theme' else 'plugin.'+hashlib.sha256(target.encode()).hexdigest()[:16],
            sourceLabel='Theme' if kind=='theme' else entry['label'],operation='set' if kind=='theme' else 'open',
            planSafe=True,verification='process' if kind=='theme' else 'accepted')
    typed=parameters()
    actions.update(typed[0]);labels.update(typed[1]);metadata.update(typed[2])
    return actions,labels,metadata

def parameters():
    """Fixed percentage controls do not depend on plugin discovery."""
    actions,labels,metadata={}, {}, {}
    for kind in ('volume','brightness'):
        for amount in range(0 if kind=='volume' else 1,101):
            action=f'param:{kind}:{amount}'
            actions[action]=parameter_commands.resolve(action);labels[action]=f'Set {kind} to {amount}%'
            metadata[action]=dict(sourceId='desktop.volume' if kind=='volume' else 'desktop.brightness',
                sourceLabel='Volume' if kind=='volume' else 'Screen brightness',operation='set',planSafe=True,verification='state' if kind=='volume' else 'process')
    return actions,labels,metadata
