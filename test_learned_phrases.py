"""Behavioral checks for private learned replies and reviewed command proposals."""
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).parent / 'plugin'))
import learned_phrases as learned
from capability_registry import Registry


class LearnedPhraseTests(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)
        self.base = Path(self.folder.name)
        self.registry = self.control()

    @staticmethod
    def control(argv=None, available=True):
        return Registry({'browser': argv or ['reviewed-browser']},
                        {'browser': 'Open browser'},
                        availability=lambda action: available)

    def remember(self, phrase='Explain tiling window managers', data=None, reason=''):
        if data is None:
            data = {'text': 'Tiling arranges windows without overlap.',
                    'emote': 'reading', 'action': ''}
        generation = learned.begin(self.base, phrase)
        learned.complete(self.base, phrase, generation, data, self.registry, reason)
        return learned.lookup(self.base, phrase, self.registry)

    def test_keys_preserve_meaning_timing_and_literal_case(self):
        for first, second in (
            ('weather', 'weather now'),
            ('open cartoons', 'do not open cartoons'),
            ('explain "ABC"', 'explain "abc"'),
            ('explain "a  b"', 'explain "a b"'),
            ('explain "a\tb"', 'explain "a b"'),
            ('open /Work/Foo', 'open /work/foo'),
            ('explain one line', 'explain one\nline'),
            ('explain "quoted"', 'explain quoted'),
            ('set 1:30', 'set 130'),
        ):
            with self.subTest(first=first, second=second):
                self.assertNotEqual(learned.key_for(first), learned.key_for(second))
        self.assertEqual(learned.key_for(' Explain café '),
                         learned.key_for('Explain cafe\u0301'))
        for message in ('', ' \t ', 'x' * 4001, None):
            with self.subTest(message=str(message)[:20]), self.assertRaises(ValueError):
                learned.key_for(message)

    def test_answer_is_dated_snapshot_and_does_not_replay_extra_controls(self):
        result = self.remember(data={
            'text': 'A window manager arranges application windows.',
            'emote': 'reading', 'action': '',
            'argv': ['unsafe-program'], 'choices': [{'action': 'unsafe'}],
            'resources': [{'url': 'file:///private'}], 'learnedKey': 'forged',
        })
        self.assertEqual(result['route'], 'learned')
        self.assertEqual(result['learnedKind'], 'answer')
        self.assertTrue(result['text'].startswith('Saved local AI reply · '))
        self.assertIn('A window manager arranges application windows.', result['text'])
        self.assertEqual(result['action'], '')
        self.assertNotEqual(result['learnedKey'], 'forged')
        raw = (self.base / learned.FILE).read_text()
        for field in ('argv', 'choices', 'resources'):
            self.assertNotIn(field, result)
            self.assertNotIn('"' + field + '"', raw)
        self.assertNotIn('unsafe-program', raw)

    def test_action_is_reconstructed_proposal_without_effects(self):
        with patch('subprocess.run') as run, patch('subprocess.Popen') as popen:
            result = self.remember('Start a browser for research', {
                'text': 'Already executed.', 'emote': 'working', 'action': 'browser',
                'actionLabel': 'Forged label', 'argv': ['unsafe-program'],
            })
            self.assertEqual(result['action'], 'browser')
            self.assertEqual(result['actionLabel'], 'Open browser')
            self.assertIn('Tap Run', result['text'])
            self.assertNotIn('Already executed', result['text'])
            run.assert_not_called()
            popen.assert_not_called()
        raw = (self.base / learned.FILE).read_text()
        self.assertNotIn('unsafe-program', raw)
        self.assertNotIn('Already executed', raw)

    def test_action_requires_current_registration_fingerprint_and_availability(self):
        phrase = 'Start a browser for research'
        self.remember(phrase, {'text': 'Ready', 'emote': 'working', 'action': 'browser'})
        variants = (
            self.control(argv=['different-browser']),
            self.control(available={'available': False, 'reason': 'Disabled by user'}),
            Registry({}, {}, availability=lambda action: True),
        )
        with patch('subprocess.run') as run:
            for registry in variants:
                with self.subTest(registry=registry):
                    result = learned.lookup(self.base, phrase, registry)
                    self.assertEqual(result['action'], '')
                    self.assertIn('unavailable', result['text'].lower())
            run.assert_not_called()

    def test_failed_contextual_and_side_effect_attempts_remain_retryable(self):
        ordinary = {'text': 'This is not a completed answer.', 'emote': 'reading', 'action': ''}
        cases = [
            ('Explain compositors ' + reason, ordinary, reason)
            for reason in ('unavailable', 'incomplete', 'invalid')
        ] + [
            ('Tell me more', ordinary, ''),
            ('Open that one', ordinary | {'action': 'browser'}, ''),
            ('Choose a garden activity', ordinary | {'roomActivity': 'garden'}, ''),
            ('Choose a companion name', ordinary | {'chosenName': 'Name'}, ''),
            ('Write a useful routine', ordinary | {'automationScript': {'code': 'unsafe'}}, ''),
            ('Explain a failed request', ordinary | {'ok': False}, ''),
            ('Explain an errored request', ordinary | {'errors': ['failed']}, ''),
            ('Explain a cancelled request', ordinary | {'status': 'cancelled'}, ''),
            ('Explain an invalid emote', ordinary | {'emote': []}, ''),
            ('Explain an unknown action', ordinary | {'action': 'arbitrary-shell'}, ''),
        ]
        for phrase, data, reason in cases:
            with self.subTest(phrase=phrase):
                result = self.remember(phrase, data, reason)
                self.assertEqual(result['learnedKind'], 'unresolved')
                self.assertEqual(result['action'], '')
                self.assertIn('Ask again', result['text'])
                self.assertNotIn(ordinary['text'], result['text'])
        phrase = 'Explain an interrupted attempt'
        learned.begin(self.base, phrase)
        self.assertIn('did not finish', learned.lookup(self.base, phrase, self.registry)['text'])

    def test_forget_and_refresh_cannot_resurrect_old_inflight_answers(self):
        phrase = 'Explain Wayland protocols'
        first = learned.begin(self.base, phrase)
        learned.forget(self.base, learned.key_for(phrase))
        data = {'text': 'Stale answer', 'emote': 'reading', 'action': ''}
        self.assertEqual(learned.complete(self.base, phrase, first, data, self.registry), {})
        self.assertIsNone(learned.lookup(self.base, phrase, self.registry))
        with self.assertRaises(ValueError):
            learned.phrase(self.base, learned.key_for(phrase))
        second = learned.begin(self.base, phrase)
        third = learned.begin(self.base, phrase)
        self.assertEqual(learned.complete(self.base, phrase, second, data, self.registry), {})
        learned.complete(self.base, phrase, third, data | {'text': 'Fresh answer'}, self.registry)
        result = learned.lookup(self.base, phrase, self.registry)
        self.assertIn('Fresh answer', result['text'])
        self.assertNotIn('Stale answer', result['text'])

    def test_private_files_and_forget_remove_recovery_copies(self):
        phrase = 'Explain my private saved topic'
        self.remember(phrase)
        for name in (learned.FILE, learned.FILE + '.bak'):
            path = self.base / name
            self.assertEqual(path.stat().st_mode & 0o777, 0o600)
            self.assertIn(phrase, path.read_text())
        self.remember('Explain another saved topic')
        learned.forget(self.base, learned.key_for(phrase))
        for name in (learned.FILE, learned.FILE + '.bak'):
            self.assertNotIn(phrase, (self.base / name).read_text())
        learned.forget(self.base)
        for name in (learned.FILE, learned.FILE + '.bak'):
            self.assertEqual(json.loads((self.base / name).read_text())['entries'], [])

    def test_bounds_evict_least_recently_used_and_limit_storage_bytes(self):
        with patch.object(learned, 'MAX_ENTRIES', 2):
            for index in range(2):
                with patch.object(learned.time, 'time', return_value=1000 + index):
                    self.remember('Explain concept ' + str(index))
            with patch.object(learned.time, 'time', return_value=1010):
                learned.lookup(self.base, 'Explain concept 0', self.registry)
            with patch.object(learned.time, 'time', return_value=1020):
                self.remember('Explain concept 2')
            self.assertIsNotNone(learned.lookup(self.base, 'Explain concept 0', self.registry))
            self.assertIsNone(learned.lookup(self.base, 'Explain concept 1', self.registry))
            self.assertIsNotNone(learned.lookup(self.base, 'Explain concept 2', self.registry))
        learned.forget(self.base)
        with patch.object(learned, 'MAX_BYTES', 1600):
            for index in range(4):
                self.remember('Explain bounded concept ' + str(index), {
                    'text': 'x' * 700, 'emote': 'reading', 'action': '',
                })
            for name in (learned.FILE, learned.FILE + '.bak'):
                self.assertLessEqual((self.base / name).stat().st_size, 1600)
            saved = json.loads((self.base / learned.FILE).read_text())['entries']
            self.assertLess(len(saved), 4)
            self.assertEqual(saved[0]['phrase'], 'Explain bounded concept 3')

    def test_corrupt_data_falls_back_without_proposing_an_action(self):
        phrase = 'Explain a saved compositor'
        self.remember(phrase)
        (self.base / learned.FILE).write_text('{damaged')
        result = learned.lookup(self.base, phrase, self.registry)
        self.assertEqual(result['learnedKind'], 'answer')
        (self.base / (learned.FILE + '.bak')).write_text('{also damaged')
        (self.base / learned.FILE).write_text('{damaged again')
        self.assertIsNone(learned.lookup(self.base, phrase, self.registry))
        self.assertEqual((self.base / learned.FILE).read_text(), '{damaged again')

    def test_invalid_saved_timestamp_never_crashes_reply_rendering(self):
        phrase = 'Explain a saved compositor'
        self.remember(phrase)
        path = self.base / learned.FILE
        data = json.loads(path.read_text())
        data['entries'][0]['created'] = 1e100
        path.write_text(json.dumps(data))
        result = learned.lookup(self.base, phrase, self.registry)
        self.assertTrue(result is None or result['action'] == '')

    def test_saved_answer_still_works_when_usage_update_cannot_be_written(self):
        phrase = 'Explain tiling window managers'
        self.remember(phrase)
        with patch.object(learned, '_write', side_effect=OSError('Disk full')):
            result = learned.lookup(self.base, phrase, self.registry)
        self.assertIsNotNone(result)
        self.assertEqual(result['learnedKind'], 'answer')
        self.assertIn('Tiling arranges windows', result['text'])


if __name__ == '__main__':
    unittest.main()
