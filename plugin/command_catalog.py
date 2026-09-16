"""Human-facing command descriptions and non-executing search suggestions."""
import re


def decorate(entries, phrases):
    from desktop_commands import CATEGORIES, DESCRIPTIONS
    groups = {'browser':'Apps', 'terminal':'Apps', 'files':'Apps', 'notes':'Apps',
              'reminders':'Reminders', 'dnd_on':'Notifications', 'dnd_off':'Notifications',
              'power_saver':'Power', 'power_balanced':'Power'}
    for entry in entries:
        key = entry['id']
        group = groups.get(key, 'Desktop')
        if key.startswith('workspace_'): group = 'Workspaces'
        if key.startswith('brightness_'): group = 'Display'
        if key in ('volume_up','volume_down','mute','unmute','toggle_mute','pause_music',
                   'play_music','play_pause','next_track','previous_track'): group = 'Audio'
        entry['group'] = CATEGORIES.get(key, entry.get('group', group))
        variants = phrases.get(key, ())
        entry['examples'] = sorted(variants, key=lambda s: (len(s.split()),len(s),s))[:2]
        entry['phraseCount'] = len(variants)
        entry['description'] = DESCRIPTIONS.get(key, entry['label'] + ' using the desktop’s native control.')
    return entries


def personal_entries(state_dir):
    import command_bank
    import command_routes
    import shutil
    bank = command_bank.scan(state_dir=state_dir)
    unique = {}
    for phrase, descriptor in bank['aliases'].items():
        key = command_routes.action_id(descriptor)
        if key not in unique:
            unique[key] = {'id':key,'label':descriptor['label'],'available':bool(shutil.which('omarchy')),
                           'requires':'omarchy','group':'Installed themes' if descriptor['kind']=='theme' else 'Installed plugins',
                           'description':'Discovered on this computer; checked again before running.',
                           'examples':[], 'phraseCount':0}
        entry = unique[key]
        entry['phraseCount'] += 1
        entry['examples'] = sorted(entry['examples']+[phrase], key=lambda s:(len(s),s))[:2]
    return sorted(unique.values(),key=lambda e:(e['group'],e['label']))


def offline_reply(message, entries):
    words = set(re.findall(r'[a-z0-9]+', message.casefold())) - {'the','my','a','to','please','can','you','i'}
    ranked = []
    for entry in entries:
        if not entry['available']: continue
        terms = set(re.findall(r'[a-z0-9]+',' '.join([entry['label'],*entry.get('examples',[])]).casefold()))
        score = len(words & terms)
        if score: ranked.append((score,entry))
    ranked.sort(key=lambda pair:(-pair[0],pair[1]['label']))
    suggestions = [e['examples'][0] for _,e in ranked[:3] if e.get('examples')]
    text = 'Local conversation is unavailable right now. Desktop commands still work without AI.'
    if suggestions:text += '\nTry: ' + ' · '.join('“'+s+'”' for s in suggestions) + '.'
    text += '\nOpen Commands to search what this computer supports.'
    return {'text':text,'action':'','emote':'reading','route':'local'}
