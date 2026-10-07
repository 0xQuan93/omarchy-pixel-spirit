"""Behavioral checks for saved plans that must never acquire execution authority."""
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / 'plugin'))

import command_plans
from capability_specs import build
import reviewed_routines


class ReviewedRoutineTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.actions = {'browser': ['omarchy', 'launch', 'browser'],
                        'terminal': ['omarchy', 'launch', 'terminal']}
        self.labels = {'browser': 'Open browser', 'terminal': 'Open terminal'}
        self.registry = build(self.actions, self.labels, availability=lambda action: True)

    def plan(self):
        return command_plans.prepare_steps(['browser', 'terminal'], self.base,
                                           self.actions, self.labels, self.registry)

    def test_saved_plan_is_repreviewed_and_never_executed(self):
        initial = self.plan()
        saved = reviewed_routines.save_pending(self.base, initial['action'], 'Work setup', self.registry)
        self.assertEqual(saved['routines'][0]['steps'], 2)
        self.assertEqual(saved['routines'][0]['name'], 'Work setup')
        fresh = reviewed_routines.prepare(self.base, saved['savedId'], self.actions,
                                          self.labels, self.registry)
        self.assertEqual([step['action'] for step in fresh['steps']], ['browser', 'terminal'])
        self.assertNotEqual(fresh['action'], initial['action'])
        self.assertEqual(command_plans.pending(self.base, fresh['action'], self.registry), ['browser', 'terminal'])

    def test_changed_or_removed_capability_cannot_prepare(self):
        saved = reviewed_routines.save_pending(self.base, self.plan()['action'], 'Work setup', self.registry)
        changed = {'browser': ['omarchy', 'launch', 'different-browser'],
                   'terminal': self.actions['terminal']}
        changed_registry = build(changed, self.labels, availability=lambda action: True)
        with self.assertRaisesRegex(ValueError, 'changed'):
            reviewed_routines.prepare(self.base, saved['savedId'], changed, self.labels, changed_registry)
        missing_actions = {'terminal': self.actions['terminal']}
        missing_labels = {'terminal': self.labels['terminal']}
        missing_registry = build(missing_actions, missing_labels, availability=lambda action: True)
        with self.assertRaisesRegex(ValueError, 'no longer registered'):
            reviewed_routines.prepare(self.base, saved['savedId'], missing_actions, missing_labels, missing_registry)

    def test_unavailable_source_and_deleted_routine_do_not_run(self):
        saved = reviewed_routines.save_pending(self.base, self.plan()['action'], 'Work setup', self.registry)
        unavailable = build(self.actions, self.labels, availability=lambda action: action != 'browser')
        self.assertFalse(reviewed_routines.list_saved(self.base, unavailable)['routines'][0]['ready'])
        with self.assertRaisesRegex(ValueError, 'unavailable'):
            reviewed_routines.prepare(self.base, saved['savedId'], self.actions, self.labels, unavailable)
        reviewed_routines.remove(self.base, saved['savedId'], self.registry)
        with self.assertRaisesRegex(ValueError, 'removed'):
            reviewed_routines.prepare(self.base, saved['savedId'], self.actions, self.labels, self.registry)

    def test_invalid_state_is_preserved_and_never_interpreted_as_argv(self):
        path = self.base / 'reviewed-routines.json'
        raw = {'version': 1, 'items': [{'id': '0' * 16, 'name': 'Bad',
               'actions': [['sh', '-c', 'touch /tmp/never']], 'fingerprints': {}, 'createdAt': 1}]}
        path.write_text(json.dumps(raw))
        with self.assertRaisesRegex(ValueError, 'preserved'):
            reviewed_routines.list_saved(self.base, self.registry)
        self.assertEqual(json.loads(path.read_text()), raw)

    def test_empty_or_bool_version_file_is_preserved(self):
        path = self.base / 'reviewed-routines.json'
        for raw in ({}, {'version': True, 'items': []}):
            with self.subTest(raw=raw):
                path.write_text(json.dumps(raw))
                with self.assertRaisesRegex(ValueError, 'preserved'):
                    reviewed_routines.list_saved(self.base, self.registry)
                self.assertEqual(json.loads(path.read_text()), raw)

    def test_readiness_requires_registry_and_full_plan_validation(self):
        actions = {'mute': ['omarchy', 'volume', 'mute'],
                   'unmute': ['omarchy', 'volume', 'unmute']}
        labels = {'mute': 'Mute', 'unmute': 'Unmute'}
        registry = build(actions, labels, availability=lambda _: True)
        path = self.base / 'reviewed-routines.json'
        path.write_text(json.dumps({'version': 1, 'items': [{
            'id': '0' * 16, 'name': 'Contradictory', 'actions': ['mute', 'unmute'],
            'fingerprints': {action: registry.fingerprint(action) for action in actions},
            'createdAt': 1}]}))
        self.assertIsNone(reviewed_routines.list_saved(self.base)['routines'][0]['ready'])
        status = reviewed_routines.list_saved(self.base, registry)['routines'][0]
        self.assertFalse(status['ready'])
        self.assertIn('review', status['reason'])

    def test_invisible_name_is_rejected(self):
        with self.assertRaisesRegex(ValueError, 'printable'):
            reviewed_routines.save_pending(self.base, self.plan()['action'], 'A\u202eB', self.registry)

    def test_duplicate_name_and_bad_token_leave_saved_routine_unchanged(self):
        saved = reviewed_routines.save_pending(self.base, self.plan()['action'], 'Work setup', self.registry)
        with self.assertRaisesRegex(ValueError, 'already has'):
            reviewed_routines.save_pending(self.base, self.plan()['action'], 'work setup', self.registry)
        with self.assertRaisesRegex(ValueError, 'token'):
            reviewed_routines.save_pending(self.base, 'browser', 'Nope', self.registry)
        self.assertEqual([item['id'] for item in reviewed_routines.list_saved(self.base)['routines']], [saved['savedId']])


if __name__ == '__main__':
    unittest.main()
