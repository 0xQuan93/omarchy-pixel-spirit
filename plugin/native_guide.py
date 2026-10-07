"""Read-only native Omarchy paths for controls Wisp already knows.

The host command catalogue confirms displayed CLI routes. It never registers an
action, supplies argv, or grants execution authority to discovered metadata.
"""
import json
import re
import subprocess
import time

MAX_OUTPUT = 512 * 1024
MAX_COMMANDS = 1024
MAX_AGE = 300
_cache = None
_checked_at = 0

# Shortcuts are Omarchy defaults, not a reading of the user's custom bindings.
PATHS = {
    'browser': {'route': 'omarchy launch browser', 'shortcut': 'Super + Shift + Return', 'menu': 'Apps → Browser'},
    'terminal': {'route': 'omarchy launch terminal', 'shortcut': 'Super + Return', 'menu': 'Apps → Terminal'},
    'files': {'route': 'omarchy launch nautilus', 'shortcut': 'Super + Shift + F', 'menu': 'Apps → Files'},
    'keybindings': {'shortcut': 'Super + K', 'menu': 'Learn → Keybindings'},
    'settings_audio': {'shortcut': 'Super + Ctrl + A'},
    'settings_bluetooth': {'shortcut': 'Super + Ctrl + B'},
    'settings_network': {'shortcut': 'Super + Ctrl + W'},
    'settings_display': {'shortcut': 'Super + Ctrl + D'},
    'theme_picker': {'menu': 'Style → Theme'},
    'background_picker': {'menu': 'Style → Background'},
    'plugins': {'menu': 'Setup → Plugins'},
    'capture_menu': {'shortcut': 'Super + Ctrl + C'},
}

ALIASES = {
    'browser': ('browser', 'web browser'),
    'terminal': ('terminal',),
    'files': ('files', 'file manager'),
    'keybindings': ('keyboard shortcuts', 'keybindings', 'hotkeys'),
    'settings_audio': ('audio settings', 'sound settings'),
    'settings_bluetooth': ('bluetooth settings',),
    'settings_network': ('wifi settings', 'wi-fi settings', 'network settings'),
    'settings_display': ('display settings', 'monitor settings'),
    'capture_menu': ('screenshot controls', 'screen capture controls'),
}


def _routes(data):
    if not isinstance(data, dict) or data.get('ok') is not True or not isinstance(data.get('commands'), list):
        return {}
    if len(data['commands']) > MAX_COMMANDS:
        return {}
    result = {}
    for row in data['commands']:
        if not isinstance(row, dict) or row.get('hidden') is True or row.get('requires_sudo') is True:
            continue
        route, summary = row.get('route'), row.get('summary')
        if (isinstance(route, str) and re.fullmatch(r'omarchy(?: [a-zA-Z0-9_-]+){1,6}', route)
                and isinstance(summary, str) and 1 <= len(summary) <= 200
                and not any(ord(char) < 32 for char in summary)):
            result[route] = summary
    return result


def installed_routes():
    global _cache, _checked_at
    now = time.monotonic()
    if _cache is not None and now - _checked_at < MAX_AGE:
        return _cache
    routes = {}
    try:
        result = subprocess.run(['omarchy', 'commands', '--json'], capture_output=True,
                                timeout=3, check=True)
        if len(result.stdout) <= MAX_OUTPUT:
            routes = _routes(json.loads(result.stdout))
    except (OSError, ValueError, subprocess.SubprocessError):
        pass
    _cache, _checked_at = routes, now
    return routes


def details(action, routes=None):
    """Return display-only fields for a reviewed Wisp action ID."""
    path = PATHS.get(action)
    if path is None:
        return {}
    routes = installed_routes() if routes is None else routes
    result = {}
    if path.get('shortcut'):
        result['nativeShortcut'] = path['shortcut']
    if path.get('menu'):
        result['nativeMenu'] = path['menu']
    if path.get('route') in routes:
        result['nativeRoute'] = path['route']
        result['nativeSummary'] = routes[path['route']]
    return result


def reply(message, routes=None):
    """Answer a few complete informational questions about native controls."""
    if not isinstance(message, str) or len(message) > 200 or re.search(r'[\n\r;`"\'“”‘’<>|\\]', message):
        return None
    text = re.sub(r'\s+', ' ', message.casefold()).strip(' .!?')
    match = re.fullmatch(r'how (?:do|can) i (?:open|find|see|show|reach|bring up) (?:the |my )?(.+?) (?:in|on) omarchy', text)
    if match is None:
        return None
    target = match.group(1)
    action = next((key for key, aliases in ALIASES.items() if target in aliases), None)
    if action is None:
        return None
    info = details(action, routes)
    if not info:
        return None
    parts = []
    if info.get('nativeMenu'):
        parts.append('Omarchy menu: ' + info['nativeMenu'] + '.')
    if info.get('nativeShortcut'):
        parts.append('Default shortcut: ' + info['nativeShortcut'] + '. Check Super + K for your current bindings.')
    if info.get('nativeRoute'):
        parts.append('Installed command: ' + info['nativeRoute'] + '.')
    parts.append('Wisp can also prepare this control from Commands for your review.')
    return {'text': ' '.join(parts), 'emote': 'reading', 'action': '', 'route': 'local',
            'helpTopic': 'omarchy.native.' + action,
            'resources': [{'label': 'Omarchy hotkeys', 'url': 'https://omarchy.org/manual/hotkeys/',
                           'kind': 'official'}]}
