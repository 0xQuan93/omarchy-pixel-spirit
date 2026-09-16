"""Integration tests for local proposals and fixed, revalidated execution."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).parent / 'plugin'))
import brain
import command_bank
import command_routes


class CommandRouteTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        root = Path(temp.name)
        self.config, self.system, self.state = [root / p for p in ('config', 'system', 'state')]
        self.config.mkdir()
        self.state.mkdir()
        self.theme = self.system / 'themes/tokyo-night'
        self.theme.mkdir(parents=True)
        self.manifest = self.config / 'plugins/demo.weather/manifest.json'
        self.manifest.parent.mkdir(parents=True)
        self.manifest.write_text(json.dumps({
            'schemaVersion': 1, 'id': 'demo.weather', 'name': 'Weather',
            'kinds': ['panel'], 'entryPoints': {'panel': 'Panel.qml'},
        }))
        (self.config / 'shell.json').write_text('{"plugins":[{"id":"demo.weather"}]}')
        for patcher in (patch.object(brain, 'BASE', self.state),
                        patch.object(command_bank, 'defaults', return_value=(self.config, self.system, self.state))):
            patcher.start()
            self.addCleanup(patcher.stop)

    def test_static_and_discovered_chat_never_infer_or_execute(self):
        with patch('inference.request', side_effect=AssertionError('model used')) as inference, \
             patch.object(brain, 'execute') as execute, \
             patch.object(command_routes.subprocess, 'run', side_effect=AssertionError('execution during proposal')) as run, \
             patch.object(brain.shutil, 'which', return_value='/usr/bin/omarchy'):
            for message, action in (
                ('change the theme', 'theme_picker'),
                ('open weather', 'bank:plugin:demo.weather'),
                ('change the theme to Tokyo Night', 'bank:theme:tokyo-night'),
            ):
                with self.subTest(message=message):
                    result = brain.chat(message)
                    self.assertEqual(result['action'], action)
                    self.assertIn('Tap Run', result['text'])
            inference.assert_not_called()
            execute.assert_not_called()
            run.assert_not_called()

    def test_stale_theme_and_disabled_plugin_rejected_before_execution(self):
        theme = command_routes.proposal('change theme to tokyo night', self.state)['action']
        plugin = command_routes.proposal('open weather', self.state)['action']
        self.theme.rmdir()
        (self.config / 'shell.json').write_text('{"plugins":[{"id":"demo.weather"}],"disabledPlugins":["demo.weather"]}')
        with patch.object(command_routes.subprocess, 'run') as run:
            for action in (theme, plugin):
                with self.subTest(action=action), self.assertRaises(ValueError):
                    brain.execute(action)
            run.assert_not_called()

    def test_theme_execution_uses_revalidated_fixed_argv(self):
        with patch.object(command_routes.shutil, 'which', return_value='/usr/bin/omarchy'), \
             patch.object(command_routes.subprocess, 'run', return_value=subprocess.CompletedProcess([], 0, '')) as run:
            result = brain.execute('bank:theme:tokyo-night')
            run.assert_called_once_with(['omarchy', 'theme', 'set', 'tokyo-night'],
                                        capture_output=True, text=True, timeout=60, check=True)
            self.assertEqual(result['action'], '')

    def test_plugin_execution_uses_fixed_summon_and_literal_receipt(self):
        with patch.object(command_routes.shutil, 'which', return_value='/usr/bin/omarchy'), \
             patch.object(command_routes.subprocess, 'run', return_value=subprocess.CompletedProcess([], 0, 'ok\n')) as run:
            result = brain.execute('bank:plugin:demo.weather')
            run.assert_called_once_with(['omarchy', 'shell', 'shell', 'summon', 'demo.weather', '{}'],
                                        capture_output=True, text=True, timeout=60, check=True)
            self.assertEqual(result['action'], '')

    def test_static_execution_accepts_literal_receipt_with_fixed_argv(self):
        with patch.object(brain.shutil, 'which', return_value='/usr/bin/omarchy'):
            for action, argv in (
                ('theme_picker', ['omarchy', 'menu', 'summon', 'style.theme']),
                ('settings_audio', ['omarchy', 'shell', 'shell', 'summon', 'omarchy.audio', '{}']),
            ):
                with self.subTest(action=action), patch.object(brain, 'run', return_value='ok') as run:
                    self.assertEqual(brain.execute(action)['action'], '')
                    run.assert_called_once_with(argv)

    def test_bad_personal_action_never_runs(self):
        with patch.object(command_routes.subprocess, 'run') as run:
            for action in ('bank:theme:$(touch x)', 'bank:plugin:demo.weather:extra',
                           'bank:argv:sh', 'bank:theme:missing', 'bank::'):
                with self.subTest(action=action), self.assertRaises(ValueError):
                    brain.execute(action)
            run.assert_not_called()

    def test_failed_plugin_receipt_is_not_success(self):
        with patch.object(command_routes.shutil, 'which', return_value='/usr/bin/omarchy'):
            for output in ('', 'error', '{"ok":false}', 'not found'):
                with self.subTest(output=output), \
                     patch.object(command_routes.subprocess, 'run', return_value=subprocess.CompletedProcess([], 0, output)), \
                     self.assertRaises(ValueError):
                    brain.execute('bank:plugin:demo.weather')

    def test_failed_static_receipt_is_not_success(self):
        with patch.object(brain.shutil, 'which', return_value='/usr/bin/omarchy'):
            for action in ('theme_picker', 'settings_audio', 'pause_music'):
                for output in ('', 'error', '{"ok":false}'):
                    with self.subTest(action=action, output=output), \
                         patch.object(brain, 'run', return_value=output) as run, \
                         self.assertRaises(ValueError):
                        brain.execute(action)
                    run.assert_called_once_with(brain.ACTIONS[action])

    def test_refresh_uses_discovery_without_model(self):
        with patch('inference.request', side_effect=AssertionError('model used')) as inference:
            result = brain.chat('scan installed plugins')
            self.assertEqual(result['action'], '')
            self.assertTrue((self.state / command_bank.GENERATED).exists())
            inference.assert_not_called()


if __name__ == '__main__':
    unittest.main()
