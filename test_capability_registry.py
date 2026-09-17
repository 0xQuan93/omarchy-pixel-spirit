from pathlib import Path
import sys
import unittest
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).parent / 'plugin'))
from capability_registry import Registry


class CapabilityRegistryTests(unittest.TestCase):
    def setUp(self):
        self.actions = {'open': ['tool', 'open'], 'mute': ['tool', 'mute'],
                        'open_muted': ['tool', 'open-muted'], 'browser': ['browser']}
        self.labels = {'open': 'Open player', 'mute': 'Mute player',
                       'open_muted': 'Open muted', 'browser': 'Open browser'}
        self.metadata = {action: {'sourceId': 'player', 'sourceLabel': 'Player',
                                 'operation': action, 'planSafe': True,
                                 'verification': 'accepted'}
                         for action in ('open', 'mute', 'open_muted')}
        self.metadata['browser'] = {'sourceId': 'browser', 'planSafe': True}

    def registry(self, **kwargs):
        return Registry(self.actions, self.labels, self.metadata, **kwargs)

    def test_describe_defaults_and_missing_tool(self):
        registry = Registry(self.actions, self.labels)
        with patch('capability_registry.shutil.which', return_value=None) as which:
            result = registry.describe('open')
            which.assert_called_once_with('tool')
        self.assertEqual(result['sourceId'], 'desktop')
        self.assertEqual(result['sourceLabel'], 'Desktop')
        self.assertEqual(result['operation'], 'open')
        self.assertFalse(result['planSafe'])
        self.assertFalse(result['available'])
        self.assertTrue(result['availabilityReason'])
        self.assertEqual(result['requires'], 'tool')
        self.assertEqual(result['verification'], 'process')
        self.assertEqual(registry.plan_allowed(), frozenset())

    def test_availability_is_dynamic_and_fails_closed(self):
        for value, expected in ((True, True), (False, False),
                                ({'available': False, 'reason': 'Plugin disabled'}, False),
                                ({'available': True, 'reason': ''}, True),
                                ({'available': 'yes'}, False), ({}, False), (1, False),
                                ({'available': True, 'reason': []}, False)):
            with self.subTest(value=value):
                registry = self.registry(availability=lambda action: value)
                self.assertIs(registry.describe('open')['available'], expected)
        def broken(action):
            raise RuntimeError('private detail must not escape')
        result = self.registry(availability=broken).describe('open')
        self.assertFalse(result['available'])
        self.assertNotIn('private detail', result['availabilityReason'])

    def test_strict_metadata_and_fixed_action_validation(self):
        for data in ({'missing': {}}, {'open': {'argv': ['bad']}},
                     {'open': {'module': 'untrusted'}}, {'open': {'planSafe': 1}},
                     {'open': {'verification': []}}, {'open': {'verification': 'guessed'}},
                     {'open': {'sourceId': '../external'}}, {'open': {'sourceLabel': ''}},
                     {'open': {'operation': 'run arbitrary code'}}, {'open': []}):
            with self.subTest(data=data), self.assertRaises(ValueError):
                Registry(self.actions, self.labels, data)
        for action_map in ({'open': []}, {'open': ['tool', None]}, {'open': ['tool\x00bad']}):
            with self.assertRaises(ValueError):
                Registry(action_map, self.labels)
        with self.assertRaises(ValueError):
            Registry(self.actions, {})

    def test_fingerprint_and_metadata_are_defensive_stable_snapshots(self):
        registry = self.registry()
        original = registry.fingerprint('open')
        self.assertEqual(len(original), 64)
        reversed_metadata = {key: dict(reversed(tuple(value.items()))) for key, value in self.metadata.items()}
        same = Registry(dict(reversed(tuple(self.actions.items()))), self.labels, reversed_metadata)
        self.assertEqual(same.fingerprint('open'), original)
        self.actions['open'].append('changed')
        self.metadata['open']['planSafe'] = False
        registry.describe('open')['planSafe'] = False
        self.assertEqual(registry.fingerprint('open'), original)
        changed = self.registry()
        self.assertNotEqual(changed.fingerprint('open'), original)
        for unknown in ('unknown', None, []):
            with self.subTest(unknown=unknown), self.assertRaises(ValueError):
                registry.fingerprint(unknown)

    def test_adjacent_source_combinations_preserve_order(self):
        registry = self.registry(combinations=[('open', 'mute', 'open_muted')])
        self.assertEqual(registry.rewrite_plan(('browser', 'open', 'mute')), ('browser', 'open_muted'))
        self.assertEqual(registry.rewrite_plan(('open', 'browser', 'mute')), ('open', 'browser', 'mute'))
        self.assertEqual(registry.rewrite_plan(('mute', 'browser', 'open')), ('mute', 'browser', 'open'))
        self.assertEqual(registry.rewrite_plan(('mute', 'open')), ('mute', 'open'))
        self.assertIsNone(registry.rewrite_plan(('unknown',)))
        self.assertIsNone(registry.rewrite_plan(('open',) * 5))
        self.assertIsNone(Registry(self.actions, self.labels).rewrite_plan(('open',)))

    def test_combinations_require_known_safe_same_source_actions(self):
        for rules in ([('open', 'mute', 'missing')], [('open', 'browser', 'open_muted')],
                      [('open', 'mute')], [('open', 'mute', 'open_muted'), ('open', 'mute', 'open')]):
            with self.subTest(rules=rules), self.assertRaises(ValueError):
                self.registry(combinations=rules)
        with self.assertRaises(ValueError):
            Registry(self.actions, self.labels, combinations=[('open', 'mute', 'open_muted')])
        # Fold once over original adjacent pairs; replacements do not cascade.
        metadata = dict(self.metadata, browser={'sourceId': 'player', 'planSafe': True})
        registry = Registry(self.actions, self.labels, metadata,
                            combinations=[('open', 'mute', 'open_muted'), ('open_muted', 'browser', 'open')])
        self.assertEqual(registry.rewrite_plan(('open', 'mute', 'browser')), ('open_muted', 'browser'))

    def test_semantic_conflicts_use_concrete_source_and_operations(self):
        actions = {name: ['fixed', name] for name in ('set_a', 'set_b', 'on', 'off', 'mute', 'unmute', 'pause', 'resume')}
        labels = {name: name for name in actions}
        operations = {'set_a': 'set', 'set_b': 'set', 'on': 'enable', 'off': 'disable',
                      'mute': 'mute', 'unmute': 'unmute', 'pause': 'pause', 'resume': 'resume'}
        metadata = {name: {'sourceId': 'media', 'operation': op, 'planSafe': True} for name, op in operations.items()}
        registry = Registry(actions, labels, metadata)
        for ids in (('set_a', 'set_b'), ('on', 'off'), ('mute', 'unmute'), ('pause', 'resume')):
            self.assertTrue(registry.conflicts(ids))
            self.assertIsNone(registry.rewrite_plan(ids))
        self.assertFalse(registry.conflicts(('on', 'mute')))
        metadata['unmute']['sourceId'] = 'other-media'
        separate = Registry(actions, labels, metadata)
        self.assertFalse(separate.conflicts(('mute', 'unmute')))
        generic = Registry(actions, labels, {a: {'operation': operations[a], 'planSafe': True} for a in actions})
        self.assertFalse(generic.conflicts(('set_a', 'set_b')))
        self.assertFalse(generic.conflicts(('mute', 'unmute')))
        self.assertTrue(generic.conflicts(('mute', 'mute')))
        self.assertTrue(generic.conflicts(('unknown',)))

    def test_semantic_conflicts_cannot_be_hidden_or_created_by_recipes(self):
        actions = {name: ['fixed', name] for name in ('start', 'quiet', 'loud', 'start_quiet', 'set_a')}
        labels = {name: name for name in actions}
        operations = {'start': 'open', 'quiet': 'mute', 'loud': 'unmute', 'start_quiet': 'set', 'set_a': 'set'}
        metadata = {name: {'sourceId': 'player', 'operation': op, 'planSafe': True} for name, op in operations.items()}
        registry = Registry(actions, labels, metadata, combinations=[('start', 'quiet', 'start_quiet')])
        self.assertIsNone(registry.rewrite_plan(('start', 'quiet', 'loud')))
        self.assertIsNone(registry.rewrite_plan(('start', 'quiet', 'set_a')))
        self.assertEqual(registry.rewrite_plan(('start', 'quiet')), ('start_quiet',))

    def test_intent_targets_filter_unavailable_verbs_without_alias_override(self):
        target = {'label': "Player's controls", 'aliases': ["player's controls", 'player'],
                  'verbs': {'open': 'open', 'mute': 'mute', 'close': 'unknown'},
                  'hide_without_stopping': True}
        registry = self.registry(targets=[target])
        result = registry.intent_targets()
        self.assertEqual(result[0]['verbs'], {'open': 'open', 'mute': 'mute'})
        result[0]['verbs']['open'] = 'browser'
        target['aliases'].append('changed')
        self.assertEqual(registry.intent_targets()[0]['aliases'], ["player's controls", 'player'])
        self.assertEqual(registry.intent_targets()[0]['verbs']['open'], 'open')
        for bad in ({'label': 'bad', 'aliases': ['player'], 'verbs': {}, 'argv': ['bad']},
                    {'label': 'bad', 'aliases': ['player; run'], 'verbs': {'open': 'open'}},
                    {'label': 'bad', 'aliases': ['player'], 'verbs': {}, 'hide_without_stopping': 1}):
            with self.assertRaises(ValueError):
                self.registry(targets=[bad])

    def test_verification_preserves_evidence_level_and_payload_text(self):
        registry = self.registry()
        accepted = registry.receipt('open', {'text': 'Request acknowledged.', 'action': '', 'ok': True, 'status': 'completed'})
        self.assertEqual(accepted['status'], 'accepted')
        self.assertEqual(accepted['text'], 'Request acknowledged.')
        self.assertEqual(accepted['sourceId'], 'player')
        self.assertEqual(accepted['route'], 'local')
        completed = registry.receipt('browser', {'text': 'Process exited.', 'action': ''})
        self.assertEqual(completed['status'], 'completed')
        self.assertEqual(completed['verification'], 'process')
        state = Registry(self.actions, self.labels, {'open': {'verification': 'state'}})
        for verified in (None, False, 1, 'true'):
            self.assertFalse(state.receipt('open', {'text': 'Reported.', 'action': '', 'verified': verified})['ok'])
        receipt = state.receipt('open', {'text': 'State confirmed.', 'action': '', 'verified': True})
        self.assertTrue(receipt['ok'])
        self.assertEqual(receipt['status'], 'verified')

    def test_malformed_or_failed_receipts_cannot_report_success(self):
        registry = self.registry()
        for data in ({}, None, [], {'text': ''}, {'text': ' '},
                     {'text': 'Done', 'action': 'mute'}, {'text': 'Done'},
                     {'text': 'Done', 'action': '', 'error': 'failed'},
                     {'text': 'Done', 'action': '', 'errors': ['failed']},
                     {'text': 'Done', 'action': '', 'ok': False},
                     {'text': 'Done', 'action': '', 'ok': 'yes'},
                     {'text': 'Cancelled', 'action': '', 'status': 'cancelled', 'ok': True}):
            with self.subTest(data=data):
                result = registry.receipt('open', data)
                self.assertFalse(result['ok'])
                self.assertEqual(result['status'], 'failed')
                self.assertEqual(result['action'], '')
        cancelled = registry.receipt('open', {'text': 'Selection cancelled.', 'action': '', 'ok': False, 'status': 'cancelled'})
        self.assertEqual(cancelled['status'], 'cancelled')
        self.assertFalse(cancelled['ok'])

    def test_registry_has_no_execution_or_model_effects(self):
        with patch('subprocess.run', side_effect=AssertionError('execution')), \
             patch('inference.request', side_effect=AssertionError('model')), \
             patch('capability_registry.shutil.which', return_value='/usr/bin/tool'):
            registry = self.registry(combinations=[('open', 'mute', 'open_muted')])
            self.assertTrue(registry.describe('open')['available'])
            self.assertEqual(registry.rewrite_plan(('open', 'mute')), ('open_muted',))
            self.assertTrue(registry.receipt('open', {'text': 'Accepted.', 'action': ''})['ok'])


if __name__ == '__main__':
    unittest.main()
