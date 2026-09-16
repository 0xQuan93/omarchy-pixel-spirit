"""Small, authored command tips using only an already-permitted app category.

This module does not collect context, decide when to interrupt, execute actions,
write state, or call a model. The caller owns awareness/quiet/privacy gates and
stores returned action IDs in its bounded recent history.
"""
import shutil

from capabilities import ACTIONS, LABELS
from smart_commands import match

RECENT_LIMIT = 12
CATEGORIES = frozenset({'Maker', 'Artist', 'Musician', 'Archivist'})

# Each family has one fixed action and an exact, tested example. Categories are
# broad app metadata, never a claim about the person's task, intent or feelings.
HINTS = (
    ('terminal', ('Maker',), 'open a terminal',
     'A terminal is one request away. Try “open a terminal” whenever you need one.'),
    ('keybindings', ('Maker',), 'show keyboard shortcuts',
     'Learning the desktop keys? “Show keyboard shortcuts” opens the shortcut reference.'),
    ('clipboard', ('Maker', 'Archivist'), 'open clipboard history',
     'Need something you copied earlier? “Open clipboard history” brings up the clipboard picker.'),
    ('workspace_next', ('Maker', 'Archivist'), 'next workspace',
     'Workspaces give windows separate places. Try “next workspace” to switch to the next one.'),
    ('default_editor', ('Maker',), 'change my default editor',
     'You can choose your preferred editor through the desktop. Try “change my default editor”.'),
    ('window_focus_left', ('Maker',), 'focus the window on the left',
     'Window navigation works in words, too. Try “focus the window on the left”.'),
    ('capture_menu', ('Artist',), 'open screenshot menu',
     'The capture menu offers screenshot choices. Try “open screenshot menu” to browse them.'),
    ('settings_display', ('Artist',), 'open display settings',
     'Display controls have their own panel. Try “open display settings” when you want to review them.'),
    ('background_picker', ('Artist',), 'change my wallpaper',
     'A different background is easy to browse. Try “change my wallpaper” to open the chooser.'),
    ('font_picker', ('Artist', 'Archivist'), 'show the font picker',
     'Curious about desktop fonts? “Show the font picker” opens the available choices.'),
    ('recording_menu', ('Artist',), 'open recording options',
     'Screen recording starts with its own options menu. Try “open recording options” to see the choices.'),
    ('settings_audio', ('Musician',), 'open audio settings',
     'Audio devices and volume controls live together. Try “open audio settings” to inspect them.'),
    ('mic_mute', ('Musician',), 'mute my microphone',
     'Microphone mute is separate from speaker mute. “Mute my microphone” prepares the microphone control.'),
    ('pause_music', ('Musician',), 'pause playback',
     'For a controllable media player, “pause playback” prepares a pause request without closing the player.'),
    ('previous_track', ('Musician',), 'previous track',
     'Media controls include a way back. Try “previous track” with a controllable player.'),
    ('volume_down', ('Musician',), 'lower the volume',
     'Small volume changes work without a model. Try “lower the volume” for a single step down.'),
    ('files', ('Archivist',), 'open my files',
     'The file manager is always a useful starting point. Try “open my files”.'),
    ('reminders', ('Archivist',), 'show my reminders',
     'Timers and reminders have a shared panel. Try “show my reminders” to open it.'),
    ('capture_text', ('Archivist',), 'extract screen text',
     'The desktop can capture text from a selected area. Try “extract screen text” to open that tool.'),
    ('emoji', ('Archivist',), 'open emoji picker',
     'There is an emoji picker built into the desktop. Try “open emoji picker” to browse it.'),
    ('theme_picker', (), 'change the theme',
     'You can browse a different desktop look without a model. Try “change the theme” to open the chooser.'),
    ('learn_menu', (), 'open omarchy help',
     'New to Omarchy? “Open Omarchy help” brings up its learning resources.'),
    ('plugins', (), 'open the plugin manager',
     'Desktop extras live in the plugin manager. Try “open the plugin manager” to review your options.'),
    ('settings_network', (), 'open wifi settings',
     'Network choices have a dedicated panel. Try “open wifi settings” when you want to inspect available connections.'),
    ('settings_bluetooth', (), 'open bluetooth settings',
     'Bluetooth devices have their own controls. Try “open Bluetooth settings” to view the panel.'),
    ('default_apps', (), 'open default apps',
     'You can choose which apps the desktop prefers. Try “open default apps” to see the options.'),
    ('launcher', (), 'open the app launcher',
     'Looking for an application? “Open the app launcher” brings up the desktop launcher.'),
    ('settings', (), 'open system settings',
     'Desktop configuration starts in one menu. Try “open system settings” to explore the available controls.'),
    ('about', (), 'show system information',
     'The desktop has a system information screen. Try “show system information” to open it.'),
    ('bar_settings', (), 'open bar settings',
     'The desktop bar has its own settings. Try “open bar settings” to see what you can change.'),
    ('power_menu', (), 'open power options',
     'Power choices stay in the desktop menu. “Open power options” shows the choices without selecting one.'),
    ('brightness_down', (), 'dim the screen',
     'Brightness can change one step at a time. Try “dim the screen” to prepare a small decrease.'),
    ('nightlight_on', (), 'turn on night light',
     'Night light has an explicit on command. “Turn on night light” prepares that setting rather than toggling it.'),
    ('dnd_on', (), 'enable do not disturb',
     'Notification quiet time is available on request. Try “enable do not disturb” when you want it.'),
)


def choose(snapshot, recent=None):
    """Choose one available, unrepeated tip without observing anything new.

    ``recent`` can contain action-ID strings or saved reflection dictionaries
    with an ``action`` field. Only its last twelve entries participate. Unknown
    categories receive general beginner tips; app names and titles are ignored.
    A returned action is proposal metadata, never authorization to execute it.
    """
    if not isinstance(snapshot, dict):
        return None
    category = snapshot.get('category')
    category = category if isinstance(category, str) and category in CATEGORIES else ''
    history = recent[-RECENT_LIMIT:] if isinstance(recent, (list, tuple)) else ()
    excluded = set()
    for item in history:
        action = item.get('action') if isinstance(item, dict) else item
        if isinstance(action, str):
            excluded.add(action)
    # Keep contextual examples first, then a stable beginner sequence. These
    # lists contain authored categories; no user-provided string enters prose.
    candidates = [hint for hint in HINTS if category and category in hint[1]]
    candidates += [hint for hint in HINTS if not hint[1]]
    # Continue after the latest eligible family so a fixed twelve-item history
    # does not permanently starve families later in the beginner sequence.
    positions = {hint[0]: index for index, hint in enumerate(candidates)}
    for item in reversed(history):
        last = item.get('action') if isinstance(item, dict) else item
        if isinstance(last, str) and last in positions:
            start = positions[last] + 1
            candidates = candidates[start:] + candidates[:start]
            break
    for action, categories, example, text in candidates:
        if action in excluded or action not in ACTIONS or action not in LABELS:
            continue
        # Catalogue membership is checked above; the one-argument matcher API
        # also supports personal overlays without changing routing priority.
        if match(example) != action or not shutil.which(ACTIONS[action][0]):
            continue
        return {'text': text, 'basis': category if categories else 'Omarchy command tip',
                'kind': 'command-hint', 'action': action,
                'actionLabel': LABELS[action], 'example': example}
    return None
