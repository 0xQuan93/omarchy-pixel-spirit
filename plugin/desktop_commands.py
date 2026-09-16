"""Fixed Omarchy desktop actions; never execute commands from discovered metadata.

Menu routes follow Omarchy's shipped default/omarchy/omarchy-menu.jsonc.
The menu owns interactive selection and applies theme/background choices.
Shell and menu summons must return the literal receipt ``ok`` before
the caller reports success; process exit status alone is insufficient.
"""

_MENU_ROUTES = {
    'theme_picker': ('style.theme', 'Choose a theme'),
    'background_picker': ('style.background', 'Choose a wallpaper'),
    'font_picker': ('style.font', 'Choose a font'),
    'settings': ('setup', 'Open settings'),
    'appearance': ('style', 'Open appearance settings'),
    'plugins': ('setup.plugin', 'Manage plugins'),
    'keybindings': ('learn.keybindings', 'Show keyboard shortcuts'),
    'launcher': ('apps', 'Open app launcher'),
    'bar_settings': ('style.bar', 'Open bar settings'),
    'default_apps': ('setup.default', 'Choose default apps'),
    'power_menu': ('system', 'Open power menu'),
    'install_menu': ('install', 'Open install menu'),
    'update_menu': ('update', 'Open update menu'),
    'learn_menu': ('learn', 'Open learning resources'),
    'capture_menu': ('trigger.capture', 'Open screen capture options'),
    'recording_menu': ('trigger.capture.screenrecord', 'Open recording options'),
}

_PANELS = {
    'settings_audio': ('omarchy.audio', 'Open audio settings'),
    'settings_bluetooth': ('omarchy.bluetooth', 'Open Bluetooth settings'),
    'settings_network': ('omarchy.network', 'Open network settings'),
    'settings_display': ('omarchy.monitor', 'Open display controls'),
    'clipboard': ('omarchy.clipboard', 'Open clipboard history'),
    'emoji': ('omarchy.emojis', 'Open emoji picker'),
}

ACTIONS = {
    action: ['omarchy', 'menu', 'summon', route]
    for action, (route, _label) in _MENU_ROUTES.items()
}
ACTIONS.update({
    action: ['omarchy', 'shell', 'shell', 'summon', plugin_id, '{}']
    for action, (plugin_id, _label) in _PANELS.items()
})
ACTIONS.update({
    'background_next': ['omarchy', 'theme', 'bg', 'next'],
    'nightlight_toggle': ['omarchy', 'toggle', 'nightlight'],
    'idle_inhibit': ['omarchy', 'toggle', 'idle', 'stay-awake'],
    'idle_allow': ['omarchy', 'toggle', 'idle', 'allow-idle'],
    # The upstream helper controls the negative flag "bar-off": off shows it.
    'bar_show': ['omarchy', 'toggle', 'bar', 'off'],
    'bar_hide': ['omarchy', 'toggle', 'bar', 'on'],
    'about': ['omarchy', 'launch', 'about'],
})

LABELS = {action: label for action, (_route, label) in _MENU_ROUTES.items()}
LABELS.update({action: label for action, (_plugin, label) in _PANELS.items()})
LABELS.update({
    'background_next': 'Next wallpaper',
    'nightlight_toggle': 'Toggle night light',
    'idle_inhibit': 'Keep the computer awake',
    'idle_allow': 'Allow normal idle behavior',
    'bar_show': 'Show the bar',
    'bar_hide': 'Hide the bar',
    'about': 'Show system information',
})

MENU_ACTIONS = frozenset(_MENU_ROUTES)
IPC_ACTIONS = MENU_ACTIONS | frozenset(_PANELS)
