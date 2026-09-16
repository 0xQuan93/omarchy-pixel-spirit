"""Catalogue and chat integration never execute suggestion text."""
from contextlib import ExitStack
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).parent / 'plugin'))
import brain
import command_catalog
import parameter_commands
from smart_commands import PHRASES, match


class CommandCatalogueTests(unittest.TestCase):
    def test_all_builtin_entries_have_routable_examples(self):
        with patch.object(brain.shutil, 'which', return_value='/usr/bin/tool'):
            entries = brain.catalogue()
        self.assertEqual({entry['id'] for entry in entries}, set(brain.ACTIONS))
        self.assertEqual(sum(e['phraseCount'] for e in entries), sum(map(len, PHRASES.values())))
        for entry in entries:
            with self.subTest(action=entry['id']):
                self.assertTrue(entry['group'])
                self.assertTrue(entry['description'])
                self.assertTrue(entry['examples'])
                for example in entry['examples']:
                    self.assertEqual(match(example), entry['id'])

    def test_offline_suggestions_do_not_become_actions(self):
        entries = [
            {'id': 'theme_picker', 'label': 'Choose theme', 'available': True, 'examples': ['change theme']},
            {'id': 'unavailable', 'label': 'Unavailable theme', 'available': False, 'examples': ['unavailable theme']},
        ]
        for message in ('help me with themes', 'do not change theme', 'change theme and reboot'):
            result = command_catalog.offline_reply(message, entries)
            self.assertEqual(result['action'], '')
            self.assertEqual(result['route'], 'local')
            self.assertNotIn('unavailable theme', result['text'])

    def test_percentage_chat_skips_model_discovery_and_execution(self):
        with patch('inference.request', side_effect=AssertionError('model requested')) as model, \
             patch.object(brain.command_routes, 'proposal', side_effect=AssertionError('discovery requested')), \
             patch.object(brain, 'execute', side_effect=AssertionError('desktop executed')) as execute:
            for message, action in (
                ('Wisp, please set my volume to 35 percent.', 'param:volume:35'),
                ('adjust display brightness at 72%', 'param:brightness:72'),
                ('set volume to 0%', 'param:volume:0'),
                ('set screen brightness to 100%', 'param:brightness:100'),
                ('set volume to 101%', ''),
                ('set brightness to 0%', ''),
            ):
                with self.subTest(message=message):
                    result = brain.chat(message)
                    self.assertEqual(result['action'], action)
                    self.assertEqual(result['route'], 'local')
            model.assert_not_called()
            execute.assert_not_called()

    def test_percentages_require_whole_requests(self):
        for message in ('do not set volume to 30%', 'never set brightness to 40%',
                        'set volume to 30% and open files', 'set volume to 30% tomorrow',
                        'set volume to 30% if possible', 'say set volume to 30%',
                        '“set volume to 30%”',
                        'set volume to 30%\nopen files', 'set app volume to 30%',
                        'set volume to 30%;reboot', 'set volume to 30% # comment'):
            with self.subTest(message=message):
                self.assertIsNone(parameter_commands.proposal(message))

    def test_model_unavailability_returns_local_nonexecuting_help(self):
        with tempfile.TemporaryDirectory() as temporary, ExitStack() as stack:
            stack.enter_context(patch.object(brain, 'BASE', Path(temporary)))
            stack.enter_context(patch.object(brain.command_routes, 'proposal', return_value=None))
            stack.enter_context(patch('growth.memory_context', return_value={}))
            stack.enter_context(patch('identity.profile', return_value={'name': 'Wisp', 'model': 'test'}))
            stack.enter_context(patch('awareness.context', return_value={}))
            stack.enter_context(patch('playroom.context', return_value={}))
            stack.enter_context(patch.object(brain, 'context', return_value={}))
            stack.enter_context(patch.object(brain.shutil, 'which', return_value='/usr/bin/tool'))
            stack.enter_context(patch('inference.request', side_effect=OSError('offline')))
            execute = stack.enter_context(patch.object(brain, 'execute'))
            result = brain.chat('I need some advice about choosing desktop colors')
            self.assertEqual(result['action'], '')
            self.assertEqual(result['route'], 'local')
            self.assertIn('without AI', result['text'])
            execute.assert_not_called()


if __name__ == '__main__':
    unittest.main()
