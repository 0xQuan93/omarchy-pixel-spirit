"""Independent fixed-source readback checks; no live commands are invoked."""
from pathlib import Path
import subprocess
import sys
import unittest
from unittest.mock import Mock

sys.path.insert(0, str(Path(__file__).parent / 'plugin'))
from desktop_verification import verify


class DesktopVerificationTests(unittest.TestCase):
    def test_input_and_output_read_the_correct_source_and_expected_state(self):
        for action, target, muted in (
            ('mute', '@DEFAULT_AUDIO_SINK@', True),
            ('unmute', '@DEFAULT_AUDIO_SINK@', False),
            ('mic_mute', '@DEFAULT_AUDIO_SOURCE@', True),
            ('mic_unmute', '@DEFAULT_AUDIO_SOURCE@', False),
        ):
            with self.subTest(action=action):
                invoke = Mock(return_value=subprocess.CompletedProcess([], 0,
                    'Volume: 0.43' + (' [MUTED]' if muted else '') + '\n'))
                self.assertTrue(verify(action, invoke=invoke))
                invoke.assert_called_once_with(['wpctl', 'get-volume', target],
                    capture_output=True, text=True, timeout=2, check=True)

    def test_opposite_audio_state_never_confirms_success(self):
        for action in ('mute', 'mic_mute', 'unmute', 'mic_unmute'):
            muted = action in ('unmute', 'mic_unmute')
            invoke = Mock(return_value=subprocess.CompletedProcess([], 0,
                'Volume: 0.50' + (' [MUTED]' if muted else '')))
            with self.subTest(action=action):
                self.assertFalse(verify(action, invoke=invoke))

    def test_malformed_audio_readbacks_fail_closed(self):
        samples = ('', 'error: no such node', 'Volume: unknown', 'Volume: -1.00',
                   'Volume: NaN [MUTED]', 'Volume: 0.30 [MUTE]',
                   'Volume: 0.30 [MUTED]\nVolume: 0.50',
                   'node 12 Volume: 0.30 [MUTED]',
                   'Volume: 0.30 [MUTED] extra', '{"muted":true}')
        for action in ('mute', 'unmute', 'mic_mute', 'mic_unmute'):
            for sample in samples:
                with self.subTest(action=action, sample=sample):
                    invoke = Mock(return_value=subprocess.CompletedProcess([], 0, sample))
                    self.assertFalse(verify(action, invoke=invoke))

    def test_profiles_use_fixed_readback_and_exact_expected_name(self):
        for action, expected in (('power_saver', 'power-saver'), ('power_balanced', 'balanced')):
            with self.subTest(action=action):
                invoke = Mock(return_value=subprocess.CompletedProcess([], 0, expected + '\n'))
                self.assertTrue(verify(action, invoke=invoke))
                invoke.assert_called_once_with(['powerprofilesctl', 'get'],
                    capture_output=True, text=True, timeout=2, check=True)
                for other in ('performance', '', 'balanced\npower-saver',
                              'balanced' if expected == 'power-saver' else 'power-saver'):
                    invoke.return_value.stdout = other
                    self.assertFalse(verify(action, invoke=invoke))

    def test_timeout_and_command_failures_are_not_reported_as_verified(self):
        for action in ('mute', 'mic_unmute', 'power_saver'):
            for exception in (subprocess.TimeoutExpired(['fixed-command'], 2),
                              subprocess.CalledProcessError(1, ['fixed-command']),
                              FileNotFoundError('Missing tool')):
                with self.subTest(action=action, error=type(exception).__name__):
                    invoke = Mock(side_effect=exception)
                    with self.assertRaises(type(exception)):
                        verify(action, invoke=invoke)
                    self.assertEqual(invoke.call_count, 1)

    def test_unknown_and_injected_action_names_never_invoke(self):
        for action in ('', 'volume_up', 'mute; shutdown now',
                       'mic_mute $(touch /tmp/unwanted)', 'mute\nwhoami',
                       '--help', 'power_balanced --profile performance',
                       '@DEFAULT_AUDIO_SOURCE@', 'MUTE', 'mute '):
            with self.subTest(action=action):
                invoke = Mock()
                self.assertFalse(verify(action, invoke=invoke))
                invoke.assert_not_called()


if __name__ == '__main__':
    unittest.main()
