"""The new UI routes keep their review and preference boundaries at IPC."""
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).parent / 'plugin'))

import brain
import command_plans
from capability_specs import build


class FeatureIpcTests(unittest.TestCase):
    def test_routine_ipc_prepares_a_new_plan_without_executing(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            actions = {'browser': ['omarchy', 'launch', 'browser'],
                       'terminal': ['omarchy', 'launch', 'terminal']}
            labels = {'browser': 'Open browser', 'terminal': 'Open terminal'}
            registry = build(actions, labels, availability=lambda _: True)
            original = command_plans.prepare_steps(['browser', 'terminal'], base,
                                                    actions, labels, registry)
            with patch.object(brain, 'BASE', base), \
                 patch.object(brain, 'plan_context', return_value=(actions, labels, registry)), \
                 patch.object(brain, 'execute') as execute:
                with patch.object(brain, 'read_request', return_value=['routines', 'save',
                                                                      original['action'], 'Morning desk']):
                    saved = brain.main()
                self.assertEqual(saved['routines'][0]['name'], 'Morning desk')
                with patch.object(brain, 'read_request', return_value=['routines', 'prepare',
                                                                      saved['savedId']]):
                    fresh = brain.main()
                self.assertNotEqual(fresh['action'], original['action'])
                self.assertEqual(len(fresh['steps']), 2)
                execute.assert_not_called()

    def test_interaction_and_tour_ipc_require_explicit_write_request(self):
        with tempfile.TemporaryDirectory() as directory, patch.object(brain, 'BASE', Path(directory)):
            with patch.object(brain, 'read_request', return_value=['interaction']):
                self.assertFalse(brain.main()['fastActions'])
            with patch.object(brain, 'read_request', return_value=['interaction', 'fast_actions', 'on']):
                self.assertTrue(brain.main()['fastActions'])
            with patch.object(brain, 'read_request', return_value=['tour']):
                self.assertTrue(brain.main()['unseen'])
            with patch.object(brain, 'read_request', return_value=['tour', 'seen']):
                self.assertFalse(brain.main()['unseen'])


if __name__ == '__main__':
    unittest.main()
