"""Safety and presentation contracts for the fixed desktop catalogue."""
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).parent / 'plugin'))
import desktop_commands as commands


class DesktopCommandTests(unittest.TestCase):
    def test_every_action_has_display_metadata_and_fixed_argv(self):
        keys = set(commands.ACTIONS)
        for mapping in (commands.LABELS, commands.CATEGORIES, commands.DESCRIPTIONS):
            self.assertEqual(keys, set(mapping))
            self.assertTrue(all(isinstance(text, str) and text for text in mapping.values()))
        for action, argv in commands.ACTIONS.items():
            with self.subTest(action=action):
                self.assertIsInstance(argv, list)
                self.assertIn(argv[0], ('omarchy', 'hyprctl', 'wpctl'))
                self.assertTrue(all(isinstance(arg, str) and arg for arg in argv))
                self.assertNotIn('-c', argv)

    def test_nightlight_state_is_not_accidentally_a_toggle(self):
        for state, method, receipt in (('on', 'enable', 'enabled'), ('off', 'disable', 'disabled')):
            action = 'nightlight_' + state
            self.assertEqual(commands.ACTIONS[action], ['omarchy', 'shell', 'nightlight', method])
            self.assertEqual(commands.RECEIPTS[action], {receipt})
            self.assertIn(action, commands.ASYNC_ACTIONS)
            self.assertNotIn(action, commands.IPC_ACTIONS)

    def test_bar_negative_flag_and_microphone_explicit_state(self):
        self.assertEqual(commands.ACTIONS['bar_show'][-1], 'off')
        self.assertEqual(commands.ACTIONS['bar_hide'][-1], 'on')
        self.assertEqual(commands.ACTIONS['mic_mute'], ['wpctl', 'set-mute', '@DEFAULT_AUDIO_SOURCE@', '1'])
        self.assertEqual(commands.ACTIONS['mic_unmute'], ['wpctl', 'set-mute', '@DEFAULT_AUDIO_SOURCE@', '0'])

    def test_interactive_capture_uses_nonblocking_menu_and_receipt(self):
        for action in ('screenshot', 'capture_text', 'capture_qr'):
            self.assertEqual(commands.ACTIONS[action][:3], ['omarchy', 'menu', 'summon'])
            self.assertIn(action, commands.ASYNC_ACTIONS)
            self.assertEqual(commands.RECEIPTS[action], {'ok'})
        self.assertEqual(commands.ACTIONS['recording_stop'],
                         ['omarchy', 'capture', 'screenrecording', '--stop-recording'])

    def test_receipt_coverage_and_bounded_workspaces(self):
        for action, argv in commands.ACTIONS.items():
            if action in commands.IPC_ACTIONS or argv[0] == 'hyprctl':
                self.assertEqual(commands.RECEIPTS[action], {'ok'})
        for number in range(1, 11):
            for prefix in ('workspace_', 'window_workspace_'):
                self.assertIn('workspace = "' + str(number) + '"', commands.ACTIONS[prefix + str(number)][2])
        for number in (0, 11, -1):
            self.assertNotIn('workspace_' + str(number), commands.ACTIONS)
            self.assertNotIn('window_workspace_' + str(number), commands.ACTIONS)

    def test_close_requires_confirmation_and_power_routes_only_open_menu(self):
        self.assertIn('window_close', commands.CONFIRM_ACTIONS)
        self.assertEqual(commands.ACTIONS['power_menu'], ['omarchy', 'menu', 'summon', 'system'])
        for argv in commands.ACTIONS.values():
            self.assertNotIn(argv[:2], [['omarchy', 'refresh'], ['omarchy', 'reinstall']])
            self.assertNotIn(argv, [['omarchy', 'system', 'shutdown'], ['omarchy', 'system', 'reboot']])


if __name__ == '__main__':
    unittest.main()
