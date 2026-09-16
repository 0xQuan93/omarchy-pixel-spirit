"""Everyday wording stays an explicit request for one implemented capability."""
from pathlib import Path
import sys
import unittest
sys.path.insert(0, str(Path(__file__).parent / 'plugin'))
from capabilities import ACTIONS
from smart_commands import EVERYDAY_PHRASES, match, normalize, _authored_key


class EverydayPhraseTests(unittest.TestCase):
    def test_reviewed_examples_match_the_fixed_catalogue(self):
        for action, phrases in EVERYDAY_PHRASES.items():
            self.assertIn(action, ACTIONS)
            for phrase in phrases:
                with self.subTest(phrase=phrase):
                    self.assertEqual(match(phrase, ACTIONS), action)
                    self.assertEqual(normalize(phrase), _authored_key(phrase))
                    self.assertEqual(match('Wisp, could you please ' + phrase + '?', ACTIONS), action)

    def test_every_example_preserves_negation_conditions_quotes_and_compounds(self):
        for phrases in EVERYDAY_PHRASES.values():
            for phrase in phrases:
                for message in (
                    'do not ' + phrase, "don't " + phrase, 'never ' + phrase,
                    'if possible ' + phrase, 'if i ask you to ' + phrase,
                    'explain how to ' + phrase, 'why would you ' + phrase,
                    '"' + phrase + '"', '“' + phrase + '”',
                    phrase + ' tomorrow', phrase + ' when i get back',
                    phrase + ' unless i change my mind',
                    phrase + ' and open terminal', phrase + '; open terminal',
                ):
                    with self.subTest(message=message):
                        self.assertEqual(match(message), '')

    def test_varied_english_and_voice_punctuation(self):
        cases = {
            'Let me customise the desktop.': 'appearance',
            'Let me customize the desktop!': 'appearance',
            'Change the colour theme': 'theme_picker',
            'Change the color theme': 'theme_picker',
            'Close the window I’m using.': 'window_close',
            'Pause what’s playing': 'pause_music',
            'Turn the music down a bit, please.': 'volume_down',
            'Give me a bit more volume': 'volume_up',
            'Restore normal idle behaviour': 'idle_allow',
            'Restore normal idle behavior': 'idle_allow',
        }
        for message, action in cases.items():
            with self.subTest(message=message):
                self.assertEqual(match(message), action)

    def test_statements_and_unsupported_controls_do_not_infer_intent(self):
        for message in (
            "i can't hear", 'the screen is too bright', 'the music is too loud',
            'i need a break', 'i am tired', 'my microphone is not working',
            'i cannot read this font', 'my internet is broken',
            'kill this app', 'force quit the current window',
            'make all my text larger', 'turn off the computer',
            'open a command prompt and delete my files',
            'toggle full screen if the app supports it',
            'switch my theme to an unknown theme',
        ):
            with self.subTest(message=message):
                self.assertEqual(match(message), '')


if __name__ == '__main__':
    unittest.main()
