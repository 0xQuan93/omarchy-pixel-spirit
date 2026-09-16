"""Independent adversarial corpus for whole-request intent composition."""
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).parent / 'plugin'))
import intent_router as router
from smart_commands import normalize


class IntentAdversarialTests(unittest.TestCase):
    def setUp(self):
        self.actions = {key: ['fixed-tool', key] for key in (
            'settings', 'settings_audio', 'settings_bluetooth', 'volume_down',
            'mic_mute', 'dnd_on', 'window_close', 'bar_hide',
            'cartoons_on', 'cartoons_off', 'cartoons_hide', 'cartoons_pause')}
        self.labels = {key: key.replace('_', ' ').title() for key in self.actions}
        self.cartoon = {'label': 'Cartoon player', 'aliases': ['cartoons', 'toonami'],
                        'verbs': {'open': 'cartoons_on', 'stop': 'cartoons_off',
                                  'close': 'cartoons_off', 'hide': 'cartoons_hide',
                                  'pause': 'cartoons_pause'}, 'hide_without_stopping': True}

    def resolve(self, text, extra=None):
        return router.resolve(text, self.actions, self.labels, normalize,
                              extra_targets=[self.cartoon] if extra is None else extra)

    def test_compositions_are_proposals_with_fixed_actions(self):
        for text, action in (
            ('help me open the bluetooth controls', 'settings_bluetooth'),
            ('bring my speaker volume down one step', 'volume_down'),
            ('put the cartoons on pause', 'cartoons_pause'),
            ('hide the cartoons without stopping playback', 'cartoons_hide'),
            ('enable do not disturb', 'dnd_on'),
        ):
            with self.subTest(text=text):
                result = self.resolve(text)
                self.assertIsNotNone(result)
                self.assertEqual(result['action'], action)
                self.assertEqual(result['matchType'], 'composed')
                self.assertIn('Run', result['text'])
                self.assertEqual(result['route'], 'local')

    def test_source_amount_time_and_scope_modifiers_are_never_discarded(self):
        for text in (
            'lower only the browser volume', 'lower the volume in firefox',
            'lower speaker volume by twenty percent', 'turn speaker volume down to 20 percent',
            'turn speaker volume down twice', 'mute the microphone for ten minutes',
            'close cartoons after this episode', 'stop cartoons in ten minutes',
            'close every window except toonami', 'open settings and reboot',
            'open settings then restart bluetooth', 'open settings but keep it hidden',
            'hide cartoons without stopping my recording',
            'hide cartoons without stopping playback tomorrow',
            'hide cartoons without stopping playback and close the window',
        ):
            with self.subTest(text=text):
                self.assertIsNone(self.resolve(text))

    def test_negation_quotation_questions_and_complaints_do_not_become_commands(self):
        for text in (
            'do not close cartoons', "don't close cartoons", 'never close cartoons',
            'can you not close cartoons', 'please do not mute my microphone',
            'if i ask you to stop cartoons', 'why did you stop cartoons',
            'i did not ask you to stop cartoons', 'i cannot open settings',
            'the cartoons are too loud', 'my bluetooth will not connect',
            'explain close the cartoons', 'say "close cartoons"',
            '“close cartoons”', "'close cartoons'", '`close cartoons`',
            'open settings; reboot', 'open settings\nreboot',
            'please\rclose cartoons', 'open settings: reboot',
        ):
            with self.subTest(text=text):
                self.assertIsNone(self.resolve(text))

    def test_pronouns_require_clarification_and_never_bind_the_current_window(self):
        for text in ('close it', 'close that', 'stop them', 'hide this one'):
            with self.subTest(text=text):
                result = self.resolve(text)
                self.assertIsNotNone(result)
                self.assertEqual(result['matchType'], 'clarify')
                self.assertEqual(result['action'], '')
                self.assertLessEqual(len(result['choices']), 4)

    def test_alias_collision_is_not_resolved_by_order(self):
        collision = {'label': 'Alternate settings', 'aliases': ['settings'],
                     'verbs': {'open': 'settings_audio'}}
        result = self.resolve('open settings', [collision])
        self.assertEqual(result['matchType'], 'clarify')
        self.assertEqual(result['action'], '')
        self.assertEqual({c['action'] for c in result['choices']}, {'settings', 'settings_audio'})
        for extras in ([self.cartoon, collision], [collision, self.cartoon]):
            self.assertEqual(self.resolve('open settings', extras)['choices'], result['choices'])

    def test_unknown_or_malformed_extra_actions_cannot_enter_results(self):
        records = [
            {'label': 'Ghost', 'aliases': ['ghost'], 'verbs': {'open': 'unregistered'}},
            {'label': 'Shell', 'aliases': ['shell'], 'verbs': {'execute': 'settings'}},
            {'label': 'Bad', 'aliases': ['settings; reboot'], 'verbs': {'open': 'settings'}},
            {'label': 'Bad\nlabel', 'aliases': ['bad'], 'verbs': {'open': 'settings'}},
        ]
        for text in ('open ghost', 'execute shell', 'open bad', 'open settings; reboot'):
            self.assertIsNone(self.resolve(text, records))

    def test_many_ambiguous_targets_are_bounded_to_four_choices(self):
        records = []
        for i in range(8):
            action = 'close_player_' + str(i)
            self.actions[action] = ['fixed-tool', action]
            self.labels[action] = 'Close player ' + str(i)
            records.append({'label': 'Player ' + str(i), 'aliases': ['player'],
                            'verbs': {'close': action}})
        for text in ('close player', 'close it'):
            result = self.resolve(text, records)
            self.assertEqual(result['action'], '')
            self.assertLessEqual(len(result['choices']), 4)
            self.assertEqual(len({c['action'] for c in result['choices']}), len(result['choices']))

    def test_explicit_keep_playing_constraint_filters_unsafe_alternatives(self):
        unpromised = dict(self.cartoon, hide_without_stopping=False)
        for text in ('hide cartoons without stopping playback', 'hide it without stopping playback'):
            result = self.resolve(text, [unpromised])
            if result is not None:
                self.assertEqual(result['action'], '')
                self.assertEqual(result['choices'], [])


if __name__ == '__main__':
    unittest.main()
