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
    'default_browser': ('setup.default.browser', 'Choose the default browser'),
    'default_terminal': ('setup.default.terminal', 'Choose the default terminal'),
    'default_editor': ('setup.default.editor', 'Choose the default editor'),
    'screenshot': ('trigger.capture.screenshot', 'Take a screenshot'),
    'capture_text': ('trigger.capture.text', 'Copy text from the screen'),
    'capture_qr': ('trigger.capture.qr', 'Scan a QR code on the screen'),
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

# Exact receipts differ between shell services. In particular nightlight returns
# its requested state immediately, before hyprsunset finishes applying it.
RECEIPTS = {action: frozenset({'ok'}) for action in IPC_ACTIONS}
ASYNC_ACTIONS = set(IPC_ACTIONS)
CONFIRM_ACTIONS = frozenset({'window_close'})
CATEGORIES = {action: 'Settings' for action in ACTIONS}
DESCRIPTIONS = {action: label + '.' for action, label in LABELS.items()}


def _add(action, argv, label, category, description, receipt=None, asynchronous=False):
    ACTIONS[action] = argv
    LABELS[action] = label
    CATEGORIES[action] = category
    DESCRIPTIONS[action] = description
    if receipt is not None:
        RECEIPTS[action] = frozenset({receipt})
    if asynchronous:
        ASYNC_ACTIONS.add(action)


for _state, _method, _receipt in (('on', 'enable', 'enabled'), ('off', 'disable', 'disabled')):
    _add('nightlight_' + _state, ['omarchy', 'shell', 'nightlight', _method],
         'Turn night light ' + _state, 'Display',
         'Request ' + ('warmer evening colors.' if _state == 'on' else 'normal daytime colors.'),
         receipt=_receipt, asynchronous=True)
    _add('bluetooth_' + _state, ['omarchy', 'bluetooth', 'power', _state],
         'Turn Bluetooth ' + _state, 'Network',
         'Turn all Bluetooth adapters ' + _state + '; this preference survives reboot.')

for _action, _value, _label in (('mic_mute', '1', 'Mute the microphone'),
                               ('mic_unmute', '0', 'Unmute the microphone')):
    _add(_action, ['wpctl', 'set-mute', '@DEFAULT_AUDIO_SOURCE@', _value],
         _label, 'Audio', _label + ' for the default input device.')

for _verb, _label in (('up', 'Brighten the keyboard'), ('down', 'Dim the keyboard'),
                      ('off', 'Turn off keyboard lighting'), ('restore', 'Restore keyboard lighting')):
    _add('keyboard_brightness_' + _verb, ['omarchy', 'brightness', 'keyboard', _verb],
         _label, 'Display', _label + ' on a supported backlit keyboard.')

_add('audio_output_next', ['omarchy', 'audio', 'output', 'switch'],
     'Switch audio output', 'Audio', 'Cycle to the next available speaker or headphone output.')
_add('recording_stop', ['omarchy', 'capture', 'screenrecording', '--stop-recording'],
     'Stop screen recording', 'Capture', 'Ask the current recording to stop and save.')

# These Lua dispatchers are the same fixed expressions shipped in Omarchy's
# default/hypr/bindings/tiling.lua. No user text is interpolated into Lua.
for _direction, _code in (('left', 'l'), ('right', 'r'), ('up', 'u'), ('down', 'd')):
    _add('window_focus_' + _direction,
         ['hyprctl', 'dispatch', 'hl.dsp.focus({ direction = "' + _code + '" })'],
         'Focus the window ' + _direction, 'Windows',
         'Focus the neighboring window ' + _direction + ' of the active window.', receipt='ok')
    _add('window_swap_' + _direction,
         ['hyprctl', 'dispatch', 'hl.dsp.window.swap({ direction = "' + _code + '" })'],
         'Swap window ' + _direction, 'Windows',
         'Swap the window focused when Run is pressed with its neighbor ' + _direction + '.', receipt='ok')

for _number in range(1, 11):
    _workspace = str(_number)
    _add('workspace_' + _workspace,
         ['hyprctl', 'dispatch', 'hl.dsp.focus({ workspace = "' + _workspace + '" })'],
         'Go to workspace ' + _workspace, 'Workspaces',
         'Focus workspace ' + _workspace + '.', receipt='ok')
    _add('window_workspace_' + _workspace,
         ['hyprctl', 'dispatch', 'hl.dsp.window.move({ workspace = "' + _workspace + '" })'],
         'Move window to workspace ' + _workspace, 'Workspaces',
         'Move the window focused when Run is pressed to workspace ' + _workspace + ' and follow it.', receipt='ok')

_DISPATCHERS = {
    'window_next': ('hl.dsp.window.cycle_next()', 'Focus the next window', 'Windows'),
    'window_previous': ('hl.dsp.window.cycle_next({ next = false })', 'Focus the previous window', 'Windows'),
    'window_fullscreen_toggle': ('hl.dsp.window.fullscreen({ mode = "fullscreen" })', 'Toggle window fullscreen', 'Windows'),
    'window_maximize_toggle': ('hl.dsp.window.fullscreen({ mode = "maximized" })', 'Toggle window maximization', 'Windows'),
    'window_float_toggle': ('hl.dsp.window.float({ action = "toggle" })', 'Toggle floating window', 'Windows'),
    'window_close': ('hl.dsp.window.close()', 'Close the focused window', 'Windows'),
    'workspace_former': ('hl.dsp.focus({ workspace = "previous" })', 'Return to the former workspace', 'Workspaces'),
    'monitor_next': ('hl.dsp.focus({ monitor = "+1" })', 'Focus the next monitor', 'Display'),
    'monitor_previous': ('hl.dsp.focus({ monitor = "-1" })', 'Focus the previous monitor', 'Display'),
    'scratchpad_toggle': ('hl.dsp.workspace.toggle_special("scratchpad")', 'Toggle the scratchpad', 'Workspaces'),
    'window_to_scratchpad': ('hl.dsp.window.move({ workspace = "special:scratchpad", follow = false })', 'Move window to scratchpad', 'Workspaces'),
}
for _action, (_expression, _label, _category) in _DISPATCHERS.items():
    _add(_action, ['hyprctl', 'dispatch', _expression], _label, _category,
         _label + '; uses the focused window or workspace when Run is pressed.', receipt='ok')
DESCRIPTIONS['window_close'] = 'Close the window focused when Run is pressed. Its app may ask to save unsaved work.'

for _action, _route, _label in (
    ('window_gaps_toggle', ['hyprland', 'window', 'gaps', 'toggle'], 'Toggle window gaps'),
    ('window_transparency_toggle', ['hyprland', 'window', 'transparency', 'toggle'], 'Toggle focused window transparency'),
    ('workspace_layout_toggle', ['hyprland', 'workspace', 'layout', 'toggle'], 'Toggle workspace layout'),
):
    _add(_action, ['omarchy'] + _route, _label, 'Windows', _label + '.')

for _category, _actions in {
    'Appearance': ('theme_picker', 'background_picker', 'background_next', 'font_picker', 'appearance', 'bar_settings', 'bar_show', 'bar_hide'),
    'Audio': ('settings_audio',),
    'Network': ('settings_network', 'settings_bluetooth'),
    'Display': ('settings_display', 'nightlight_toggle', 'idle_inhibit', 'idle_allow'),
    'Capture': ('capture_menu', 'recording_menu', 'screenshot', 'capture_text', 'capture_qr'),
    'Apps': ('launcher', 'clipboard', 'emoji', 'default_apps', 'default_browser', 'default_terminal', 'default_editor'),
    'Learn': ('keybindings', 'learn_menu', 'about'),
}.items():
    for _action in _actions:
        CATEGORIES[_action] = _category
DESCRIPTIONS.update({
    'screenshot': 'Open the native screenshot selector; select a region or window to capture.',
    'capture_text': 'Select screen text for OCR and copying to the clipboard.',
    'capture_qr': 'Select a QR code on the screen to decode it.',
    'power_menu': 'Choose a power action in the native menu; opening it does not shut down the computer.',
    'install_menu': 'Browse the native software installation choices.',
    'update_menu': 'Browse native update and maintenance choices.',
})
ASYNC_ACTIONS = frozenset(ASYNC_ACTIONS)
