"""Pending-plan edits preserve review tokens without model or desktop effects."""
from contextlib import ExitStack
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).parent / 'plugin'))
import brain
import command_plans
from storage import get


class PlanEditIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.stack = ExitStack()
        self.addCleanup(self.stack.close)
        root = Path(self.stack.enter_context(tempfile.TemporaryDirectory()))
        self.base = root / 'state'
        config, system = root / 'config', root / 'system'
        config.mkdir()
        system.mkdir()
        self.stack.enter_context(patch.object(brain, 'BASE', self.base))
        self.stack.enter_context(patch('command_bank.defaults', return_value=(config, system, self.base)))
        self.stack.enter_context(patch('shutil.which', return_value='/test/fixed-tool'))
        self.guards = [self.stack.enter_context(patch(target, side_effect=AssertionError(target)))
                       for target in ('inference.request', 'brain.execute', 'subprocess.run')]

    def tearDown(self):
        for guard in self.guards:
            guard.assert_not_called()

    def prepare(self):
        reply = brain.chat('open browser and terminal', eco=False)
        self.assertEqual(self.ids(reply), ['browser', 'terminal'])
        self.assertTrue(reply['action'].startswith('plan:'))
        self.assertEqual(reply['route'], 'local')
        return reply['action']

    @staticmethod
    def ids(reply):
        return [step['action'] for step in reply['steps']]

    def assert_pending(self, token, ids):
        registry = brain.plan_context()[2]
        self.assertEqual(command_plans.pending(self.base, token, registry), ids)

    def assert_invalid(self, token):
        with self.assertRaises(ValueError):
            command_plans.pending(self.base, token, brain.plan_context()[2])

    def test_skip_browser_issues_fresh_review_and_invalidates_old_token(self):
        old = self.prepare()
        reply = brain.chat('skip browser', eco=False, pending_plan=old)
        self.assertEqual(self.ids(reply), ['terminal'])
        self.assertNotEqual(reply['action'], old)
        self.assert_pending(reply['action'], ['terminal'])
        self.assert_invalid(old)

    def test_only_percentage_replaces_entire_plan(self):
        old = self.prepare()
        reply = brain.chat('only set volume to 50 percent', eco=False, pending_plan=old)
        self.assertEqual(self.ids(reply), ['param:volume:50'])
        self.assertNotEqual(reply['action'], old)
        self.assert_pending(reply['action'], ['param:volume:50'])
        self.assert_invalid(old)

    def test_invalid_edit_preserves_existing_token_and_persisted_plan(self):
        token = self.prepare()
        before = get(self.base / 'command-plan.json', {})
        reply = brain.chat('replace first with frobnicate clouds', eco=False, pending_plan=token)
        self.assertEqual(reply['action'], token)
        self.assertEqual(self.ids(reply), ['browser', 'terminal'])
        self.assertIn('unchanged', reply['text'])
        self.assertEqual(get(self.base / 'command-plan.json', {}), before)
        self.assert_pending(token, ['browser', 'terminal'])

    def test_removing_every_step_invalidates_plan(self):
        old = self.prepare()
        one = brain.chat('remove first', pending_plan=old)
        empty = brain.chat('remove first', pending_plan=one['action'])
        self.assertEqual(empty['action'], '')
        self.assertEqual(empty['steps'], [])
        self.assertEqual(empty['reason'], 'empty-plan')
        self.assert_invalid(old)
        self.assert_invalid(one['action'])
        self.assertEqual(get(self.base / 'command-plan.json', {}), {})

    def test_direct_edit_api_appends_and_rejects_same_source_conflict(self):
        old = self.prepare()
        actions, labels, registry = brain.plan_context()
        def resolve(text):
            return brain.smart_match(text) or brain.parameter_commands.proposal(text)
        reply = command_plans.edit('also set volume to 20 percent', old, self.base,
                                   actions, labels, resolve, registry)
        self.assertEqual(self.ids(reply), ['browser', 'terminal', 'param:volume:20'])
        current = reply['action']
        conflict = command_plans.edit('also set volume to 80 percent', current, self.base,
                                      actions, labels, resolve, registry)
        self.assertEqual(conflict['action'], current)
        self.assertEqual(self.ids(conflict), self.ids(reply))
        self.assert_pending(current, self.ids(reply))
        self.assert_invalid(old)


if __name__ == '__main__':
    unittest.main()
