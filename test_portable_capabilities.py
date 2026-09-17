"""Clean-install integration checks without a model, desktop or personal adapters."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

PLUGIN = Path(__file__).resolve().parent / 'plugin'
sys.path.insert(0, str(PLUGIN))
import brain
import capabilities
import command_bank
import command_plans
import plan_extensions
from capability_registry import Registry


class PortableCapabilities(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.home = Path(self.temp.name)
        self.state = self.home / 'state/pixel-spirit'
        self.config = self.home / '.config/omarchy'
        self.system = self.home / 'system'
        self.enterContext(patch.dict(os.environ, {
            'HOME': str(self.home), 'XDG_STATE_HOME': str(self.home / 'state'),
            'XDG_CONFIG_HOME': str(self.home / 'xdg-config'),
            'OMARCHY_PATH': str(self.system), 'PATH': ''}))
        self.enterContext(patch.object(brain, 'BASE', self.state))

    def plugin(self):
        path = self.config / 'plugins/demo.weather/manifest.json'
        path.parent.mkdir(parents=True)
        path.write_text(json.dumps(dict(schemaVersion=1, id='demo.weather', name='Weather',
            version='1', kinds=['panel'], entryPoints={'panel': 'Panel.qml'},
            argv=['sh', '-c', 'untrusted'], adapter='machine_commands',
            planSafe=True, verification='state')))
        (self.config / 'shell.json').write_text('{"plugins":[{"id":"demo.weather"}]}')
        return path

    def propose(self, message):
        with patch('shutil.which', return_value='/mock/bin/tool'), \
             patch('inference.request', side_effect=AssertionError('model invoked')), \
             patch('growth.memory_context', side_effect=AssertionError('model fallback entered')), \
             patch.object(brain, '_execute_command', side_effect=AssertionError('control executed')), \
             patch('subprocess.run', side_effect=AssertionError('process launched')), \
             patch('subprocess.Popen', side_effect=AssertionError('process launched')):
            reply = brain.chat(message)
        self.assertEqual(reply['route'], 'local')
        self.assertTrue(reply['action'].startswith('plan:'), reply)
        return reply

    def test_fresh_interpreter_missing_omarchy_model_and_private_modules(self):
        # Isolate imports from the suite's module cache and forbid runtime effects.
        code = '''
import sys, json, subprocess
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0, sys.argv[1])
with patch.object(subprocess, 'run', side_effect=AssertionError('effect')), patch.object(subprocess, 'Popen', side_effect=AssertionError('effect')):
 import capabilities, brain
 entries = capabilities.catalogue()
 assert entries and all(not e['available'] for e in entries)
 assert not {'machine_commands','radio_command','personal_intents','local_life'} & set(sys.modules)
 assert not Path(brain.BASE).exists()
 print(json.dumps({'count':len(entries)}))
'''
        result = subprocess.run([sys.executable, '-I', '-B', '-c', code, str(PLUGIN)],
                                env=dict(os.environ), capture_output=True, text=True, timeout=15)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertGreater(json.loads(result.stdout)['count'], 20)

    def test_fixed_plan_without_personal_bank_or_model(self):
        reply = self.propose('open browser and terminal')
        self.assertEqual([s['action'] for s in reply['steps']], ['browser', 'terminal'])
        self.assertFalse((self.state / command_bank.PERSONAL).exists())

    def test_missing_executable_prevents_runnable_plan(self):
        with patch('shutil.which', return_value=None), patch('inference.request', side_effect=AssertionError('model invoked')):
            reply = brain.chat('open browser and terminal')
        self.assertEqual(reply['action'], '')
        self.assertEqual(reply.get('steps'), [])
        self.assertFalse((self.state / 'command-plan.json').exists())

    def test_new_theme_and_percentage_compound_without_inference(self):
        (self.system / 'themes/tokyo-night').mkdir(parents=True)
        reply = self.propose('switch theme to tokyo night and set volume to 35%')
        self.assertEqual([s['action'] for s in reply['steps']],
                         ['bank:theme:tokyo-night', 'param:volume:35'])

    def test_new_plugin_and_fixed_compound_without_inference(self):
        self.plugin()
        reply = self.propose('open weather and open terminal')
        self.assertEqual([s['action'] for s in reply['steps']], ['bank:plugin:demo.weather', 'terminal'])

    def test_manifest_cannot_inject_argv_or_verification(self):
        self.plugin()
        actions, labels, metadata = plan_extensions.discover(self.state)
        action = 'bank:plugin:demo.weather'
        self.assertEqual(actions[action], ['omarchy', 'shell', 'shell', 'summon', 'demo.weather', '{}'])
        self.assertEqual(metadata[action]['verification'], 'accepted')
        registry = capabilities.registry(extensions=(actions, labels, metadata))
        receipt = registry.receipt(action, {'text': 'Accepted', 'action': '', 'verified': True})
        self.assertEqual(receipt['status'], 'accepted')
        self.assertNotIn('machine_commands', metadata[action].values())

    def test_disabled_or_removed_plugin_invalidates_plan_before_effects(self):
        path = self.plugin()
        for change in ('disabled', 'removed'):
            with self.subTest(change=change):
                (self.config / 'shell.json').write_text('{"plugins":[{"id":"demo.weather"}]}')
                reply = self.propose('open weather and open terminal')
                if change == 'disabled':
                    (self.config / 'shell.json').write_text('{"plugins":[{"id":"demo.weather"}],"disabledPlugins":["demo.weather"]}')
                else:
                    path.unlink()
                with patch('shutil.which', return_value='/mock/bin/tool'):
                    actions, labels, registry = brain.plan_context()
                    self.assertNotIn('bank:plugin:demo.weather', actions)
                    with patch.object(brain, '_execute_command') as execute:
                        with self.assertRaises(ValueError):
                            command_plans.execute(reply['action'], self.state, actions, labels,
                                lambda action: True, execute, registry=registry)
                        execute.assert_not_called()

    def test_percentage_extensions_are_bounded_fixed_argv(self):
        actions, labels, metadata = plan_extensions.discover(self.state)
        self.assertIn('param:volume:0', actions)
        self.assertIn('param:volume:100', actions)
        self.assertIn('param:brightness:1', actions)
        self.assertIn('param:brightness:100', actions)
        for action in ('param:volume:-1', 'param:volume:101', 'param:brightness:0',
                       'param:brightness:101', 'param:volume:35;id'):
            self.assertNotIn(action, actions)
        self.assertFalse(any(action.startswith('bank:') for action in actions))
        self.assertEqual(len(actions), 201)

    def test_state_verification_requires_explicit_readback(self):
        registry = Registry({'mute': ['fixed-control']}, {'mute': 'Mute source'},
                            {'mute': {'verification': 'state'}})
        for payload in ({'status': 'completed'}, {'verified': 1}, {'verified': False}):
            receipt = registry.receipt('mute', dict(text='Requested mute', action='', **payload))
            self.assertEqual(receipt['status'], 'failed')
            self.assertFalse(receipt['ok'])
        receipt = registry.receipt('mute', dict(text='Source mute confirmed', action='', verified=True))
        self.assertEqual(receipt['status'], 'verified')
        self.assertTrue(receipt['ok'])


if __name__ == '__main__':
    unittest.main()
