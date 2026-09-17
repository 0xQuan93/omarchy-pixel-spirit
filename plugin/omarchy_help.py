"""Small, offline Omarchy guide with reviewed links and installed references.

This is a topic router, not an interpreter: complete informational requests match
curated answers; action requests, quoted text and unfamiliar questions fall through.
Official chapters checked against omarchy.org/manual on 2026-09-16. Nothing here
fetches a page, reads user configuration contents, or executes a command.
"""
import os
from pathlib import Path
import re
import unicodedata


MANUAL = 'https://omarchy.org/manual/'
CHAPTERS = {
    'overview': ('Omarchy manual', ''),
    'start': ('Learning the desktop', 'navigation/'),
    'docs': ('Omarchy manual', ''),
    'keys': ('Keyboard shortcuts', 'hotkeys/'),
    'themes': ('Themes guide', 'themes/'),
    'plugins': ('Shell plugins guide', 'shell-plugins/'),
    'commands': ('Omarchy CLI guide', 'omarchy-cli/'),
    'config': ('Configuration guide', 'dotfiles/'),
}

# Full matches keep a supported topic embedded in prose or a compound command
# from swallowing the rest of the user's request.
PATTERNS = {
    'overview': (
        r'(?:about |what (?:exactly )?is |tell me (?:more )?about |explain |describe |introduce me to |help me understand )?(?:the )?omarchy(?: ecosystem)?',
        r'(?:give me |show me )?(?:an? )?(?:overview|introduction)(?: of| to)? omarchy',
        r'what (?:can you tell me|should i know) about omarchy',
        r'(?:give me |show me )?(?:some )?information (?:about|on) omarchy',
        r'omarchy (?:overview|introduction)',
    ),
    'start': (
        r'(?:help me |i want to |i would like to )?(?:learn(?: about)?|understand|use) omarchy',
        r'(?:teach me|show me around|help me with) omarchy',
        r'(?:i am |im )?(?:new to|a beginner (?:at|with)) omarchy',
        r'i am (?:confused by|lost in|getting used to) omarchy',
        r'get me started (?:with|on|in) omarchy',
        r'(?:getting|how (?:do|can) i get) started (?:with|on|in) omarchy',
        r'(?:where (?:do|can|should) i start|how (?:do|can) i get started) (?:with|on|in) omarchy',
        r'how (?:do i use|does) omarchy(?: work)?',
        r'omarchy (?:basics|for beginners|tutorial|getting started|help)',
        r'(?:help|a tutorial|a beginner guide|the basics) (?:with|for|of|on) omarchy',
    ),
    'themes': (
        r'how (?:do|can|should) i (?:change|switch|pick|choose|select|customize) (?:my |the |a |an? )?(?:theme|themes|appearance|background|wallpaper) (?:in|on|for) omarchy',
        r'how (?:do|can|should) i (?:change|switch|pick|choose|select|customize) (?:my |the )?omarchy (?:theme|themes|appearance|background|wallpaper)',
    ),
    'plugins': (
        r'how (?:do|can|should) i (?:find|use|manage|install|add|remove|make|create) (?:a |the |my )?(?:shell )?plugins? (?:in|on|for) omarchy',
        r'how (?:do|can|should) i (?:find|use|manage|install|add|remove|make|create) (?:an? |the |my )?omarchy (?:shell )?plugins?',
    ),
    'keys': (
        r'how (?:do|can) i (?:navigate|move around|use the keyboard in) omarchy',
        r'what (?:is|does) (?:the )?super key(?: mean)? (?:in|on) omarchy',
    ),
    'config': (
        r'where (?:is|are|can i find) (?:my |the )?omarchy (?:config|configuration|settings|dotfiles)(?: files)?',
        r'how (?:do|can) i (?:configure|customize) omarchy',
    ),
    'commands': (
        r'how (?:do|can) i (?:find|list|see|learn|use) (?:the |all (?:the )?)?omarchy commands',
        r'how (?:do|can) i use (?:the )?omarchy (?:cli|command line)',
    ),
}
NOUNS = {
    'docs': r'(?:docs|documentation|manual|guide|resources|local resources|local docs|offline help|offline docs)',
    'keys': r'(?:hotkeys|shortcuts|keyboard shortcuts|keybindings|key bindings|navigation|keyboard controls)',
    'themes': r'(?:themes|theme|backgrounds|wallpapers|appearance)',
    'plugins': r'(?:plugins|shell plugins|plugin system|plugin marketplace)',
    'commands': r'(?:commands|command line|cli|terminal commands)',
    'config': r'(?:config|configuration|settings|dotfiles|config files|configuration files)',
}


def _topic(message):
    if not isinstance(message, str) or len(message) > 300:
        return None
    text = unicodedata.normalize('NFKC', message).casefold().strip()
    # Expand only ordinary contractions; never erase quotation delimiters.
    for contraction, expanded in (("what's", 'what is'), ("i'm", 'i am'),
                                  ("i'd", 'i would'), ("where's", 'where is')):
        text = text.replace(contraction, expanded).replace(contraction.replace("'", '’'), expanded)
    if re.search(r'[\n\r;`"\'“”‘’<>|\\]', text):
        return None
    text = re.sub(r'\s+', ' ', text).strip(' .!?')
    text = re.sub(r'^(?:(?:hey|hi|hello) )?(?:wisp|zephyr)[, ]+', '', text)
    text = re.sub(r'^(?:please|pls|plz|kindly)[, ]+', '', text)
    text = re.sub(r'^(?:can|could|would|will) you (?:please )?', '', text)
    text = re.sub(r'[, ]+(?:please|pls|plz|thanks|thank you)$', '', text)
    for topic, patterns in PATTERNS.items():
        if any(re.fullmatch(pattern, text) for pattern in patterns):
            return topic
    for topic, noun in NOUNS.items():
        subject = rf'(?:(?:the )?omarchy {noun}|(?:the )?{noun} (?:for|in|on|about) omarchy)'
        if re.fullmatch(rf'(?:{subject}|(?:tell me about|explain|help me understand|show me|find|find me|where (?:is|are|can i find)|what (?:is|are)) {subject})(?: (?:help|guide|docs))?', text):
            return topic
    return None


def _roots():
    # Omarchy's own config discovery uses ~/.config regardless of XDG_CONFIG_HOME.
    config = Path.home() / '.config'
    data = Path(os.environ.get('XDG_DATA_HOME') or Path.home() / '.local/share')
    candidates = [Path('/usr/share/omarchy'), data / 'omarchy']
    if os.environ.get('OMARCHY_PATH'):
        candidates.insert(0, Path(os.environ['OMARCHY_PATH']))
    system = next((path for path in candidates
                   if (path / 'default').is_dir() or (path / 'shell').is_dir()), candidates[0])
    return system, config


def _local(label, root, relative):
    """Link only named, existing regular files inside their expected root."""
    path = root / relative
    try:
        resolved = path.resolve(strict=True)
        if not resolved.is_relative_to(root.resolve()) or not resolved.is_file():
            return None
        if any(ord(char) < 32 for char in str(resolved)):
            return None
        return {'label': label, 'url': path.absolute().as_uri(), 'kind': 'local'}
    except (OSError, RuntimeError, ValueError):
        return None


def reply(message):
    """Return a curated local answer, or None when the request is not covered."""
    topic = _topic(message)
    if topic is None:
        return None
    system, config = _roots()
    legacy = ((system / 'default/hypr/bindings/utilities.conf').is_file()
              and not (system / 'default/hypr/bindings/utilities.lua').is_file())
    modern = not legacy
    menu_key = 'Super + Space' if modern else 'Super + Alt + Space'
    basics = (f'Default keys: {menu_key} opens the Omarchy menu; '
              'Super + K shows shortcuts; Super + Return opens a terminal. '
              'Super is usually the Windows key. Your own bindings can override these.')
    answers = {
        'overview': ('Omarchy is an Arch Linux desktop built around Hyprland: windows tile automatically, '
                     'themes coordinate the desktop, and the Omarchy menu brings apps and settings together. '
                     + basics + '\nAsk me about Omarchy shortcuts, themes, plugins, or commands.'),
        'start': ('Start with the Omarchy menu, then learn one shortcut at a time. ' + basics +
                  '\nTry opening a terminal and browser to see tiling. Wisp’s Commands view shows '
                  'what I can control locally; the guide below teaches the desktop itself.'),
        'docs': ('Here are Omarchy’s official manual and any matching references installed on this computer. '
                 'The local files work offline; the manual link needs a browser connection. '
                 'For built-in terminal help, use omarchy commands or omarchy --help.'),
        'keys': (basics + '\nOther defaults: Super + Arrow changes focus; Super + 1–9 switches workspaces; '
                 'Super + Shift + Return opens the browser. Use the shortcuts view to see your current bindings.'),
        'themes': (f'Open the Omarchy menu with {menu_key}, then Style → Theme. '
                   'The default direct shortcut is Super + Ctrl + Shift + Space. '
                   'Super + Ctrl + Space chooses a background. '
                   'For terminal instructions, omarchy theme --help lists the installed theme controls. '
                   'Tell me “change the theme” when you want the picker.'),
        'plugins': ('Plugins add panels, widgets and services to the Omarchy shell; Wisp is one. '
                    'Use the Omarchy menu’s Setup → Plugins to manage them. '
                    'The read-only omarchy plugin list command shows installed plugins, '
                    'and omarchy plugin --help explains the controls. '
                    'The local references below describe the shell and plugin format.'),
        'commands': ('Omarchy’s terminal help is built in: omarchy commands lists the installed commands, '
                     'omarchy --help shows groups, and omarchy theme --help explains one group. '
                     'These help commands do not change your desktop. '
                     'Wisp’s Commands view lists the actions I can handle locally.'),
        'config': ('Omarchy keeps personal configuration in your user config directory; packaged defaults '
                   'are separate. The existing files linked below are local references. '
                   'For a guided starting point, use Setup → Config in the Omarchy menu. '
                   'The official guide explains which setting belongs where.'),
    }
    candidates = {
        'shell': ('Installed shell guide', system, 'shell/README.md'),
        'plugins': ('Installed plugin guide', system, 'shell/plugins/README.md'),
        'keys': ('Installed default shortcuts', system,
                 'default/hypr/bindings/utilities.lua' if modern else 'default/hypr/bindings/utilities.conf'),
        'bindings': ('Your shortcut configuration', config,
                     'hypr/bindings.lua' if (config / 'hypr/bindings.lua').is_file() else 'hypr/bindings.conf'),
        'config': ('Your shell configuration', config, 'omarchy/shell.json'),
        'colors': ('Active theme colors', config, 'omarchy/current/theme/colors.toml'),
    }
    references = {
        'overview': ('keys', 'shell'), 'start': ('keys', 'bindings'),
        'docs': ('shell', 'plugins', 'keys'), 'keys': ('keys', 'bindings'),
        'themes': ('keys', 'colors'), 'plugins': ('shell', 'plugins'),
        'commands': ('shell',), 'config': ('bindings', 'config'),
    }
    resources = [resource for key in references[topic]
                 if (resource := _local(*candidates[key])) is not None]
    label, chapter = CHAPTERS[topic]
    resources.append({'label': label, 'url': MANUAL + chapter, 'kind': 'official'})
    if topic == 'plugins':
        resources.append({'label': 'Omarchy plugin directory', 'url': 'https://plugins.omarchy.org/', 'kind': 'official'})
    # URLs also remain visible for consumers that have no resource-card support.
    text = answers[topic] + '\n\n' + '\n'.join(
        resource['label'] + ': ' + resource['url'] for resource in resources)
    return {'text': text, 'emote': 'happy', 'action': '', 'route': 'local',
            'helpTopic': 'omarchy.' + topic, 'resources': resources}
