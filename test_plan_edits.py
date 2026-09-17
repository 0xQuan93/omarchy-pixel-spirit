from pathlib import Path
import sys
import unittest
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).parent / 'plugin'))
from capability_registry import Registry
from plan_edits import propose


class PlanEditTests(unittest.TestCase):
    def setUp(self):
        self.labels = {key: key.replace('_', ' ') for key in (
            'browser', 'terminal', 'files', 'notes', 'cartoons_on', 'cartoons_mute',
            'cartoons_unmute', 'cartoons_on_muted', 'cartoons_pause', 'window_close')}
        actions = {key: ['fixed', key] for key in self.labels}
        metadata = {key: {'sourceId': 'cartoons' if key.startswith('cartoons_') else key,
                          'planSafe': key != 'window_close'} for key in self.labels}
        self.registry = Registry(actions, self.labels, metadata,
                                 combinations=[('cartoons_on', 'cartoons_mute', 'cartoons_on_muted')],
                                 availability=lambda action: True)
        self.commands = {'open browser': 'browser', 'open terminal': 'terminal',
                         'open files': 'files', 'open notes': 'notes',
                         'open cartoons': 'cartoons_on', 'mute cartoons': 'cartoons_mute',
                         'unmute cartoons': 'cartoons_unmute', 'pause cartoons': 'cartoons_pause',
                         'close this window': 'window_close'}

    def resolve(self, text):
        return self.commands.get(text)

    def edit(self, text, ids=('browser', 'terminal')):
        return propose(text, ids, self.labels, self.resolve, self.registry)

    def actions(self, reply):
        self.assertTrue(reply['planEdit'])
        self.assertEqual(reply['action'], '')
        self.assertEqual(reply['route'], 'local')
        return [step['action'] for step in reply['steps']]

    def test_ordinal_removal(self):
        for text, expected in (('skip the first step', ['terminal']),
                               ('remove step 2', ['browser']),
                               ('skip second', ['browser']),
                               ('please remove step two', ['browser'])):
            with self.subTest(text=text):
                self.assertEqual(self.actions(self.edit(text)), expected)
        self.assertEqual(self.actions(self.edit('remove the fourth step', ('browser', 'terminal', 'files', 'notes'))), ['browser', 'terminal', 'files'])
        for text in ('skip step 3', 'remove step 5', 'skip it'):
            self.assertEqual(self.actions(self.edit(text)), [])
        empty = self.edit('skip the first step', ('browser',))
        self.assertEqual(empty['reason'], 'empty-plan')
        self.assertEqual(self.actions(empty), [])

    def test_target_removal_uses_only_existing_unique_actions_or_sources(self):
        self.assertEqual(self.actions(self.edit('remove browser')), ['terminal'])
        self.assertEqual(self.actions(self.edit('remove cartoons', ('browser', 'cartoons_pause'))), ['browser'])
        self.assertEqual(self.actions(self.edit('remove cartoons', ('cartoons_on', 'cartoons_pause'))), [])
        self.assertEqual(self.actions(self.edit('remove open cartoons', ('cartoons_on', 'cartoons_pause'))), ['cartoons_pause'])
        self.assertEqual(self.actions(self.edit('remove notes')), [])

    def test_only_add_replace_and_source_instead(self):
        for text, ids, expected in (
            ('only open files', ('browser', 'terminal'), ['files']),
            ('add open files', ('browser', 'terminal'), ['browser', 'terminal', 'files']),
            ('also open files', ('browser',), ['browser', 'files']),
            ('replace step 2 with open files', ('browser', 'terminal'), ['browser', 'files']),
            ('replace browser with open files', ('browser', 'terminal'), ['files', 'terminal']),
            ('mute cartoons instead', ('browser', 'cartoons_on'), ['browser', 'cartoons_mute']),
            ('pause cartoons instead', ('cartoons_on_muted',), ['cartoons_pause']),
        ):
            with self.subTest(text=text):
                self.assertEqual(self.actions(self.edit(text, ids)), expected)
        self.assertEqual(self.actions(self.edit('open notes instead')), [])
        self.assertEqual(self.actions(self.edit('pause cartoons instead', ('cartoons_on', 'cartoons_mute'))), [])

    def test_adjacent_recipes_preserve_other_steps(self):
        self.assertEqual(self.actions(self.edit('also mute cartoons', ('browser', 'cartoons_on'))), ['browser', 'cartoons_on_muted'])
        self.assertEqual(self.actions(self.edit('also mute cartoons', ('cartoons_on', 'browser'))), ['cartoons_on', 'browser', 'cartoons_mute'])
        self.assertEqual(self.actions(self.edit('also open cartoons', ('cartoons_mute', 'browser'))), ['cartoons_mute', 'browser', 'cartoons_on'])

    def test_conflicts_limits_unknown_and_unsupported_edits_fail_closed(self):
        for text, ids in (
            ('also unmute cartoons', ('cartoons_on', 'cartoons_mute')),
            ('also open browser', ('browser',)),
            ('also open notes', ('browser', 'terminal', 'files', 'cartoons_on')),
            ('only close this window', ('browser',)),
            ('replace first with unknown command', ('browser',)),
            ('add', ('browser',)),
            ('remove browser', ('unknown',)),
        ):
            with self.subTest(text=text):
                result = self.edit(text, ids)
                self.assertEqual(self.actions(result), [])
                self.assertNotEqual(result['reason'], 'plan-edited')

    def test_qualifiers_and_ambiguous_pronouns_never_disappear(self):
        for text in ('only open browser tomorrow', 'also open terminal if possible',
                     'replace first with open files and mute cartoons',
                     'only do not open browser', 'remove it',
                     'replace it with open files', 'only open browser; open files',
                     'only "open browser"', 'also pause cartoons on my phone'):
            with self.subTest(text=text):
                self.assertEqual(self.actions(self.edit(text)), [])
        for text in ('open files', 'hello', 'what can you do', None, 5):
            self.assertIsNone(self.edit(text))

    def test_registry_default_source_does_not_make_unrelated_targets_equivalent(self):
        registry = Registry({'browser': ['b'], 'terminal': ['t']}, self.labels,
                            {'browser': {'planSafe': True}, 'terminal': {'planSafe': True}},
                            availability=lambda action: True)
        result = propose('remove browser', ['terminal'], self.labels, self.resolve, registry)
        self.assertEqual(result['steps'], [])
        result = propose('open browser instead', ['terminal'], self.labels, self.resolve, registry)
        self.assertEqual(result['steps'], [])

    def test_no_execution_or_model_and_inputs_unchanged(self):
        original = ['browser', 'terminal']
        with patch('subprocess.run', side_effect=AssertionError('execution')), \
             patch('inference.request', side_effect=AssertionError('model')):
            self.assertEqual(self.actions(self.edit('replace first with open files', original)), ['files', 'terminal'])
        self.assertEqual(original, ['browser', 'terminal'])


if __name__ == '__main__':
    unittest.main()
