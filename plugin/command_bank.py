"""Metadata-only local discovery. Generated data never contains executable commands.

Only explicit panel/overlay/menu plugins are summonable: a bar-widget's click
handler may do something quite different from opening a panel. Personal aliases
live separately in personal-command-bank.json as a list of {phrase,kind,target}.
"""
import json
import os
from pathlib import Path
import re
import stat
import tempfile

LIMIT = 512
MAX_BYTES = 128 * 1024
ID = re.compile(r'[a-z0-9][a-z0-9_-]*(?:\.[a-z0-9][a-z0-9_-]*)+')
SLUG = re.compile(r'[a-z0-9][a-z0-9_-]{0,95}')
NAME = re.compile(r'[\w][\w .&+()·’\'-]{0,79}', re.UNICODE)
GENERATED = 'generated-command-bank.json'
PERSONAL = 'personal-command-bank.json'


def defaults():
    home = Path.home()
    # Omarchy itself uses ~/.config, regardless of XDG_CONFIG_HOME.
    config = home / '.config/omarchy'
    system = Path(os.environ.get('OMARCHY_PATH', '/usr/share/omarchy'))
    state = Path(os.environ.get('XDG_STATE_HOME', str(home / '.local/state'))) / 'pixel-spirit'
    return config, system, state


from smart_commands import normalize


def read_json(path, default):
    try:
        # Reject symlinks and special files (a FIFO must never block a scan).
        fd = os.open(path, os.O_RDONLY | os.O_NONBLOCK | os.O_NOFOLLOW)
        with os.fdopen(fd, 'rb') as stream:
            info = os.fstat(stream.fileno())
            if not stat.S_ISREG(info.st_mode) or info.st_size > MAX_BYTES:
                return default
            raw = stream.read(MAX_BYTES + 1)
        return json.loads(raw) if len(raw) <= MAX_BYTES else default
    except (OSError, ValueError, RecursionError):
        return default


def children(path):
    try:
        with os.scandir(path) as entries:
            result = []
            for entry in entries:
                if len(result) >= LIMIT:
                    break
                result.append(Path(entry.path))
        return sorted(result)
    except OSError:
        return []


def discover(config_dir=None, system_dir=None):
    config, system, _ = defaults()
    config, system = Path(config_dir or config), Path(system_dir or system)
    shell = read_json(config / 'shell.json', {})
    if not isinstance(shell, dict):
        shell = {}
    disabled = shell.get('disabledPlugins', [])
    disabled = set(x for x in disabled if isinstance(x, str)) if isinstance(disabled, list) else set()
    configured = set()
    entries = shell.get('plugins', [])
    bar = shell.get('bar', {})
    layout = bar.get('layout', {}) if isinstance(bar, dict) else {}
    if isinstance(layout, dict):
        entries = (entries if isinstance(entries, list) else []) + sum((v for v in layout.values() if isinstance(v, list)), [])
    if isinstance(entries, list):
        configured = {e['id'] for e in entries if isinstance(e, dict) and isinstance(e.get('id'), str)}
    paths = []
    for directory in children(system / 'shell/plugins'):
        paths.append((directory / 'manifest.json', True))
        for nested in children(directory):
            if len(paths) >= LIMIT:
                break
            paths.append((nested / 'manifest.json', True))
            if nested.name.endswith('.manifest.json'):
                paths.append((nested, True))
        if len(paths) >= LIMIT:
            break
    # Reserve a separate budget for personal plugins.
    paths = paths[:LIMIT // 2]
    for directory in children(config / 'plugins')[:LIMIT // 2]:
        paths.append((directory / 'manifest.json', False))
    plugins = {}
    for path, first_party in paths[:LIMIT]:
        data = read_json(path, {})
        if not isinstance(data, dict) or data.get('schemaVersion') != 1:
            continue
        ident, name = data.get('id'), data.get('name')
        if not isinstance(ident, str) or len(ident) > 120 or not ID.fullmatch(ident):
            continue
        if not first_party and ident.startswith('omarchy.'):
            continue  # Match the host's reserved first-party namespace.
        if not isinstance(name, str) or not NAME.fullmatch(name):
            continue
        kinds, points = data.get('kinds'), data.get('entryPoints')
        if not isinstance(kinds, list) or not isinstance(points, dict):
            continue
        capable = any(k in kinds and isinstance(points.get(k), str) and points[k]
                      for k in ('panel', 'overlay', 'menu'))
        # Entry points are inspected for path safety, never read or imported.
        if any(not isinstance(p, str) or not p or p.startswith('/') or '..' in Path(p).parts for p in points.values()):
            continue
        enabled = ident not in disabled and (first_party or ident in configured)
        plugins[ident] = {'target': ident, 'name': name, 'enabled': enabled, 'openable': bool(capable)}
    themes = {}
    for root in (system / 'themes', config / 'themes'):
        for path in children(root):
            if SLUG.fullmatch(path.name) and path.is_dir():
                themes[path.name] = path.name.replace('-', ' ').replace('_', ' ')
    targets = {}
    for ident, plugin in plugins.items():
        if plugin['enabled'] and plugin['openable']:
            targets[('plugin', ident)] = {'kind': 'plugin', 'target': ident, 'label': 'Open ' + plugin['name']}
    for slug, name in themes.items():
        targets[('theme', slug)] = {'kind': 'theme', 'target': slug, 'label': 'Switch theme to ' + name}
    return plugins, themes, targets


def scan(state_dir=None, config_dir=None, system_dir=None):
    state = Path(state_dir or defaults()[2])
    plugins, themes, targets = discover(config_dir, system_dir)
    aliases, ambiguous = {}, set()

    def add(phrase, descriptor):
        phrase = normalize(phrase)
        if not phrase or len(phrase) > 160 or phrase in ambiguous:
            return
        if phrase in aliases and aliases[phrase] != descriptor:
            aliases.pop(phrase)
            ambiguous.add(phrase)
        else:
            aliases[phrase] = descriptor

    for (kind, target), descriptor in targets.items():
        if kind == 'theme':
            for name in {themes[target], target}:
                for prefix in ('change theme to ', 'change the theme to ', 'change my theme to ', 'switch theme to ', 'switch the theme to ', 'switch my theme to ', 'set theme to ', 'set the theme to ', 'set my theme to ', 'use theme ', 'use the theme '):
                    add(prefix + name, descriptor)
                for template in ('apply the {} theme', 'apply {} theme', 'switch to the {} theme',
                                 'switch to {} theme', 'use {} as my theme', 'make {} my theme'):
                    add(template.format(name), descriptor)
        else:
            for name in {plugins[target]['name'].lower(), target}:
                for prefix in ('open ', 'show ', 'launch ', 'bring up ', 'pull up ',
                               'show me ', 'take me to ', 'let me see '):
                    add(prefix + name, descriptor)
                    add(prefix + name + ' plugin', descriptor)
                    add(prefix + 'the ' + name + ' plugin', descriptor)
    personal = read_json(state / PERSONAL, [])
    if isinstance(personal, list):
        for alias in personal[:LIMIT]:
            if not isinstance(alias, dict) or not isinstance(alias.get('phrase'), str):
                continue
            phrase = normalize(alias['phrase'])
            if re.search(r"^(?:do not|don't|dont|never|stop|if|unless|why|what|how|when)\b|\b(?:and|then) (?:open|show|launch|run|execute|delete|remove|reboot|shutdown|switch|change|set)\b", phrase):
                continue
            kind, target = alias.get('kind'), alias.get('target')
            if isinstance(kind, str) and isinstance(target, str) and (kind, target) in targets:
                # Cannot inject argv, labels, or shadow an existing different target.
                add(alias['phrase'], targets[(kind, target)])
    bank = {'version': 1, 'plugins': sorted(plugins.values(), key=lambda p: p['target']),
            'themes': sorted(themes), 'aliases': dict(sorted(aliases.items())), 'ambiguous': sorted(ambiguous)}
    raw = json.dumps(bank, ensure_ascii=False, indent=2) + '\n'
    try:
        state.mkdir(parents=True, exist_ok=True, mode=0o700)
        destination = state / GENERATED
        # Atomic replacement; no generated bank data is ever trusted as input.
        try:
            unchanged = destination.is_file() and not destination.is_symlink() and destination.stat().st_size == len(raw.encode('utf-8')) and destination.read_text() == raw
        except (OSError, UnicodeError):
            unchanged = False
        if not unchanged:
            fd, temporary = tempfile.mkstemp(prefix='.command-bank-', dir=state)
            try:
                with os.fdopen(fd, 'w') as stream:
                    stream.write(raw)
                    stream.flush()
                    os.fsync(stream.fileno())
                os.replace(temporary, destination)
            finally:
                if os.path.exists(temporary):
                    os.unlink(temporary)
    except OSError:
        # Discovery remains useful when a disk is full or state is read-only.
        bank['persistence_warning'] = 'Command bank could not be saved; using freshly discovered commands for this request.'
    return bank


def match(message, state_dir=None, config_dir=None, system_dir=None):
    return scan(state_dir, config_dir, system_dir)['aliases'].get(normalize(message))


def resolve(descriptor, state_dir=None, config_dir=None, system_dir=None):
    if not isinstance(descriptor, dict):
        raise ValueError('Invalid discovered command.')
    kind, target = descriptor.get('kind'), descriptor.get('target')
    if not isinstance(kind, str) or not isinstance(target, str):
        raise ValueError('Invalid discovered command.')
    targets = discover(config_dir, system_dir)[2]
    if (kind, target) not in targets:
        raise ValueError('That theme or enabled plugin is no longer available. Refresh the command bank.')
    if kind == 'theme':
        return ['omarchy', 'theme', 'set', target]
    return ['omarchy', 'shell', 'shell', 'summon', target, '{}']


if __name__ == '__main__':
    import sys
    if sys.argv[1:] not in ([], ['scan']):
        raise SystemExit('Usage: command_bank.py [scan]')
    result = scan()
    print(json.dumps({'plugins': len(result['plugins']), 'themes': len(result['themes']),
                      'phrases': len(result['aliases']), 'collisions': len(result['ambiguous']),
                      'persistence_warning': result.get('persistence_warning', '')}))
