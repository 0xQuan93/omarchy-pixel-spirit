"""Reviewed portable registrations. Installed metadata never grants new execution."""
from capability_registry import Registry

PLAN_ACTIONS = frozenset({
    'browser','terminal','files','notes','settings','appearance','theme_picker',
    'background_picker','settings_audio','settings_bluetooth','settings_network',
    'settings_display','keybindings','about','volume_up','volume_down','mute','unmute',
    'brightness_up','brightness_down','dnd_on','dnd_off','power_saver','power_balanced',
})
STATE_ACTIONS = frozenset({'mute','unmute','mic_mute','mic_unmute','power_saver','power_balanced'})

def build(actions, labels, availability=None, extra_metadata=None, extra_targets=(), combinations=()):
    from desktop_commands import ASYNC_ACTIONS
    from intent_router import TARGETS
    metadata = {key:dict(sourceId='desktop',sourceLabel='Desktop',operation=key,
                        planSafe=key in PLAN_ACTIONS,
                        verification='state' if key in STATE_ACTIONS else
                        'accepted' if key in ASYNC_ACTIONS or key in
                        {'browser','terminal','files','notes','reminders','about'} else 'process')
                for key in actions}
    # Authored semantic targets provide stable source names, not executable code.
    assigned=set()
    for index,target in enumerate(TARGETS):
        for operation,key in target['verbs'].items():
            if key in metadata and key not in assigned:
                source='desktop.'+target['aliases'][0].replace(' ','-')
                metadata[key].update(sourceId=source,sourceLabel=target['label'],operation=operation)
                assigned.add(key)
    for key,record in (extra_metadata or {}).items():
        if key not in metadata:raise ValueError('Adapter refers to an unregistered action: '+key)
        metadata[key].update(record)
    return Registry(actions,labels,metadata=metadata,targets=extra_targets,
                    combinations=combinations,availability=availability)
