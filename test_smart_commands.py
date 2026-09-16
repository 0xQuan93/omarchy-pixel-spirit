"""Pure phrase-routing regression checks; never execute desktop actions."""
import unittest
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent / 'plugin'))

from smart_commands import LOOKUP, PHRASES, match, normalize


class SmartCommandTests(unittest.TestCase):
    def test_every_phrase_and_collision(self):
        seen = {}
        for action, phrases in PHRASES.items():
            for phrase in phrases:
                with self.subTest(action=action, phrase=phrase):
                    key = normalize(phrase)
                    self.assertTrue(key)
                    self.assertEqual(seen.setdefault(key, action), action)
                    self.assertEqual(match(phrase), action)
                    self.assertEqual(LOOKUP[key], action)

    def test_every_phrase_stays_bounded(self):
        for action, phrases in PHRASES.items():
            for phrase in phrases:
                for message in ("don't " + phrase, 'how do i ' + phrase,
                                'explain ' + phrase, phrase + ' tomorrow',
                                '"' + phrase + '"', phrase + ' and open terminal'):
                    with self.subTest(message=message):
                        self.assertEqual(match(message), '')

    def test_politeness(self):
        for message in (
            'Change the theme', 'Hey Wisp, could you please change the theme for me?',
            'Wisp, change the theme!', 'please, change the theme please',
            'I would like you to change the theme now.',
            'Would you mind changing the theme?', 'Do you mind changing the theme?',
            'ＣＨＡＮＧＥ　ＴＨＥ　ＴＨＥＭＥ',
        ):
            with self.subTest(message=message):
                self.assertEqual(match(message), 'theme_picker')

    def test_representative_actions(self):
        cases = {
            'open a terminal': 'terminal', 'show my files': 'files',
            'open my browser': 'browser', 'open obsidian': 'notes',
            'pause this song': 'pause_music', 'resume playback': 'play_music',
            'skip this track': 'next_track', 'go back one track': 'previous_track',
            'make it louder': 'volume_up', 'turn the volume down': 'volume_down',
            'mute': 'mute', 'unmute the sound': 'unmute',
            'dim my screen': 'brightness_down', 'brighten the display': 'brightness_up',
            'next workspace': 'workspace_next', 'previous desktop': 'workspace_previous',
            'pause notifications': 'dnd_on', 'resume notifications': 'dnd_off',
            'save battery': 'power_saver', 'disable battery saver': 'power_balanced',
            'show my reminders': 'reminders', 'open bluetooth settings': 'settings_bluetooth',
            'show keyboard shortcuts': 'keybindings',
            'change my wallpaper': 'background_picker', 'next wallpaper': 'background_next',
            'open clipboard history': 'clipboard', 'toggle night light': 'nightlight_toggle',
        }
        for message, action in cases.items():
            with self.subTest(message=message):
                self.assertEqual(match(message), action)

    def test_unsupported_meaning_does_not_disappear(self):
        messages = (
            'do not change the theme', 'never change the theme',
            'can you explain how to change the theme', 'why did you change the theme',
            'i just tried to change the theme', 'i might change the theme',
            'if i change the theme', 'change the theme if possible',
            'change the theme to catppuccin', 'change the theme tomorrow',
            'change the theme and open files', 'open files then change the theme',
            'please say change the theme', 'what does change the theme mean',
            '“change the theme”', '‘change the theme’', '`change the theme`',
            "'change the theme'", 'change the theme; open terminal',
            'change the theme\nopen terminal', 'change\rthe theme',
            'turn on night light', 'turn off night light',
            'set brightness to 50%', 'turn up the volume by 20%',
            'open browser https://example.com', 'open terminal && echo hello',
            'next theme', 'delete my files', '', None, 42, ['open files'],
            'please ' * 40 + 'open files',
        )
        for message in messages:
            with self.subTest(message=message):
                self.assertEqual(match(message), '')

    def test_action_filter(self):
        self.assertEqual(match('change the theme', {'theme_picker'}), 'theme_picker')
        self.assertEqual(match('change the theme', {'browser'}), '')
        self.assertEqual(match('open browser', {}), '')
        self.assertEqual(match('open browser', {'browser': ['fixed', 'argv']}), 'browser')


if __name__ == '__main__':
    unittest.main()
