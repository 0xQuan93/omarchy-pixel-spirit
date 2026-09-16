"""Nuance routes stay local, are available, and remain review-only."""
import sys
from pathlib import Path
import unittest
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).parent / 'plugin'))
import brain

class IntentIntegrationTests(unittest.TestCase):
    def setUp(self):
        local_bank=patch.object(brain.command_routes,'proposal',return_value=None)
        local_bank.start();self.addCleanup(local_bank.stop)

    def test_composed_and_clarification_do_not_call_model_or_execute(self):
        cases = {'just open my clipboard':'clipboard',
                 'turn my speaker volume down one step':'volume_down',
                 'close it':'', 'turn it off':''}
        for phrase, action in cases.items():
            with self.subTest(phrase=phrase), patch.object(brain, 'read', return_value=[]), \
                 patch.object(brain.shutil, 'which', return_value='/test/tool'), \
                 patch.object(brain, 'execute') as execute, \
                 patch('inference.request', side_effect=AssertionError('Model must not run')) as model:
                self.assertFalse(brain.direct_action(phrase))
                reply=brain.chat(phrase)
                self.assertEqual(reply['route'],'local')
                self.assertEqual(reply['action'],action)
                self.assertEqual(reply['matchType'],'composed' if action else 'clarify')
                if action:self.assertIn('Run',reply['text'])
                else:self.assertTrue(reply['choices']);self.assertLessEqual(len(reply['choices']),4)
                execute.assert_not_called();model.assert_not_called()

    def test_compound_plan_never_executes_or_calls_model(self):
        import tempfile
        with tempfile.TemporaryDirectory() as d, patch.object(brain,'BASE',Path(d)), \
             patch.object(brain.shutil,'which',return_value='/test/tool'), \
             patch.object(brain,'execute') as execute, \
             patch('inference.request',side_effect=AssertionError('model')) as model:
            reply=brain.chat('open browser and terminal')
            self.assertEqual(reply['route'],'local')
            self.assertEqual([s['action'] for s in reply['steps']],['browser','terminal'])
            self.assertTrue(reply['action'].startswith('plan:'))
            execute.assert_not_called();model.assert_not_called()

    def test_unavailable_composed_command_is_local_failure(self):
        with patch.object(brain.shutil,'which',return_value=None):
            result=brain.local_intent('just open my clipboard')
            self.assertEqual(result['action'],'')
            self.assertEqual(result['route'],'local')
            self.assertIn('unavailable',result['text'])
            result=brain.local_intent('close it')
            self.assertFalse(result['choices'])

if __name__=='__main__':unittest.main()
