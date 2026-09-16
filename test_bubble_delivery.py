import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch, MagicMock

sys.path.insert(0, str(Path(__file__).parent / 'plugin'))
import awareness
from storage import get, put


class DeliveryTests(unittest.TestCase):
    module = awareness

    def setUp(self):
        self.a = self.module
        temp = tempfile.TemporaryDirectory(); self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        for p in (patch.object(self.a, 'STATE', self.root),
                  patch.object(self.a.time, 'time', return_value=2000),
                  patch.object(self.a, 'gate', return_value='')):
            p.start(); self.addCleanup(p.stop)
        self.context = {'app': 'Code', 'category': 'Maker', 'workspace': 1}
        p = patch.object(self.a, 'snapshot', return_value=self.context)
        p.start(); self.addCleanup(p.stop)
        self.a.configure('enabled', 'on')
        self.settings = self.a.status()['settings']
        put(self.root / 'awareness.json', self.a.empty() | {
            'sampled': 1980, 'since': 1800, 'snapshot': self.context})
        self.hint = {'text': 'Try opening a terminal.', 'basis': 'Maker', 'kind': 'command-hint',
                     'action': 'terminal', 'actionLabel': 'Open terminal', 'example': 'open terminal'}
        self.life = MagicMock()
        self.life.eligible.return_value = True
        self.life.due_script.return_value = None
        self.life.commit.return_value = True
        p = patch.dict(sys.modules, {'local_life': self.life})
        p.start(); self.addCleanup(p.stop)

    def staged(self, **kwargs):
        return self.a.stage_reflection(self.hint, self.settings, self.context, **kwargs)['reflection']

    def test_generation_does_not_claim_display_and_receipt_is_single_use(self):
        r = self.staged()
        self.assertEqual(self.a.status()['reflections'], [])
        result = self.a.bubble_receipt(r['id'], 'displayed')
        self.assertTrue(result['accepted']); self.assertEqual(result['id'], r['id'])
        self.assertEqual(self.a.status()['last_delivered'], 2000)
        self.assertEqual(len(self.a.status()['reflections']), 1)
        self.assertFalse(self.a.bubble_receipt(r['id'], 'displayed')['accepted'])
        self.assertEqual(len(self.a.status()['reflections']), 1)

    def test_suppressed_expired_and_context_changed_do_not_charge_delivery(self):
        for kind in ('suppressed', 'expired', 'context'):
            r = self.staged()
            with patch.object(self.a.time, 'time', return_value=2200 if kind == 'expired' else 2000), patch.object(self.a, 'snapshot', return_value={} if kind == 'context' else self.context):
                self.assertFalse(self.a.bubble_receipt(r['id'], 'suppressed' if kind == 'suppressed' else 'displayed')['accepted'])
            self.assertEqual(self.a.status()['last_delivered'], 0)
            self.assertEqual(self.a.status()['reflections'], [])
        self.life.commit.assert_not_called()

    def test_revocation_clears_pending_and_never_commits_private_effects(self):
        r = self.staged(effects={'text':'test', 'topic':'reading'})
        self.a.configure('command_hints', 'off')
        self.assertIsNone(get(self.root / 'awareness.json', {})['pending'])
        self.assertFalse(self.a.bubble_receipt(r['id'], 'displayed')['accepted'])
        self.life.commit.assert_not_called()

    def test_hints_do_not_call_model_and_suppression_retries_after_short_backoff(self):
        with patch.object(self.a, 'hint_for', return_value=self.hint), patch('inference.request') as model:
            result = self.a.reflect()
            model.assert_not_called()
            self.assertEqual(result['reflection']['kind'], 'command-hint')
            self.a.bubble_receipt(result['reflection']['id'], 'suppressed')
            state = get(self.root / 'awareness.json', {})
            self.assertFalse(self.a.ready(state, 2119))
            self.assertTrue(self.a.ready(state, 2120))

    def test_delivered_cooldown_is_independent_of_attempt(self):
        state = self.a.empty() | {'last_attempt': 1800, 'last_delivered': 1900}
        self.assertFalse(self.a.ready(state, 2100))
        self.assertTrue(self.a.ready(state, 3100))

    def test_bubble_gate_does_not_require_input_optins_or_return_context(self):
        result = self.a.bubble_gate()
        self.assertTrue(result['allowed'])
        self.assertNotIn('snapshot', result)
        self.assertFalse(self.settings['activity_responses'])
        with patch.object(self.a, 'gate', return_value='Do Not Disturb'), patch.object(self.a, 'snapshot') as snap:
            self.assertFalse(self.a.bubble_gate()['allowed']); snap.assert_not_called()

    def test_omarchy_agent_is_work_context_but_shell_and_secrets_are_not(self):
        # Use the real snapshot function; setUp's patch is stopped locally.
        original = type(self).module.__dict__.get('snapshot')
        import importlib.util
        spec = importlib.util.spec_from_file_location('snapshot_check', Path(self.a.__file__))
        module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
        for app in ('org.omarchy.agent', 'omarchy-menu', 'org.omarchy.screensaver', 'Wisp', 'Bitwarden'):
            raw = {'class': app, 'workspace': {'id': 1}, 'fullscreen': 0}
            with patch.object(module, 'output', return_value=json.dumps(raw)):
                result = module.snapshot()
            if app == 'org.omarchy.agent':
                self.assertEqual(result['category'], 'Maker')
            else:
                self.assertIsNone(result)

    def test_model_failure_falls_back_without_recording_delivery(self):
        state = get(self.root / 'awareness.json', {})
        state['reflections'] = [dict(self.hint, at=500)]
        put(self.root / 'awareness.json', state)
        self.life.context.return_value = {}
        self.life.state.return_value = {'disabled': [], 'last_authored': 0}
        self.life.TOPICS = ['reading']
        with patch.object(self.a, 'hint_for', return_value=self.hint), patch('identity.profile', return_value={'name':'Test','model':'test'}), patch('inference.request', side_effect=RuntimeError('busy')):
            result = self.a.reflect()
        self.assertEqual(result['reflection']['kind'], 'command-hint')
        self.assertEqual(len(self.a.status()['reflections']), 1)
        self.assertEqual(self.a.status()['last_delivered'], 0)


if __name__ == '__main__':
    unittest.main()
