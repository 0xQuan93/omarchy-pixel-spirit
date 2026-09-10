import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent / 'plugin'))
import awareness as a
import inference
from storage import get, put
from test_brain import b


class AwarenessTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.state = Path(self.temp.name)
        self.patch = patch.object(a, 'STATE', self.state)
        self.patch.start()
        self.addCleanup(self.patch.stop)
        self.growth_patch=patch('growth.STATE', self.state)
        self.growth_patch.start()
        self.addCleanup(self.growth_patch.stop)
        self.load_patch=patch.object(a.os,"getloadavg",return_value=(0,0,0))
        self.load_patch.start()
        self.addCleanup(self.load_patch.stop)

    def test_opt_in_and_power_gate_precede_all_sensing(self):
        with patch.object(a, 'snapshot') as snap, patch.object(a, 'on_ac') as ac:
            self.assertFalse(a.observe()['due'])
            snap.assert_not_called()
            ac.assert_not_called()
        a.configure('enabled', 'on')
        with patch.object(a, 'snapshot') as snap, patch.object(a, 'on_ac', return_value=False):
            self.assertIn('battery', a.observe()['quiet'])
            self.assertIn('battery', a.reflect()['quiet'])
            snap.assert_not_called()

    def test_input_controls_persist_and_reuse_gate_without_observation(self):
        with patch.object(a, 'gate') as gate:
            self.assertFalse(a.input_gate()['allowed'])
            gate.assert_not_called()
        a.configure('mouse_gestures','on')
        a.configure('activity_responses','on')
        self.assertTrue(a.status()['settings']['mouse_gestures'])
        with patch.object(a,'gate',return_value='Locked'), patch.object(a,'snapshot') as snap:
            self.assertFalse(a.input_gate()['allowed'])
            snap.assert_not_called()
        with patch.object(a,'gate',return_value=''):
            self.assertTrue(a.input_gate()['allowed'])
        self.assertFalse((self.state/'awareness.json').exists())

    def test_lock_unknown_dnd_and_power_saver_are_quiet(self):
        settings = dict(a.defaults(), enabled=True)
        with patch.object(a, 'on_ac', return_value=True), patch.object(a.subprocess, 'run') as run, patch.object(a, 'output') as output:
            for returncode in (0, 2):
                run.return_value.returncode = returncode
                self.assertIn('unlocked', a.gate(settings))
            run.return_value.returncode = 1
            output.return_value = 'power-saver'
            self.assertIn('power saver', a.gate(settings))
            output.side_effect = ['balanced', 'on']
            self.assertIn('Disturb', a.gate(settings))

    def test_power_supply_states(self):
        root = self.state / 'supplies'
        root.mkdir()
        bat = root / 'BAT0'
        bat.mkdir()
        (bat / 'type').write_text('Battery')
        self.assertFalse(a.on_ac(root))
        ac = root / 'AC'
        ac.mkdir()
        (ac / 'type').write_text('Mains')
        (ac / 'online').write_text('1')
        self.assertTrue(a.on_ac(root))
        (ac / 'online').write_text('0')
        self.assertFalse(a.on_ac(root))

    def test_metadata_filters_titles_and_sensitive_windows(self):
        raw = {'class': 'org.kde.krita', 'title': 'SECRET document', 'pid': 123,
               'workspace': {'id': 2, 'name': 'SECRET workspace'}, 'fullscreen': 0}
        with patch.object(a, 'output', return_value=json.dumps(raw)):
            observed = a.snapshot()
            self.assertEqual(observed, {'app': 'org.kde.krita', 'category': 'Artist', 'workspace': 2})
            self.assertEqual(a.snapshot(True)['title'], 'SECRET document')
        for change in ({'class': 'Bitwarden'}, {'fullscreen': 1}):
            with patch.object(a, 'output', return_value=json.dumps(raw | change)):
                self.assertIsNone(a.snapshot())

    def test_sampled_rhythm_persists_without_counting_gaps(self):
        a.configure('enabled', 'on')
        observed = {'app': 'Code', 'category': 'Maker', 'workspace': 1}
        with patch.object(a, 'gate', return_value=''), patch.object(a, 'snapshot', return_value=observed):
            for now in (1000, 1060, 1120):
                with patch.object(a.time, 'time', return_value=now):
                    a.observe()
            self.assertEqual(a.status()['minutes']['Maker'], 2)
            with patch.object(a.time, 'time', return_value=8000):
                self.assertFalse(a.observe()['due'])
            self.assertEqual(a.status()['minutes']['Maker'], 2)
            self.assertEqual(len(a.status()['events']), 2)
            self.assertEqual(get(self.state / 'awareness.json', {})['seconds']['Maker'], 120)

    def prepared(self):
        a.configure('enabled', 'on')
        observed = {'app': 'Code', 'category': 'Maker', 'workspace': 1}
        state = a.empty() | {'sampled': 1980, 'since': 1800, 'snapshot': observed}
        put(self.state / 'awareness.json', state)
        return observed

    def test_reflection_is_bounded_throttled_and_has_no_action_channel(self):
        observed = self.prepared()
        answer = {'message': {'content': json.dumps({'text': 'A quiet little coding corner.', 'action': 'terminal'})}}
        with patch.object(a.time, 'time', return_value=2000), patch.object(a, 'gate', return_value=''), patch.object(a, 'snapshot', return_value=observed), patch('identity.profile', return_value={'name': 'Test', 'model': 'test'}), patch.object(inference, 'request', return_value=answer) as request:
            result = a.reflect()
            self.assertEqual(result['reflection']['text'], 'A quiet little coding corner.')
            self.assertNotIn('action', result)
            payload = request.call_args.args[0]
            self.assertEqual(payload['keep_alive'], 0)
            self.assertEqual(payload['options']['num_thread'], 2)
            self.assertEqual(request.call_args.kwargs, {'timeout': 30, 'background': True})
            self.assertIn('quiet', a.reflect())
            self.assertEqual(request.call_count, 1)
            self.assertFalse((self.state / 'history.json').exists())

    def test_changed_consent_or_power_discards_inflight_reflection(self):
        observed = self.prepared()
        answer = {'message': {'content': '{"text":"A thought."}'}}
        with patch.object(a.time, 'time', return_value=2000), patch.object(a, 'snapshot', return_value=observed), patch('identity.profile', return_value={'name': 'Test', 'model': 'test'}):
            with patch.object(a, 'gate', side_effect=['', 'Resting on battery.']), patch.object(inference, 'request', return_value=answer):
                self.assertIn('quiet', a.reflect())
                self.assertEqual(a.status()['reflections'], [])
            self.prepared()
            def clear_during_request(*args, **kwargs):
                a.configure('clear')
                return answer
            with patch.object(a, 'gate', return_value=''), patch.object(inference, 'request', side_effect=clear_during_request):
                self.assertIn('quiet', a.reflect())
                self.assertEqual(a.status()['reflections'], [])

    def test_clear_and_title_revocation_remove_backup_contents(self):
        a.configure('enabled', 'on')
        a.configure('titles', 'on')
        state = a.empty() | {'snapshot': {'title': 'SECRET'}, 'events': [{'title': 'SECRET'}],
                            'reflections': [{'text': 'SECRET'}], 'seconds': {'Maker': 120}}
        put(self.state / 'awareness.json', state)
        a.configure('titles', 'off')
        for file in ('awareness.json', 'awareness.json.bak'):
            self.assertNotIn('SECRET', (self.state / file).read_text())
        a.configure('clear')
        self.assertEqual(a.status()['minutes'], {})
        self.assertEqual(get(self.state / 'awareness.json.bak', {})['seconds'], {})
        self.assertTrue(a.status()['settings']['enabled'])


class ToolRoutingTests(unittest.TestCase):
    def test_supported_paraphrases_do_not_need_a_model(self):
        for phrase, action in [('could you please launch a terminal?', 'terminal'),
                               ('open my notes', 'notes'), ('make it quieter', 'volume_down'),
                               ('open the file explorer', 'files'), ('quiet notifications', 'dnd_on')]:
            self.assertEqual(b.direct_action(phrase), action)
        for phrase in ['do not open my notes', 'if I ask, open notes', 'say "open notes"',
                       'open notes; rm -rf ~', 'start a terminal and delete everything']:
            self.assertEqual(b.direct_action(phrase), '')

    def test_unavailable_tool_is_explained_without_execution_or_model(self):
        with tempfile.TemporaryDirectory() as tmp, patch.object(b, 'BASE', Path(tmp)), patch.object(b.shutil, 'which', return_value=None), patch.object(b, 'run') as run:
            result = b.chat('open my notes')
            self.assertEqual(result['action'], '')
            self.assertIn('obsidian', result['text'])
            with self.assertRaisesRegex(ValueError, 'not installed'):
                b.execute('notes')
            run.assert_not_called()

    def test_native_media_reports_unhandled_instead_of_false_success(self):
        self.assertEqual(b.ACTIONS['pause_music'], ['omarchy', 'shell', 'media', 'pause'])
        with patch.object(b.shutil, 'which', return_value='/test/omarchy'), patch.object(b, 'run', return_value='unhandled'):
            with self.assertRaisesRegex(ValueError, 'No media player'):
                b.execute('pause_music')
        with patch.object(b.shutil, 'which', return_value='/test/omarchy'), patch.object(b, 'run', return_value='ok'):
            self.assertEqual(b.execute('pause_music')['action'], '')

    def test_workspace_tools_use_current_fixed_lua_dispatch(self):
        self.assertEqual(b.ACTIONS['workspace_next'], ['hyprctl', 'dispatch', 'hl.dsp.focus({ workspace = "e+1" })'])
        self.assertEqual(b.ACTIONS['workspace_previous'], ['hyprctl', 'dispatch', 'hl.dsp.focus({ workspace = "e-1" })'])


if __name__ == '__main__':
    unittest.main()
