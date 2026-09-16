from pathlib import Path
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).parent / 'plugin'))
import command_hints as hints
from capabilities import ACTIONS, LABELS
from smart_commands import match


class CommandHintTests(unittest.TestCase):
    def test_authored_families_are_short_routable_and_distinct(self):
        self.assertGreaterEqual(len(hints.HINTS), 20)
        self.assertEqual(len({h[0] for h in hints.HINTS}), len(hints.HINTS))
        for action, categories, example, text in hints.HINTS:
            with self.subTest(action=action):
                self.assertEqual(match(example, ACTIONS), action)
                self.assertLessEqual(len((text + ' ' + LABELS[action]).split()), 30)
                self.assertTrue(set(categories) <= hints.CATEGORIES)

    def test_categories_prefer_relevant_authored_tips(self):
        with patch.object(hints.shutil, 'which', return_value='/usr/bin/tool'):
            for category in hints.CATEGORIES:
                result = hints.choose({'category': category})
                self.assertEqual(result['basis'], category)
                self.assertEqual(result['kind'], 'command-hint')
                self.assertEqual(match(result['example']), result['action'])
                self.assertEqual(result, hints.choose({'category': category}))

    def test_recent_history_avoids_repeating_ids(self):
        with patch.object(hints.shutil, 'which', return_value='/usr/bin/tool'):
            recent = []
            for _ in range(hints.RECENT_LIMIT):
                result = hints.choose({'category': 'Maker'}, recent)
                self.assertIsNotNone(result)
                self.assertNotIn(result['action'], [r['action'] for r in recent])
                recent.append(result)
            result = hints.choose({'category': 'Maker'}, [r['action'] for r in recent])
            self.assertNotIn(result['action'], [r['action'] for r in recent])
            # Only the bounded tail counts; no growing lifetime blacklist.
            first = hints.choose({'category': 'Maker'})
            self.assertEqual(hints.choose({'category': 'Maker'}, [first] + [{}] * 12), first)

    def test_rotation_reaches_every_family_without_growing_history(self):
        with patch.object(hints.shutil, 'which', return_value='/usr/bin/tool'):
            for category in (*hints.CATEGORIES, 'Other'):
                expected = {h[0] for h in hints.HINTS if not h[1] or category in h[1]}
                seen, recent = set(), []
                for _ in range(len(expected)):
                    result = hints.choose({'category': category}, recent)
                    seen.add(result['action'])
                    recent = (recent + [result])[-hints.RECENT_LIMIT:]
                self.assertEqual(seen, expected)

    def test_no_context_leak_or_invented_category(self):
        with patch.object(hints.shutil, 'which', return_value='/usr/bin/tool'):
            general = hints.choose({})
            for category in ('SECRET', None, [], {'title': 'SECRET'}):
                result = hints.choose({'category': category, 'app': 'SECRET', 'title': 'SECRET', 'workspace': 'SECRET'})
                self.assertEqual(result, general)
                self.assertNotIn('SECRET', str(result))
            self.assertIsNone(hints.choose(None))

    def test_unavailable_or_excluded_commands_produce_no_hint(self):
        with patch.object(hints.shutil, 'which', return_value=None):
            self.assertIsNone(hints.choose({'category': 'Maker'}))
        only = hints.HINTS[:1]
        with patch.object(hints, 'HINTS', only), patch.object(hints.shutil, 'which', return_value='/usr/bin/tool'):
            self.assertIsNone(hints.choose({'category': 'Maker'}, ['terminal']))
            self.assertIsNone(hints.choose({'category': 'Other'}))

    def test_never_runs_a_command_or_requests_inference(self):
        with patch('subprocess.run', side_effect=AssertionError('executed')), \
             patch('inference.request', side_effect=AssertionError('inference')), \
             patch.object(hints.shutil, 'which', return_value='/usr/bin/tool'):
            self.assertIsNotNone(hints.choose({'category': 'Artist'}))


if __name__ == '__main__':
    unittest.main()
