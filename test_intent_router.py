"""Local composition only returns reviewable fixed catalogue proposals."""
from pathlib import Path
import sys
import unittest
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).parent / 'plugin'))
import intent_router as router
from capabilities import ACTIONS, LABELS
from smart_commands import normalize


class IntentRouterTests(unittest.TestCase):
    def resolve(self, message, extra=None, actions=None, labels=None):
        return router.resolve(message, ACTIONS if actions is None else actions,
                              LABELS if labels is None else labels, normalize, extra)

    def test_explicit_targets_and_bounded_small_changes(self):
        cases = {
            'could you just launch my browser': 'browser',
            'let me open the terminal': 'terminal',
            'bring the Bluetooth settings up': 'settings_bluetooth',
            'pull my audio settings up': 'settings_audio',
            'bring the volume up': 'volume_up',
            'turn the night light back on': 'nightlight_on',
            'just show me the clipboard history': 'clipboard',
            'help me configure my audio controls': 'settings_audio',
            'i want to pull up my file manager': 'files',
            'put my music on pause': 'pause_music',
            'just unpause the media playback': 'play_music',
            'bring my speaker volume down a notch': 'volume_down',
            'bump my volume up by one step': 'volume_up',
            'lower the screen brightness slightly': 'brightness_down',
            'increase the display brightness a little': 'brightness_up',
            'just silence my microphone': 'mic_mute',
            'switch the night light on': 'nightlight_on',
            'just enable do not disturb': 'dnd_on',
            'put away my top bar': 'bar_hide',
            'close the current window': 'window_close',
        }
        for message, action in cases.items():
            with self.subTest(message=message):
                result = self.resolve(message)
                self.assertEqual(result['action'], action)
                self.assertEqual(result['actionLabel'], LABELS[action])
                self.assertEqual(result['route'], 'local')
                self.assertEqual(result['matchType'], 'composed')
                self.assertEqual(result['choices'], [])
                self.assertIn('Run', result['text'])

    def test_extra_player_and_controls_keep_explicit_semantics(self):
        actions = ACTIONS | {a: ['fixed'] for a in ('cartoons_close', 'cartoons_pause', 'cartoons_hide')}
        labels = LABELS | {'cartoons_close': 'Close cartoons', 'cartoons_pause': 'Pause cartoons', 'cartoons_hide': 'Hide cartoon controls'}
        extra = [{'label': 'Cartoon player', 'aliases': ['cartoon player', 'cartoons'],
                  'verbs': {'close': 'cartoons_close', 'pause': 'cartoons_pause'}},
                 {'label': 'Cartoon controls', 'aliases': ['cartoon controls', 'toonami'],
                  'verbs': {'hide': 'cartoons_hide'}, 'hide_without_stopping': True}]
        for message, action in (
            ('could you shut the cartoon player down', 'cartoons_close'),
            ('just pause cartoons', 'cartoons_pause'),
            ('hide toonami without stopping playback', 'cartoons_hide'),
            ('close the cartoon controls but keep the video playing', 'cartoons_hide'),
        ):
            self.assertEqual(self.resolve(message, extra, actions, labels)['action'], action)
        result = self.resolve('close cartoons without stopping playback', extra, actions, labels)
        self.assertEqual(result['action'], '')
        self.assertEqual(result['choices'], [])

    def test_missing_object_and_known_unsupported_operation_clarify(self):
        for message in ('close it', 'turn it off', 'hide that', 'open this one'):
            with self.subTest(message=message):
                result = self.resolve(message)
                self.assertEqual(result['action'], '')
                self.assertEqual(result['matchType'], 'clarify')
                self.assertEqual(result['reason'], 'target-needed')
                self.assertLessEqual(len(result['choices']), 4)
                self.assertTrue(all(c['action'] in ACTIONS for c in result['choices']))
        result = self.resolve('stop the browser')
        self.assertEqual(result['action'], '')
        self.assertEqual(result['reason'], 'operation-unavailable')

    def test_private_close_ids_and_narrow_apostrophes(self):
        private = ACTIONS | {'close_browser': ['fixed'], 'wanderer': ['fixed']}
        labels = LABELS | {'close_browser': 'Close browser', 'wanderer': 'Open Wanderer'}
        self.assertEqual(self.resolve('just close my browser', actions=private, labels=labels)['action'], 'close_browser')
        result = self.resolve('just close my browser')
        self.assertEqual(result['action'], '')
        extras = [{'label': 'Wanderer', 'aliases': ["wanderer's desk"], 'verbs': {'open': 'wanderer'}}]
        self.assertEqual(self.resolve('just open Wanderer’s Desk', extras, private, labels)['action'], 'wanderer')

    def test_alias_collisions_never_replace_fixed_actions(self):
        extras = [{'label': 'Other browser', 'aliases': ['browser'], 'verbs': {'open': 'files'}}]
        result = self.resolve('just open browser', extras)
        self.assertEqual(result['action'], '')
        self.assertEqual(result['reason'], 'ambiguous-target')
        self.assertEqual({c['action'] for c in result['choices']}, {'browser', 'files'})
        same = [{'label': 'Browser', 'aliases': ['browser'], 'verbs': {'open': 'browser'}}]
        self.assertEqual(self.resolve('just open browser', same)['action'], 'browser')

    def test_grammar_ambiguity_is_not_resolved_by_pattern_order(self):
        extras = [{'label': 'Mixer', 'aliases': ['mixer'],
                   'verbs': {'open': 'settings_audio', 'increase': 'volume_up'}}]
        result = self.resolve('bring the mixer up', extras)
        self.assertEqual(result['action'], '')
        self.assertEqual(result['reason'], 'ambiguous-target')
        self.assertEqual({c['action'] for c in result['choices']}, {'settings_audio', 'volume_up'})

    def test_unknown_extra_ids_and_invalid_aliases_are_ignored(self):
        extras = [{'label': 'Unknown', 'aliases': ['unknown'], 'verbs': {'open': 'rm -rf /'}},
                  {'label': 'Injected', 'aliases': ['browser and reboot', 'not browser'], 'verbs': {'open': 'files'}},
                  None, {'label': 'Broken', 'aliases': 'browser', 'verbs': ['open']}]
        self.assertIsNone(self.resolve('open unknown', extras))
        self.assertIsNone(self.resolve('open browser and reboot', extras))
        self.assertIsNone(self.resolve('open not browser', extras))

    def test_modifiers_negation_and_ambiguous_input_are_never_dropped(self):
        messages = (
            'do not open browser', "don't open browser", 'never open browser',
            'please do not open browser', 'just do not open browser',
            'open browser if possible', 'open browser when i get back',
            'open browser without opening a new window', 'open browser and terminal',
            'open browser then open terminal', 'open browser or terminal',
            'open browser tomorrow', 'open browser for ten minutes',
            'turn volume down by 20 percent', 'turn volume down twice',
            'lower spotify volume', 'pause music on my phone',
            'turn volume down to 50%', 'open browser https://example.com',
            'show me why i should open browser', 'explain open browser',
            '"open browser"', '“open browser”', '`open browser`',
            'open browser\nopen files', 'open browser; open files',
            None, 12, '', 'just ' * 100 + 'open browser',
        )
        for message in messages:
            with self.subTest(message=message):
                self.assertIsNone(self.resolve(message))

    def test_parser_has_no_execution_or_model_effects(self):
        with patch('subprocess.run', side_effect=AssertionError('execution')), \
             patch('inference.request', side_effect=AssertionError('inference')):
            self.assertEqual(self.resolve('just launch browser')['action'], 'browser')


if __name__ == '__main__':
    unittest.main()
