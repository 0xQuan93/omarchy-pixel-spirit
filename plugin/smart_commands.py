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

# Destination-specific vocabulary helps beginners describe the same control in
# their own words. These are complete requests, not substring triggers. Menu
# actions open a chooser; they do not infer a user's final choice.
_DESTINATIONS = {
    'browser': ('browser', 'the browser', 'my browser', 'a browser', 'the web browser', 'my web browser', 'a web browser', 'the internet browser', 'my default browser', 'the default browser'),
    'terminal': ('terminal', 'the terminal', 'a terminal', 'my terminal', 'a terminal window', 'the terminal window', 'a new terminal', 'a new terminal window', 'the command line', 'my command line'),
    'files': ('files', 'my files', 'the file manager', 'my file manager', 'file manager', 'file explorer', 'the file explorer', 'my file explorer', 'the files app', 'the file browser'),
    'notes': ('notes', 'my notes', 'obsidian', 'the notes app', 'my notes app', 'the obsidian app', 'my obsidian app', 'the note taking app'),
    'reminders': ('reminders', 'my reminders', 'timers', 'my timers', 'the reminders panel', 'the timers panel', 'the reminder list', 'my reminder list', 'my scheduled reminders', 'the timer controls'),
    'theme_picker': ('themes', 'the themes', 'theme picker', 'the theme picker', 'theme chooser', 'the theme chooser', 'theme selector', 'the theme selector', 'theme options', 'my theme options', 'available themes', 'the available themes', 'desktop themes', 'omarchy themes', 'theme selection'),
    'background_picker': ('wallpapers', 'backgrounds', 'the wallpapers', 'the backgrounds', 'wallpaper picker', 'the wallpaper picker', 'background picker', 'the background picker', 'wallpaper options', 'background options', 'available wallpapers', 'desktop backgrounds', 'wallpaper selection'),
    'font_picker': ('fonts', 'the fonts', 'font picker', 'the font picker', 'font chooser', 'the font chooser', 'font options', 'font selection', 'available fonts', 'the available fonts', 'font settings', 'desktop fonts'),
    'settings': ('settings', 'the settings', 'my settings', 'system settings', 'the system settings', 'desktop settings', 'the desktop settings', 'omarchy settings', 'the settings menu', 'system configuration', 'desktop configuration'),
    'settings_audio': ('audio settings', 'the audio settings', 'sound settings', 'the sound settings', 'volume settings', 'the volume settings', 'audio controls', 'the audio controls', 'sound controls', 'the sound controls', 'sound devices', 'audio devices', 'the audio panel', 'speaker settings', 'microphone settings', 'audio output settings', 'audio input settings'),
    'settings_bluetooth': ('bluetooth', 'bluetooth settings', 'the bluetooth settings', 'bluetooth controls', 'the bluetooth controls', 'bluetooth devices', 'my bluetooth devices', 'the bluetooth panel', 'bluetooth configuration', 'bluetooth connections', 'my bluetooth connections'),
    'settings_network': ('network settings', 'the network settings', 'wifi settings', 'the wifi settings', 'wi-fi settings', 'wireless settings', 'wireless networks', 'wifi networks', 'available networks', 'network connections', 'the network connections', 'my network connections', 'the network panel', 'internet settings', 'connection settings'),
    'settings_display': ('display settings', 'the display settings', 'monitor settings', 'the monitor settings', 'screen settings', 'the screen settings', 'display controls', 'monitor controls', 'the display panel', 'the monitor panel', 'monitor configuration', 'display configuration'),
    'appearance': ('appearance', 'appearance settings', 'the appearance settings', 'desktop appearance', 'desktop appearance settings', 'style settings', 'the style settings', 'the style menu', 'customization options', 'desktop customization', 'the appearance menu'),
    'plugins': ('plugins', 'my plugins', 'the plugins', 'plugin settings', 'the plugin settings', 'plugin manager', 'the plugin manager', 'plugin management', 'plugin options', 'the plugin menu', 'installed plugins', 'the installed plugins'),
    'keybindings': ('keybindings', 'my keybindings', 'the keybindings', 'keyboard shortcuts', 'the keyboard shortcuts', 'my keyboard shortcuts', 'shortcut help', 'the shortcuts list', 'the keybindings list', 'keybinding help', 'keyboard shortcut help', 'omarchy shortcuts'),
    'launcher': ('launcher', 'the launcher', 'app launcher', 'the app launcher', 'application launcher', 'the application launcher', 'applications', 'my applications', 'the applications menu', 'the apps menu', 'my apps'),
    'clipboard': ('clipboard', 'the clipboard', 'my clipboard', 'clipboard history', 'the clipboard history', 'my clipboard history', 'clipboard manager', 'the clipboard manager', 'copied items', 'my copied items', 'recently copied items'),
    'emoji': ('emoji picker', 'the emoji picker', 'emoji selector', 'the emoji selector', 'emojis', 'the emojis', 'emoji menu', 'the emoji menu', 'emoji selection'),
    'bar_settings': ('bar settings', 'the bar settings', 'status bar settings', 'the status bar settings', 'top bar settings', 'the top bar settings', 'bar configuration', 'status bar configuration', 'bar options'),
    'default_apps': ('default apps', 'the default apps', 'default applications', 'my default applications', 'my default apps', 'default app settings', 'default application settings', 'default app preferences', 'default program settings'),
    'power_menu': ('power menu', 'the power menu', 'power options', 'the power options', 'the system menu', 'shutdown options', 'the shutdown options', 'restart options', 'logout options'),
    'install_menu': ('install menu', 'the install menu', 'software installer', 'the software installer', 'installation options', 'the installation options', 'app installation options', 'software installation options', 'the software installation menu'),
    'update_menu': ('update menu', 'the update menu', 'updates', 'the updates', 'update options', 'the update options', 'system update options', 'software update options', 'the system update menu'),
    'learn_menu': ('learn menu', 'the learn menu', 'omarchy help', 'omarchy tutorials', 'learning resources', 'the learning resources', 'omarchy learning resources', 'the help menu', 'omarchy documentation', 'omarchy guides'),
    'capture_menu': ('capture menu', 'the capture menu', 'screenshot menu', 'the screenshot menu', 'screen capture options', 'the screen capture options', 'capture options', 'screenshot options', 'the screenshot options'),
    'recording_menu': ('recording menu', 'the recording menu', 'screen recording menu', 'the screen recording menu', 'recording options', 'the recording options', 'screen recording options', 'the screen recording options'),
    'about': ('system information', 'my system information', 'the system information', 'omarchy information', 'the about screen', 'the system information screen', 'system details', 'my system details', 'omarchy version information'),
}
_NAVIGATE = ('open', 'show', 'show me', 'bring up', 'pull up', 'bring me to',
             'take me to', 'go to', 'let me see', 'let me access', 'display',
             'view', 'access', 'get me to')
for _action, _targets in _DESTINATIONS.items():
    _forms(_action, _NAVIGATE, _targets)

# Chooser requests express the desired operation while keeping actual selection
# in the desktop's own UI. No theme, device, package or font name is invented.
for _action, _targets in {
    'theme_picker': ('theme', 'the theme', 'my theme', 'desktop theme', 'the desktop theme', 'my desktop theme', 'omarchy theme', 'the omarchy theme'),
    'background_picker': ('wallpaper', 'the wallpaper', 'my wallpaper', 'background', 'the background', 'my background', 'desktop background', 'the desktop background', 'my desktop background'),
    'font_picker': ('font', 'the font', 'my font', 'desktop font', 'the desktop font', 'my desktop font', 'system font', 'the system font'),
}.items():
    _forms(_action, ('change', 'choose', 'pick', 'select', 'switch', 'replace',
                     'let me change', 'let me choose', 'let me pick', 'let me select',
                     'help me change', 'help me choose', 'i want to change',
                     'i want to choose', 'i need to change'), _targets + ('a ' + _targets[0],))
    for _target in ('a new ' + _targets[0], 'a different ' + _targets[0], 'another ' + _targets[0]):
        _forms(_action, ('choose', 'pick', 'select', 'try', 'let me choose',
                         'let me pick', 'i want to choose', 'i want to try'), (_target,))

# Transport operations keep the selected player and audio source unchanged.
_MEDIA_TARGETS = ('music', 'the music', 'my music', 'the audio', 'audio playback',
                  'the audio playback', 'music playback', 'the music playback',
                  'media playback', 'the media playback', 'playback', 'the playback',
                  'the song', 'this song', 'the track', 'this track', 'the player')
_forms('pause_music', ('pause', 'put a pause on', 'temporarily pause'), _MEDIA_TARGETS)
_forms('play_music', ('resume', 'unpause', 'continue', 'get back to'), _MEDIA_TARGETS)
_forms('play_pause', ('toggle',), ('playback', 'audio playback', 'music playback', 'media playback', 'the player playback'))
for _action, _direction in (('next_track', 'next'), ('previous_track', 'previous')):
    _forms(_action, ('play', 'go to', 'skip to', 'switch to', 'move to', 'put on', 'jump to', 'start playing'),
           tuple(article + _direction + ' ' + noun for article in ('', 'the ') for noun in ('song', 'track', 'music track', 'audio track')))
_add('previous_track', 'go back to the last song', 'go back to the last track', 'skip back a song', 'skip back a track')
for _action, _verbs, _direction, _adjective in (
    ('volume_down', ('lower', 'decrease', 'reduce', 'turn down'), 'down', 'quieter'),
    ('volume_up', ('raise', 'increase', 'turn up'), 'up', 'louder'),
):
    _forms(_action, _verbs, ('volume', 'the volume', 'my volume', 'the audio volume', 'audio volume', 'speaker volume', 'the speaker volume', 'the music volume', 'music volume', 'system volume', 'the system volume', 'the sound level', 'the audio level', 'the sound', 'the audio', 'the music'))
    for _target in ('the volume', 'the audio volume', 'the speaker volume', 'the music volume', 'the sound', 'the audio', 'the music'):
        _add(_action, 'turn ' + _target + ' ' + _direction, 'bring ' + _target + ' ' + _direction)
    _forms(_action, ('make',), tuple(target + ' ' + _adjective for target in ('it', 'the music', 'the audio', 'the sound', 'my speakers', 'the speakers', 'my computer')))
for _action, _verbs in (('mute', ('mute', 'silence')), ('unmute', ('unmute',))):
    _forms(_action, _verbs, ('audio', 'the audio', 'sound', 'the sound', 'the speakers', 'my speakers', 'the speaker audio', 'system audio', 'the system audio', 'desktop audio', 'the desktop audio', 'the audio output', 'my audio output'))
for _action, _verbs, _direction in (
    ('brightness_down', ('lower', 'decrease', 'reduce', 'turn down'), 'down'),
    ('brightness_up', ('raise', 'increase', 'turn up'), 'up'),
):
    _forms(_action, _verbs, ('brightness', 'the brightness', 'my brightness', 'screen brightness', 'the screen brightness', 'my screen brightness', 'display brightness', 'the display brightness', 'my display brightness', 'monitor brightness', 'the monitor brightness', 'my monitor brightness', 'the brightness of my screen', 'the brightness of the screen'))
    for _target in ('the brightness', 'my screen brightness', 'the screen brightness', 'the display brightness'):
        _add(_action, 'turn ' + _target + ' ' + _direction)
for _action, _verb, _adjective in (('brightness_down', 'dim', 'dimmer'), ('brightness_up', 'brighten', 'brighter')):
    _forms(_action, (_verb,), ('the screen', 'my screen', 'the display', 'my display', 'the monitor', 'my monitor'))
    _forms(_action, ('make',), tuple(target + ' ' + _adjective for target in ('the screen', 'my screen', 'the display', 'my display', 'the monitor', 'my monitor')))
for _action, _direction in (('workspace_next', 'next'), ('workspace_previous', 'previous')):
    _forms(_action, ('go to', 'switch to', 'move to', 'take me to', 'change to', 'jump to', 'focus', 'show', 'show me', 'bring me to'),
           tuple(article + _direction + ' ' + noun for article in ('', 'the ') for noun in ('workspace', 'desktop', 'virtual desktop')))
for _action, _verbs in (('dnd_on', ('enable', 'activate', 'turn on', 'switch on', 'start using')), ('dnd_off', ('disable', 'deactivate', 'turn off', 'switch off', 'stop using'))):
    _forms(_action, _verbs, ('do not disturb', 'do not disturb mode', 'dnd', 'dnd mode', 'notification silence mode'))
_forms('dnd_on', ('mute', 'silence', 'pause'), ('notifications', 'my notifications', 'the notifications', 'desktop notifications', 'the desktop notifications', 'notification alerts'))
_forms('dnd_off', ('resume', 'unmute', 'allow'), ('notifications', 'my notifications', 'the notifications', 'desktop notifications', 'the desktop notifications', 'notification alerts'))
_forms('power_saver', ('enable', 'activate', 'turn on', 'use', 'switch to', 'start using', 'put the computer in'), ('power saver', 'power saver mode', 'battery saver', 'battery saver mode', 'power saving mode'))
_forms('power_balanced', ('enable', 'activate', 'use', 'switch to', 'return to', 'start using', 'put the computer in'), ('balanced mode', 'balanced power mode', 'balanced power', 'the balanced power profile'))
_forms('background_next', ('show', 'switch to', 'go to', 'try', 'use', 'display', 'put on', 'cycle to'), ('the next wallpaper', 'the next background', 'the next desktop background'))
_forms('bar_show', ('show', 'unhide', 'bring back', 'restore'), ('the bar', 'my bar', 'the top bar', 'my top bar', 'the status bar', 'my status bar', 'the desktop bar'))
_forms('bar_hide', ('hide',), ('the bar', 'my bar', 'the top bar', 'my top bar', 'the status bar', 'my status bar', 'the desktop bar'))
_forms('idle_inhibit', ('keep',), ('my computer awake', 'the computer awake', 'my desktop awake', 'the desktop awake', 'my screen awake', 'the screen awake'))
_forms('idle_allow', ('allow', 'let'), ('my computer sleep when idle', 'the computer sleep when idle', 'my screen sleep when idle', 'the screen sleep when idle'))

# Configuration intents open the matching controls so choices remain explicit.
for _action in ('settings', 'settings_audio', 'settings_bluetooth', 'settings_network',
                'settings_display', 'appearance', 'plugins', 'bar_settings', 'default_apps'):
    _forms(_action, ('configure', 'adjust', 'manage', 'review', 'check', 'inspect'),
           _DESTINATIONS[_action])
_add('settings_audio', 'change my audio device', 'choose my audio output',
     'choose my microphone', 'change my sound device', 'select an audio device')
_add('settings_bluetooth', 'pair a bluetooth device', 'connect a bluetooth device',
     'manage my bluetooth devices', 'pair my headphones')
_add('settings_network', 'connect to wifi', 'connect to wi-fi', 'choose a wifi network',
     'choose a wireless network', 'change my wifi network', 'manage my network connection')
_add('settings_display', 'configure my monitors', 'configure my displays',
     'adjust my display settings', 'adjust my monitor settings')
_add('plugins', 'manage my plugins', 'configure my plugins', 'change my plugin settings')
_add('default_apps', 'change my default apps', 'choose my default applications')

# Fixed window/workspace actions. Numerical destinations are explicitly bounded
# to the ten verified workspace actions; they never become shell arguments.
_WINDOW_TARGETS = ('this window', 'the current window', 'the active window',
                   'the focused window', 'my current window', 'this app window',
                   'the current app window', 'the focused app window')
_NUMBERS = ('one', 'two', 'three', 'four', 'five', 'six', 'seven', 'eight', 'nine', 'ten')
_ORDINALS = ('first', 'second', 'third', 'fourth', 'fifth', 'sixth', 'seventh', 'eighth', 'ninth', 'tenth')
for _number, (_word, _ordinal) in enumerate(zip(_NUMBERS, _ORDINALS), 1):
    _destinations = tuple(noun + ' ' + number for noun in ('workspace', 'desktop', 'virtual desktop')
                          for number in (str(_number), _word)) + tuple('the ' + _ordinal + ' ' + noun for noun in ('workspace', 'desktop', 'virtual desktop'))
    _forms('workspace_' + str(_number), ('go to', 'switch to', 'jump to', 'focus', 'show', 'show me', 'take me to', 'bring me to', 'change to', 'move to'), _destinations)
    _add('workspace_' + str(_number), 'workspace ' + str(_number), 'workspace ' + _word)
    for _verb in ('move', 'send', 'put'):
        for _target in _WINDOW_TARGETS:
            for _destination in _destinations:
                _add('window_workspace_' + str(_number), _verb + ' ' + _target + (' on ' if _verb == 'put' else ' to ') + _destination)
for _direction, _position in (('left', 'on the left'), ('right', 'on the right'), ('up', 'above'), ('down', 'below')):
    _forms('window_focus_' + _direction, ('focus', 'select', 'switch to', 'go to', 'activate'),
           ('the window ' + _position, 'the app window ' + _position, 'the neighboring window ' + _position))
    _add('window_focus_' + _direction, 'focus ' + _direction, 'move focus ' + _direction,
         'move window focus ' + _direction, 'focus the window ' + _direction)
    for _target in _WINDOW_TARGETS:
        _add('window_swap_' + _direction, 'swap ' + _target + ' ' + _direction,
             'swap ' + _target + ' with the window ' + _position,
             'exchange ' + _target + ' with the window ' + _position)
for _action, _direction in (('window_next', 'next'), ('window_previous', 'previous')):
    _forms(_action, ('focus', 'select', 'switch to', 'go to', 'activate', 'cycle to'),
           ('the ' + _direction + ' window', 'the ' + _direction + ' app window'))
    _add(_action, _direction + ' window')
_forms('window_close', ('close', 'quit', 'dismiss'), _WINDOW_TARGETS)
for _action, _mode in (('window_fullscreen_toggle', 'fullscreen'), ('window_maximize_toggle', 'maximization'), ('window_float_toggle', 'floating')):
    _add(_action, 'toggle ' + _mode, 'toggle window ' + _mode)
    for _target in _WINDOW_TARGETS:
        _add(_action, 'toggle ' + _mode + ' for ' + _target, 'toggle ' + _mode + ' on ' + _target,
             'toggle ' + _target + ' ' + _mode)
_forms('workspace_former', ('go back to', 'return to', 'switch back to', 'take me back to', 'focus'),
       ('the last workspace', 'my last workspace', 'the last desktop', 'my last desktop', 'the workspace i was on', 'the desktop i was on', 'the previously focused workspace'))
for _action, _direction in (('monitor_next', 'next'), ('monitor_previous', 'previous')):
    _forms(_action, ('focus', 'switch to', 'go to', 'move focus to', 'take me to'),
           ('the ' + _direction + ' monitor', 'the ' + _direction + ' display', 'the ' + _direction + ' screen'))
_forms('scratchpad_toggle', ('toggle',), ('scratchpad', 'the scratchpad', 'my scratchpad', 'the scratchpad workspace'))
for _target in _WINDOW_TARGETS:
    _forms('window_to_scratchpad', ('move', 'send'), (_target + ' to the scratchpad', _target + ' to my scratchpad'))
_forms('window_gaps_toggle', ('toggle',), ('gaps', 'window gaps', 'the window gaps', 'gaps between windows', 'the gaps between windows'))
_forms('window_transparency_toggle', ('toggle',), ('transparency', 'window transparency', 'the window transparency', 'transparent windows'))
_forms('workspace_layout_toggle', ('toggle',), ('workspace layout', 'the workspace layout', 'my workspace layout', 'the window layout', 'window layout'))

# Explicit state controls have separate IDs. Toggle-only controls never borrow
# enable/disable phrasing that could silently reverse the requested state.
for _action, _verbs, _targets in (
    ('nightlight_on', ('enable', 'activate', 'turn on', 'switch on', 'start using'), ('night light', 'nightlight', 'the night light', 'night light mode', 'the night light filter')),
    ('nightlight_off', ('disable', 'deactivate', 'turn off', 'switch off', 'stop using'), ('night light', 'nightlight', 'the night light', 'night light mode', 'the night light filter')),
    ('bluetooth_on', ('enable', 'activate', 'turn on', 'switch on'), ('bluetooth', 'my bluetooth', 'the bluetooth radio', 'bluetooth connectivity')),
    ('bluetooth_off', ('disable', 'deactivate', 'turn off', 'switch off'), ('bluetooth', 'my bluetooth', 'the bluetooth radio', 'bluetooth connectivity')),
    ('mic_mute', ('mute', 'silence', 'turn off', 'switch off'), ('mic', 'the mic', 'my mic', 'microphone', 'the microphone', 'my microphone', 'microphone input', 'the microphone input', 'my microphone input', 'audio input', 'my audio input')),
    ('mic_unmute', ('unmute', 'turn on', 'switch on'), ('mic', 'the mic', 'my mic', 'microphone', 'the microphone', 'my microphone', 'microphone input', 'the microphone input', 'my microphone input', 'audio input', 'my audio input')),
    ('keyboard_brightness_up', ('raise', 'increase', 'turn up'), ('keyboard brightness', 'the keyboard brightness', 'my keyboard brightness', 'keyboard backlight brightness', 'the keyboard backlight brightness')),
    ('keyboard_brightness_down', ('lower', 'decrease', 'reduce', 'turn down'), ('keyboard brightness', 'the keyboard brightness', 'my keyboard brightness', 'keyboard backlight brightness', 'the keyboard backlight brightness')),
    ('keyboard_brightness_off', ('turn off', 'disable', 'switch off'), ('keyboard backlight', 'the keyboard backlight', 'my keyboard backlight', 'keyboard lighting', 'the keyboard lighting')),
    ('keyboard_brightness_restore', ('restore', 'turn on', 'enable', 'switch on'), ('keyboard backlight', 'the keyboard backlight', 'my keyboard backlight', 'keyboard lighting', 'the keyboard lighting')),
):
    _forms(_action, _verbs, _targets)
_add('mic_mute', 'mic off', 'microphone off', 'mute myself')
_add('mic_unmute', 'mic on', 'microphone on', 'unmute myself')
_add('keyboard_brightness_up', 'brighten the keyboard', 'make the keyboard brighter', 'keyboard brightness up')
_add('keyboard_brightness_down', 'dim the keyboard', 'make the keyboard dimmer', 'keyboard brightness down')
_forms('audio_output_next', ('switch to', 'cycle to', 'use', 'select'), ('the next audio output', 'the next sound output', 'the next output device', 'the next audio device'))
_add('audio_output_next', 'cycle audio outputs', 'cycle sound outputs', 'cycle output devices', 'next audio output')
_forms('screenshot', ('take', 'grab', 'capture', 'save'), ('a screenshot', 'a screen shot', 'a screen capture'))
_add('screenshot', 'take screenshot', 'take a screenshot of my screen', 'screenshot my screen')
_forms('capture_text', ('capture', 'extract', 'copy', 'recognize'), ('text from the screen', 'text from my screen', 'the text on the screen', 'the text on my screen', 'text from a screen region'))
_add('capture_text', 'screen ocr', 'ocr my screen', 'extract screen text')
_forms('capture_qr', ('scan', 'read', 'capture', 'decode'), ('a qr code', 'the qr code', 'a qr code on my screen', 'the qr code on the screen', 'the onscreen qr code'))
_forms('recording_stop', ('stop', 'finish', 'end'), ('screen recording', 'the screen recording', 'my screen recording', 'recording my screen', 'recording the screen'))
for _action, _app in (('default_browser', 'browser'), ('default_terminal', 'terminal'), ('default_editor', 'editor')):
    _forms(_action, ('change', 'choose', 'pick', 'select', 'set', 'let me change', 'let me choose'),
           ('default ' + _app, 'the default ' + _app, 'my default ' + _app, 'a default ' + _app))
    _forms(_action, _NAVIGATE, ('default ' + _app + ' settings', 'the default ' + _app + ' settings', 'default ' + _app + ' options'))

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


# Authored everyday requests, informed by primary voice-access documentation:
# https://support.google.com/accessibility/android/answer/6151854?hl=en
# https://support.microsoft.com/en-us/accessibility/windows/voice-access/voice-access-command-list
# https://support.apple.com/en-gb/guide/mac-help/mh40719/mac
# Familiar words and explicit targets reduce the need to remember UI jargon.
# These are separately reviewed requests, not permission to infer intent from
# complaints ("I cannot hear"), questions, diagnoses, or unsupported commands.
# Keep this after gerund generation: each entry adds useful wording, not padding.
EVERYDAY_PHRASES = {
    'browser': ('bring up a browser for me', 'get a browser going',
                'launch my internet browser', 'open the app i use for the web'),
    'terminal': ('give me a terminal window', 'bring up a command prompt',
                 'open a command prompt', 'start a terminal session'),
    'files': ('let me browse my files', 'bring up my folders',
              'open the app for browsing files', 'get me to my file browser'),
    'notes': ('bring up my note taking app', 'let me open my notes',
              'open the app i use for notes'),
    'reminders': ('let me see the timers i have running', 'bring up my reminder list',
                  'show the timers and reminders panel', 'let me check my reminders'),
    'pause_music': ('put the music on hold', 'put this song on pause',
                    'pause what is playing', "pause what's playing", 'media pause'),
    'play_music': ('carry on playing the music', 'carry on with the song',
                   'pick up the music where it paused', 'get the song playing again', 'media play'),
    'next_track': ('skip over this song', 'move on to the next song',
                   'jump ahead to the next track', 'skip ahead one song'),
    'previous_track': ('go back to the song before this', 'skip back one song',
                       'take me back one track', 'return to the previous song'),
    'volume_down': ('take the volume down a notch', 'turn the music down a bit',
                    'make the sound a little quieter', 'lower the sound a little',
                    'bring the audio down a notch', 'reduce the speaker volume a little'),
    'volume_up': ('give me a bit more volume', 'turn the music up a bit',
                  'make the sound a little louder', 'raise the sound a little',
                  'bump the volume up a notch', 'increase the speaker volume a little'),
    'mute': ('mute the speaker output', 'switch the sound off',
             'mute the computer audio', 'silence the desktop audio'),
    'unmute': ('bring the sound back', 'switch the sound back on',
               'unmute the computer audio', 'restore audio output'),
    'mic_mute': ('turn my microphone off', 'switch my mic off',
                 'turn off the microphone input', 'mute my input audio'),
    'mic_unmute': ('turn my microphone back on', 'switch my mic back on',
                   'unmute the microphone input', 'unmute my input audio'),
    'brightness_down': ('take the screen brightness down a notch',
                        'make the display a little dimmer', 'dim the screen a bit',
                        'turn the screen brightness down a little'),
    'brightness_up': ('give the screen a little more brightness',
                      'make the display a little brighter', 'brighten the screen a bit',
                      'turn the screen brightness up a little'),
    'keyboard_brightness_down': ('dim the keyboard lights a little',
                                 'turn the keyboard lighting down a notch'),
    'keyboard_brightness_up': ('brighten the keyboard lights a little',
                               'turn the keyboard lighting up a notch'),
    'keyboard_brightness_off': ('turn my keyboard lights off', 'switch off the keyboard lights'),
    'keyboard_brightness_restore': ('bring the keyboard lights back', 'turn my keyboard lights back on'),
    'dnd_on': ('put notifications on hold', 'quiet my desktop notifications',
               'turn notification interruptions off', 'put my notifications on pause'),
    'dnd_off': ('let notifications through again', 'bring back my notifications',
                'take notifications off pause', 'turn notification interruptions back on'),
    'theme_picker': ('let me try a different desktop look', 'bring up the desktop theme choices',
                     'let me pick a color theme', 'change the colour theme',
                     'change the color theme', 'show me the colour themes'),
    'background_picker': ('let me pick a picture for my desktop',
                          'change my desktop picture', 'change the desktop background picture',
                          'show me the background choices'),
    'background_next': ('try another wallpaper from this theme',
                        'cycle to another background in this theme'),
    'font_picker': ('let me choose a different desktop font',
                    'show me the desktop typefaces', 'open the typeface picker'),
    'settings': ('take me to the desktop controls', 'bring up the computer settings',
                 'let me adjust my desktop settings'),
    'settings_audio': ('let me choose which speakers to use', 'let me pick my microphone',
                       'show me where to change audio devices', 'open the sound control panel',
                       'bring up the input and output audio controls'),
    'settings_bluetooth': ('bring up the bluetooth device list',
                           'let me manage my bluetooth connections',
                           'open the controls for pairing bluetooth devices'),
    'settings_network': ('bring up the wireless network choices', 'let me pick a wifi connection',
                         'get me to the wifi controls', 'open the internet connection settings'),
    'settings_display': ('let me adjust my screens', 'bring up my monitor controls',
                         'open the controls for my displays'),
    'appearance': ('let me customise the desktop', 'let me customize the desktop',
                   'open desktop customisation', 'open desktop customization'),
    'plugins': ('let me manage desktop plugins', 'bring up the desktop add-ons',
                'open the desktop extension settings'),
    'keybindings': ('show me the keys i can use', 'bring up the shortcut cheat sheet',
                    'show the keyboard shortcut reference', 'let me look up a keyboard shortcut'),
    'launcher': ('bring up the list of apps', 'let me pick an app to open',
                 'show me the application picker'),
    'clipboard': ('show me what i copied earlier', 'bring up my copy history',
                  'let me choose from my copied items', 'open the copied text history'),
    'emoji': ('let me pick an emoji', 'bring up the emoji choices', 'show me the emoji list'),
    'bar_settings': ('let me customise the top bar', 'let me customize the top bar',
                     'bring up the desktop bar options'),
    'default_apps': ('let me choose my preferred apps', 'open preferred application settings',
                     'bring up the default program choices'),
    'default_browser': ('let me choose which browser to use by default',
                        'change my preferred web browser'),
    'default_terminal': ('let me choose which terminal to use by default',
                         'change my preferred terminal app'),
    'default_editor': ('let me choose which editor to use by default',
                       'change my preferred text editor'),
    'power_menu': ('show me the power choices', 'bring up the shutdown menu',
                   'let me see the restart options'),
    'install_menu': ('show me the options for installing apps',
                     'bring up the software installation choices'),
    'update_menu': ('show me the options for updating my system',
                    'bring up the software update choices'),
    'learn_menu': ('show me how to get started with omarchy',
                   'bring up the omarchy beginner guides', 'open the omarchy learning menu'),
    'about': ('show me the details about this computer',
              'bring up the information about my system'),
    'capture_menu': ('show me the screen capture choices', 'bring up screenshot options'),
    'screenshot': ('snap a screenshot', 'grab a picture of my screen',
                   'take a picture of the screen'),
    'capture_text': ('get the text from part of my screen',
                     'copy text out of the screen', 'let me capture some screen text'),
    'capture_qr': ('read a qr code from my screen', 'scan the qr code on my display'),
    'recording_menu': ('show me how i can record my screen',
                       'let me choose screen recording options'),
    'recording_stop': ('wrap up the screen recording', 'finish capturing my screen',
                       'stop the screen video recording'),
    'workspace_next': ('hop over to the next workspace', 'take me one workspace forward'),
    'workspace_previous': ('hop over to the previous workspace', 'take me one workspace back'),
    'workspace_former': ('take me back to the workspace i was using',
                         'return me to my last workspace'),
    'window_next': ('switch focus to the next window', 'cycle forward through my windows'),
    'window_previous': ('switch focus to the previous window', 'cycle backward through my windows'),
    'window_close': ('close the window i am using', "close the window i'm using"),
    'window_fullscreen_toggle': ('toggle full screen for this window',
                                 'toggle this window between fullscreen and normal'),
    'window_maximize_toggle': ('toggle this window between maximised and normal',
                               'toggle this window between maximized and normal'),
    'window_float_toggle': ('toggle this window between floating and tiled',),
    'monitor_next': ('move my focus to the next screen', 'take me to the next display'),
    'monitor_previous': ('move my focus to the previous screen', 'take me to the previous display'),
    'scratchpad_toggle': ('toggle the scratchpad view',),
    'window_to_scratchpad': ('put this window in the scratchpad',
                             'send the window i am using to the scratchpad'),
    'bar_show': ('bring my top bar back', 'make the desktop bar visible again'),
    'bar_hide': ('hide the bar at the top', 'take the desktop bar out of view'),
    'power_saver': ('put my computer in power saving mode', 'switch to the battery saving profile'),
    'power_balanced': ('go back to the balanced power profile', 'leave battery saver mode'),
    'idle_inhibit': ('keep the computer from going idle', 'keep my display awake'),
    'idle_allow': ('let the computer go idle again', 'restore normal idle behavior',
                   'restore normal idle behaviour'),
    'nightlight_on': ('switch the night light on', 'enable the night light filter'),
    'nightlight_off': ('switch the night light off', 'disable the night light filter'),
    'bluetooth_on': ('switch the bluetooth radio on', 'turn bluetooth back on'),
    'bluetooth_off': ('switch the bluetooth radio off',),
}
for _action, _phrases in EVERYDAY_PHRASES.items():
    _add(_action, *_phrases)


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
    return _strip_request(text)


_REQUEST_PREFIX = re.compile(
    r"^(?:please|can you|could you|would you|will you|can we|could we|"
    r"i want you to|i need you to|i would like you to|"
    r"i was wondering if you could|let's|lets|let us|i'd like to|"
    r"i would like to|go ahead and)(?:,?\s+)")
_REQUEST_SUFFIX = re.compile(r"(?:,?\s+please|\s+now|\s+for me)$")
_AUTHORED_PHRASE = re.compile(r"[a-z0-9]+(?:[ '-][a-z0-9]+)*")


def _strip_request(text):
    for _ in range(8):
        stripped = (_REQUEST_PREFIX.sub('', text)
                    if text.startswith(('please', 'can ', 'could ', 'would ', 'will ',
                                        'i ', "i'd ", "let's", 'lets', 'let ', 'go '))
                    else text)
        if stripped.endswith((' please', ' now', ' for me')):
            stripped = _REQUEST_SUFFIX.sub('', stripped).strip()
        if stripped == text:
            break
        text = stripped
    return text


def _authored_key(phrase):
    """Compile trusted, canonical source phrases without input sanitization.

    Incoming requests always use normalize(). The narrow source grammar rejects
    new noncanonical phrases, and tests exhaustively compare these keys with the
    public normalizer. This avoids 20,000 redundant Unicode/punctuation passes
    each time a short-lived desktop helper starts.
    """
    if len(phrase) > 240 or not _AUTHORED_PHRASE.fullmatch(phrase):
        raise ValueError('Noncanonical smart command phrase: ' + phrase)
    return _strip_request(phrase)


PHRASES = {action: tuple(sorted(phrases)) for action, phrases in _bank.items()}
LOOKUP = {}
for _action, _phrases in PHRASES.items():
    for _phrase in _phrases:
        _key = _authored_key(_phrase)
        if not _key or (_key in LOOKUP and LOOKUP[_key] != _action):
            raise ValueError('Ambiguous or invalid smart command phrase: ' + _phrase)
        LOOKUP[_key] = _action


def match(message, actions=None):
    """Return a fixed capability ID; optionally restrict to implemented actions."""
    action = LOOKUP.get(normalize(message), '')
    return action if actions is None or action in actions else ''
