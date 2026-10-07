"""Adapter contract fixtures: namespaced sources, evidence and fail-closed receipts."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / 'plugin'))

import adapter_contract
from capability_registry import Registry


def fixture(source, action):
    return {'schemaVersion': 1, 'sourceId': source, 'sourceLabel': source,
            'controls': [{'id': action, 'label': 'Pause ' + source,
                          'argv': ['example-control', '--source', source, 'pause'],
                          'operation': 'pause', 'planSafe': False,
                          'verification': 'state'}]}


class AdapterContractTests(unittest.TestCase):
    def test_two_sources_remain_distinct_and_require_real_readback(self):
        first = adapter_contract.extension(fixture('example.radio', 'example_radio_pause'))
        second = adapter_contract.extension(fixture('other.player', 'other_player_pause'))
        actions = first[0] | second[0]
        labels = first[1] | second[1]
        metadata = first[2] | second[2]
        registry = Registry(actions, labels, metadata=metadata, availability=lambda _: True)
        self.assertNotEqual(registry.describe('example_radio_pause')['sourceId'],
                            registry.describe('other_player_pause')['sourceId'])
        failed = registry.receipt('example_radio_pause', {'text': 'Pause requested', 'action': ''})
        self.assertEqual(failed['status'], 'failed')
        verified = registry.receipt('example_radio_pause',
                                    {'text': 'Radio paused', 'action': '', 'verified': True})
        self.assertEqual(verified['status'], 'verified')

    def test_unknown_control_fields_and_duplicate_ids_fail(self):
        spec = fixture('example.radio', 'example_radio_pause')
        spec['controls'][0]['shell'] = 'arbitrary command'
        with self.assertRaisesRegex(ValueError, 'fields'):
            adapter_contract.extension(spec)
        spec = fixture('example.radio', 'example_radio_pause')
        spec['controls'].append(dict(spec['controls'][0]))
        with self.assertRaisesRegex(ValueError, 'control'):
            adapter_contract.extension(spec)
        spec = fixture('example.radio', 'example_radio_pause')
        spec['schemaVersion'] = True
        with self.assertRaisesRegex(ValueError, 'contract'):
            adapter_contract.extension(spec)

    def test_fact_evidence_has_source_expiry_and_honest_unknown(self):
        fact = {'schemaVersion': 1, 'sourceId': 'example.radio', 'sourceLabel': 'Example Radio',
                'observedAtMs': 1000, 'expiresAtMs': 5000, 'status': 'verified',
                'verification': 'state', 'unknownReason': '', 'value': {'playing': True}}
        evidence = adapter_contract.validate_fact(fact, 'example.radio', 'Example Radio', now_ms=2000)
        self.assertEqual(evidence['expiresAtMs'], 5000)
        self.assertNotIn('value', evidence)
        with self.assertRaisesRegex(ValueError, 'evidence'):
            adapter_contract.validate_fact(fact, 'other.player', now_ms=2000)
        unknown = dict(fact, status='unknown', value=None, unknownReason='Player is closed.')
        self.assertEqual(adapter_contract.validate_fact(unknown, now_ms=2000)['status'], 'unknown')
        with self.assertRaisesRegex(ValueError, 'evidence'):
            adapter_contract.validate_fact(dict(unknown, unknownReason=''), now_ms=2000)
        for invalid in (dict(fact, schemaVersion=True), dict(fact, sourceLabel='Other'),
                        dict(fact, expiresAtMs=1999), dict(fact, observedAtMs=5000),
                        dict(unknown, unknownReason='  ')):
            with self.subTest(invalid=invalid), self.assertRaises(ValueError):
                adapter_contract.validate_fact(invalid, 'example.radio', 'Example Radio', now_ms=2000)

    def test_fact_value_is_bounded_before_serialization(self):
        fact = {'schemaVersion': 1, 'sourceId': 'example.radio', 'sourceLabel': 'Example Radio',
                'observedAtMs': 1000, 'expiresAtMs': 5000, 'status': 'verified',
                'verification': 'state', 'unknownReason': '', 'value': {'playing': True}}
        for value in ([0] * 300, {'deep': {'deep': {'deep': {'deep': {'deep': {'deep':
                      {'deep': {'deep': {'deep': True}}}}}}}}}, {'unsafe\nkey': 1},
                      1 << 5000):
            with self.subTest(value=str(value)[:30]), self.assertRaises(ValueError):
                adapter_contract.validate_fact(dict(fact, value=value), now_ms=2000)


if __name__ == '__main__':
    unittest.main()
