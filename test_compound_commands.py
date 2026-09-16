from pathlib import Path
import sys
import unittest
from unittest.mock import Mock, patch
sys.path.insert(0, str(Path(__file__).parent / 'plugin'))
import compound_commands as compounds
import intent_router
from capabilities import ACTIONS, LABELS
from smart_commands import match, normalize


class CompoundCommandTests(unittest.TestCase):
    def setUp(self):
        self.actions = ACTIONS | {key: ['fixed'] for key in ('cartoons_on', 'cartoons_mute', 'cartoons_unmute', 'cartoons_close', 'cartoons_on_muted')}
        self.labels = LABELS | {'cartoons_on': 'Open cartoons', 'cartoons_mute': 'Mute cartoons', 'cartoons_on_muted': 'Open cartoons muted', 'cartoons_unmute': 'Unmute cartoons', 'cartoons_close': 'Close cartoons'}
        self.extras = [{'label': 'Cartoons', 'aliases': ['cartoons', 'toonami'],
                        'verbs': {'open': 'cartoons_on', 'mute': 'cartoons_mute', 'unmute': 'cartoons_unmute', 'close': 'cartoons_close'}}]

    def resolve(self, text):
        action = match(text, self.actions)
        return action or intent_router.resolve(text, self.actions, self.labels, normalize, self.extras)

    def propose(self, text, rewrite=None, resolver=None):
        return compounds.propose(text, resolver or self.resolve, self.labels, self.actions, normalize, rewrite)

    def test_complete_clauses_and_inherited_target_lists(self):
        for text, expected in (
            ('open browser and terminal', ['browser', 'terminal']),
            ('open browser and open files', ['browser', 'files']),
            ('open browser then mute the sound', ['browser', 'mute']),
            ('please open browser and then open terminal', ['browser', 'terminal']),
            ('open browser, then open terminal', ['browser', 'terminal']),
            ('open browser and please open terminal', ['browser', 'terminal']),
            ('just open browser and files', ['browser', 'files']),
            ('open browser and files and terminal and notes', ['browser', 'files', 'terminal', 'notes']),
            ('enable do not disturb and open terminal', ['dnd_on', 'terminal']),
        ):
            with self.subTest(text=text):
                result = self.propose(text)
                self.assertEqual([s['action'] for s in result['steps']], expected)
                self.assertEqual(result['action'], '')
                self.assertEqual(result['route'], 'local')
                self.assertEqual(result['reason'], 'compound-plan')
                for step in result['steps']:
                    self.assertEqual(step['label'], self.labels[step['action']])

    def test_source_aware_rewrite_can_guarantee_silent_launch(self):
        def rewrite(actions):
            self.assertEqual(actions, ('browser', 'cartoons_on', 'cartoons_mute'))
            return ('browser', 'cartoons_on_muted')
        result = self.propose('open browser and cartoons but mute cartoons', rewrite)
        self.assertEqual([s['action'] for s in result['steps']], ['browser', 'cartoons_on_muted'])

    def test_noncompound_and_ordinary_conversation(self):
        for text in ('open browser', 'turn the music down a little',
                     'I like music and cartoons', 'what are themes and plugins',
                     'why do people open terminals and browsers',
                     'explain why \"open browser and terminal\" works',
                     'create a routine to open browser and terminal',
                     'what are cats and dogs', None, 42):
            with self.subTest(text=text):
                self.assertIsNone(self.propose(text))

    def test_nothing_partial_for_unresolved_or_unsafe_steps(self):
        cases = (
            'open browser and an unknown app', 'open browser and mute it',
            'open browser then turn that off',
            'open browser and close the browser',
            'do not open browser and terminal', "don't open browser and terminal",
            'open browser and do not mute the sound',
            'open browser and terminal tomorrow',
            'open browser and terminal if possible',
            'open browser and terminal after ten minutes',
            'open browser and turn volume down by 20%',
            'open browser and pause music on my phone',
            'open browser and open files or terminal',
            'open browser and terminal and files and notes and clipboard',
            'open browser and and open terminal', 'open browser but',
            'open browser but terminal', 'open browser then terminal',
            'open browser, terminal and files',
            '"open browser and terminal"', '“open browser and terminal”',
            'open browser; open terminal', 'open browser && open terminal',
            'open browser\nopen terminal', 'open browser | open terminal',
        )
        for text in cases:
            with self.subTest(text=text):
                result = self.propose(text)
                self.assertIsNotNone(result)
                self.assertEqual(result['steps'], [])
                self.assertEqual(result['action'], '')
                self.assertEqual(result['route'], 'local')

    def test_known_single_target_with_connector_is_not_split(self):
        def resolver(text):
            return 'settings_audio' if text == 'open sound and video' else 'browser'
        result = self.propose('open sound and video', resolver=resolver)
        self.assertEqual(result['steps'], [])
        self.assertEqual(result['reason'], 'ambiguous-compound')

    def test_duplicate_and_conflicting_states(self):
        for text in ('open browser and browser', 'mute sound then unmute sound',
                     'enable night light then disable night light',
                     'raise volume then lower volume',
                     'pause music and resume music'):
            with self.subTest(text=text):
                result = self.propose(text)
                self.assertEqual(result['steps'], [])
                self.assertIn(result['reason'], ('duplicate-step', 'conflicting-steps'))

    def test_rewrite_cannot_hide_original_conflicts(self):
        rewrite = Mock(return_value=('cartoons_on_muted',))
        for message in ('open cartoons and mute cartoons then unmute cartoons',
                        'open cartoons and close cartoons'):
            result = self.propose(message, rewrite)
            self.assertEqual(result['steps'], [])
            self.assertEqual(result['reason'], 'conflicting-steps')
        rewrite.assert_not_called()

    def test_single_semantic_hide_request_never_becomes_a_partial_plan(self):
        result = self.propose('hide cartoon controls but keep the video playing',
                              resolver=lambda text: 'cartoons_close')
        self.assertEqual(result['steps'], [])
        self.assertEqual(result['reason'], 'ambiguous-compound')

    def test_rewrites_and_callback_results_are_revalidated(self):
        for replacement in (None, [], ['browser'] * 5, 'browser', ['untrusted'], [42]):
            with self.subTest(replacement=replacement):
                result = self.propose('open browser and files', lambda actions: replacement)
                self.assertEqual(result['steps'], [])
        def resolver(text):
            if text == 'open browser and files':
                return None
            return {'action': 'browser', 'matchType': 'clarify'}
        self.assertEqual(self.propose('open browser and files', resolver=resolver)['steps'], [])
        broken = Mock(side_effect=ValueError('no result'))
        self.assertEqual(self.propose('open browser and files', resolver=broken)['steps'], [])

    def test_no_execution_storage_or_inference(self):
        with patch('subprocess.run', side_effect=AssertionError('executed')), \
             patch('inference.request', side_effect=AssertionError('model requested')):
            self.assertEqual(len(self.propose('open browser and files')['steps']), 2)


if __name__ == '__main__':
    unittest.main()
