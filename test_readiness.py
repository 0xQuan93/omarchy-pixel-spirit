"""Readiness checks inspect fixed local status without operating a control."""
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).parent / 'plugin'))
import brain
import capabilities
import readiness


class ReadinessTests(unittest.TestCase):
    def test_generic_catalogue_avoids_live_probes_until_commands_open(self):
        with patch('shutil.which', return_value='/bin/control'), \
             patch.object(readiness, '_media_status', return_value=None) as media, \
             patch.object(readiness, '_microphone_present', return_value=False) as microphone:
            capabilities.catalogue()
            media.assert_not_called()
            microphone.assert_not_called()
            capabilities.catalogue(probe_stateful=True)
            media.assert_called_once()
            microphone.assert_called_once()

    def test_media_status_is_fixed_bounded_read_only_and_minimized(self):
        status = {'hasPlayer': True, 'playing': True, 'canGoNext': False,
                  'canGoPrevious': True, 'canTogglePlaying': True,
                  'title': 'A private track title'}
        with patch.object(readiness.subprocess, 'run') as run:
            run.return_value.stdout = json.dumps(status)
            result = readiness._media_status()
            run.assert_called_once_with(['omarchy', 'shell', 'media', 'status'],
                                        capture_output=True, text=True,
                                        timeout=readiness.PROBE_TIMEOUT, check=True)
        self.assertNotIn('title', result)
        with patch.object(readiness.shutil, 'which', return_value='/bin/omarchy'), \
             patch.object(readiness, '_media_status', return_value=result) as probe:
            cache = {}
            self.assertTrue(readiness.check('pause_music', ['omarchy'], cache)['actionable'])
            self.assertFalse(readiness.check('next_track', ['omarchy'], cache)['suggestable'])
            self.assertTrue(readiness.check('next_track', ['omarchy'], cache)['actionable'])
            self.assertTrue(readiness.check('previous_track', ['omarchy'], cache)['actionable'])
            probe.assert_called_once()

    def test_no_player_and_unknown_probe_are_distinct(self):
        with patch.object(readiness.shutil, 'which', return_value='/bin/omarchy'):
            with patch.object(readiness, '_media_status', return_value={'hasPlayer': False, 'playing': False}):
                missing = readiness.check('pause_music', ['omarchy'])
            with patch.object(readiness, '_media_status', return_value=None):
                unknown = readiness.check('pause_music', ['omarchy'])
        self.assertIs(missing['connected'], False)
        self.assertFalse(missing['actionable'])
        self.assertIsNone(unknown['connected'])
        self.assertTrue(unknown['actionable'])
        self.assertIn('could not be checked', unknown['reason'])

    def test_missing_tool_does_not_probe_and_malformed_status_fails_unknown(self):
        with patch.object(readiness.shutil, 'which', return_value=None), \
             patch.object(readiness, '_media_status') as probe:
            missing = readiness.check('pause_music', ['omarchy'])
            self.assertFalse(missing['installed'])
            probe.assert_not_called()
        with patch.object(readiness.subprocess, 'run') as run:
            run.return_value.stdout = '{"hasPlayer": "yes"}'
            self.assertIsNone(readiness._media_status())
            run.return_value.stdout = 'x' * (readiness.MAX_STATUS_BYTES + 1)
            self.assertIsNone(readiness._media_status())

    def test_run_rechecks_media_after_proposal_without_executing_stale_action(self):
        playing = {'hasPlayer': True, 'playing': True, 'canGoNext': True,
                   'canGoPrevious': True, 'canTogglePlaying': True}
        closed = {'hasPlayer': False, 'playing': False}
        with tempfile.TemporaryDirectory() as temp, patch.object(brain, 'BASE', Path(temp)), \
             patch.object(readiness.shutil, 'which', return_value='/bin/omarchy'), \
             patch.object(readiness, '_media_status', side_effect=[playing, closed]), \
             patch.object(brain, 'run') as control:
            proposed = brain.chat('pause music')
            self.assertEqual(proposed['action'], 'pause_music')
            with self.assertRaisesRegex(ValueError, 'No controllable media player'):
                brain.execute('pause_music')
            control.assert_not_called()


if __name__ == '__main__':
    unittest.main()
