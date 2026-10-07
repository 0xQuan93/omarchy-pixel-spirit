import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import sys
sys.path.insert(0, str(Path(__file__).parent / 'plugin'))

import interaction_policy as policy
import brain


class FakeRegistry:
    def __init__(self, *, available=True, connected=True):
        self.available = available
        self.connected = connected
        self.calls = []

    def describe(self, action):
        self.calls.append(action)
        return {'available': self.available,
                'availabilityReason': 'Unavailable',
                'readiness': {'connected': self.connected}}


class InteractionPolicyTests(unittest.TestCase):
    def test_default_requires_review_and_exact_whitelist(self):
        with tempfile.TemporaryDirectory() as directory:
            registry = FakeRegistry()
            self.assertFalse(policy.eligible(directory, 'lower the volume', 'volume_down', registry))
            self.assertEqual(registry.calls, [])
            policy.configure(directory, 'on')
            self.assertTrue(policy.eligible(directory, 'lower the volume', 'volume_down', registry))
            self.assertFalse(policy.eligible(directory, 'lower the volume and open files', 'volume_down', registry))
            self.assertFalse(policy.eligible(directory, 'close the window', 'window_close', registry))
            self.assertFalse(policy.eligible(directory, 'lower the volume', 'volume_up', registry))

    def test_connected_player_required_for_direct_playback(self):
        with tempfile.TemporaryDirectory() as directory:
            policy.configure(directory, 'on')
            self.assertFalse(policy.eligible(directory, 'pause music', 'pause_music', FakeRegistry(connected=None)))
            self.assertFalse(policy.eligible(directory, 'pause music', 'pause_music', FakeRegistry(connected=False)))
            with patch('readiness.check', return_value={'suggestable': False}):
                self.assertFalse(policy.eligible(directory, 'pause music', 'pause_music', FakeRegistry(connected=True)))
            with patch('readiness.check', return_value={'suggestable': True}):
                self.assertTrue(policy.eligible(directory, 'pause music', 'pause_music', FakeRegistry(connected=True)))
            self.assertFalse(policy.eligible(directory, 'lower the volume', 'volume_down', FakeRegistry(available=False)))

    def test_damaged_preference_never_enables_direct_action(self):
        with tempfile.TemporaryDirectory() as directory:
            (Path(directory) / 'interaction-settings.json').write_text('{"version":1,"fastActions":"yes"}')
            with self.assertRaises(ValueError):
                policy.eligible(directory, 'lower the volume', 'volume_down', FakeRegistry())
            self.assertTrue((Path(directory) / 'interaction-settings.json').exists())

    def test_chat_runs_only_after_opt_in_and_returns_the_real_receipt(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            registry = FakeRegistry()
            receipt = {'text': 'Command finished', 'status': 'completed', 'action': '',
                       'route': 'local', 'evidence': {'sourceId': 'desktop', 'status': 'completed'}}
            with patch.object(brain, 'BASE', base), patch.object(brain, 'controls', return_value=registry), \
                 patch.object(brain, 'execute', return_value=receipt) as execute:
                proposal = brain.chat('lower the volume', learn=False)
                self.assertEqual(proposal['action'], 'volume_down')
                execute.assert_not_called()
                policy.configure(base, 'on')
                result = brain.chat('lower the volume', learn=False)
                execute.assert_called_once_with('volume_down')
                self.assertEqual(result['status'], 'completed')
                self.assertEqual(result['evidence']['status'], 'completed')
                self.assertTrue(result['quickAction'])


if __name__ == '__main__':
    unittest.main()
