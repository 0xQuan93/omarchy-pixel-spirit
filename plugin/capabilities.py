"""The actual fixed desktop tool catalogue, shared by UI, routing and model."""
import shutil
ACTIONS = {
 'browser': ['omarchy','launch','browser'],
 'terminal': ['omarchy','launch','terminal'],
 'files': ['omarchy','launch','nautilus'],
 'volume_up': ['wpctl','set-volume','-l','1','@DEFAULT_AUDIO_SINK@','5%+'],
 'volume_down': ['wpctl','set-volume','@DEFAULT_AUDIO_SINK@','5%-'],
 'mute': ['wpctl','set-mute','@DEFAULT_AUDIO_SINK@','1'],
 'unmute': ['wpctl','set-mute','@DEFAULT_AUDIO_SINK@','0'],
 'toggle_mute': ['wpctl','set-mute','@DEFAULT_AUDIO_SINK@','toggle'],
 'pause_music': ['omarchy','shell','media','pause'],
 'play_music': ['omarchy','shell','media','play'],
 'play_pause': ['omarchy','shell','media','playPause'],
 'next_track': ['omarchy','shell','media','next'],
 'brightness_up': ['brightnessctl','set','+5%'],
 'brightness_down': ['brightnessctl','set','5%-'],
 'workspace_next': ['hyprctl','dispatch','hl.dsp.focus({ workspace = "e+1" })'],
 'workspace_previous': ['hyprctl','dispatch','hl.dsp.focus({ workspace = "e-1" })'],
 'power_saver': ['powerprofilesctl','set','power-saver'],
 'power_balanced': ['powerprofilesctl','set','balanced'],
}
ACTIONS.update({
 'dnd_on': ['omarchy','shell','notifications','setDnd','on'],
 'dnd_off': ['omarchy','shell','notifications','setDnd','off'],
 'notes': ['obsidian'],
 'reminders': ['omarchy','shell','pixel-spirit','reminders'],
})
LABELS = {
 'browser':'Open browser', 'terminal':'Open terminal', 'files':'Open file manager',
 'notes':'Open Obsidian', 'volume_up':'Raise volume', 'volume_down':'Lower volume',
 'mute':'Mute audio', 'unmute':'Unmute audio', 'toggle_mute':'Toggle mute',
 'pause_music':'Pause music', 'play_music':'Resume music', 'play_pause':'Toggle playback',
 'next_track':'Next track', 'brightness_up':'Brighten screen', 'brightness_down':'Dim screen',
 'workspace_next':'Next workspace', 'workspace_previous':'Previous workspace',
 'power_saver':'Enable power saver', 'power_balanced':'Use balanced power',
 'dnd_on':'Quiet notifications', 'dnd_off':'Resume notifications',
 'reminders':'Open timers and reminders',
}
def registry(availability_override=None, extensions=None):
 actions=dict(ACTIONS);labels=dict(LABELS);extra={}
 if extensions:
  new_actions,new_labels,extra=extensions
  if set(new_actions)&set(actions):raise ValueError('Extensions cannot replace built-in controls.')
  actions.update(new_actions);labels.update(new_labels)

 from capability_specs import build
 return build(actions,labels,availability_override,extra)

def catalogue(state_dir=None, include_personal=False):
 from smart_commands import PHRASES
 from command_catalog import decorate, personal_entries
 controls=registry()
 entries=decorate([controls.describe(key) for key in ACTIONS],PHRASES)
 if include_personal:
  from parameter_commands import catalogue as percentages
  extras=percentages()+personal_entries(state_dir)
  from plan_extensions import discover
  expanded=registry(extensions=discover(state_dir))
  for entry in extras:
   if entry['id'] in expanded.plan_allowed():
    entry.update({key:value for key,value in expanded.describe(entry['id']).items() if key not in {'id','label','requires'}})
  entries += extras
 return entries

MEDIA_ACTIONS = {'pause_music','play_music','play_pause','next_track'}

# Portable Omarchy destinations, shared with personal overlays.
from desktop_commands import ACTIONS as DESKTOP_ACTIONS, LABELS as DESKTOP_LABELS
ACTIONS.update(DESKTOP_ACTIONS)
LABELS.update(DESKTOP_LABELS)
ACTIONS['previous_track'] = ['omarchy','shell','media','previous']
LABELS['previous_track'] = 'Previous track'
MEDIA_ACTIONS.add('previous_track')
