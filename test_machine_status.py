"""Current machine answers use fixed readbacks and conservative language."""

from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).parent / 'plugin'))
import machine_status as status


class QuestionTests(unittest.TestCase):
    def test_clear_present_tense_questions(self):
        examples = {
            'What is my current volume?': 'volume',
            "What's the speaker volume at?": 'volume',
            'Please, what is my current volume?': 'volume',
            'Could you tell me what my current volume is?': 'volume',
            'Is my sound muted?': 'mute',
            'Are my speakers muted?': 'mute',
            'Is my output muted?': 'mute',
            'What power profile am I using?': 'profile',
            'What is my current power mode?': 'profile',
            'Is power saver on?': 'power_saver',
            'Am I in battery saver mode?': 'power_saver',
            'How much battery do I have?': 'battery',
            "What's my battery percentage?": 'battery',
            "How's my battery?": 'battery_overview',
            'Is my laptop charging?': 'charging',
            'Can you tell me if my laptop is charging?': 'charging',
            'Am I plugged in?': 'external',
            'Is my computer on AC power?': 'external',
        }
        for phrase, kind in examples.items():
            with self.subTest(phrase=phrase):
                self.assertEqual(status.question_kind(phrase), kind)

    def test_commands_hypotheticals_history_and_other_sources_do_not_probe(self):
        for phrase in (
            'Turn my volume down', 'Mute my speakers', 'Enable power saver',
            'If I ask what my volume is, answer me',
            'What was my volume yesterday?',
            'What would my battery level be after an hour?',
            'Explain what power saver does',
            'Is my microphone muted?',
            'What is my volume and turn it down?',
            'Is my laptop charging; open a terminal',
            'Tell me what my battery level was',
            'Could you tell me what my volume was yesterday?',
        ):
            with self.subTest(phrase=phrase), patch.object(status, 'read_output_volume') as volume, \
                    patch.object(status, 'read_power_profile') as profile, \
                    patch.object(status, 'read_power_supplies') as supplies:
                self.assertIsNone(status.reply(phrase))
                volume.assert_not_called()
                profile.assert_not_called()
                supplies.assert_not_called()

    def test_other_live_questions_are_non_replayable_without_overmatching(self):
        for phrase in ('Is do not disturb on?', 'Could you tell me if DND is active?',
                       'How is my computer doing?', 'Is my Wi-Fi connected?',
                       'What app is active?'):
            with self.subTest(phrase=phrase):
                self.assertTrue(status.requires_freshness(phrase))
                self.assertIsNone(status.question_kind(phrase))
        for phrase in ('Turn on do not disturb', 'How was my computer doing yesterday?',
                       'If DND is on, pause music', 'Explain Wi-Fi connections'):
            with self.subTest(phrase=phrase):
                self.assertFalse(status.requires_freshness(phrase))


class ReadbackTests(unittest.TestCase):
    def test_output_volume_and_mute_use_fixed_command(self):
        with patch.object(status.subprocess, 'run') as run:
            run.return_value.stdout = 'Volume: 0.35 [MUTED]\n'
            self.assertEqual(status.reply('What is my volume?')['text'],
                             'Output volume is 35%. It is muted.')
            self.assertEqual(status.reply('Is my audio muted?')['text'],
                             'The audio output is muted.')
            run.assert_called_with(['wpctl', 'get-volume', '@DEFAULT_AUDIO_SINK@'],
                                   capture_output=True, text=True, timeout=2, check=True)
            run.return_value.stdout = 'Volume: 0.80\n'
            self.assertEqual(status.reply('Is my sound muted?')['text'],
                             'The audio output is not muted.')
            run.return_value.stdout = 'unexpected'
            unknown = status.reply('What is my volume?')
            self.assertIn('cannot read', unknown['text'])
            self.assertEqual(unknown['evidence']['status'], 'unknown')
            self.assertTrue(unknown['evidence']['unknownReason'])
            run.side_effect = subprocess.TimeoutExpired('wpctl', 2)
            self.assertIn('cannot read', status.reply('What is my volume?')['text'])

    def test_fresh_evidence_names_source_and_expires(self):
        with patch.object(status, 'read_output_volume', return_value=(35, False)):
            first = status.reply('What is my volume?')
        self.assertEqual(first['evidence']['sourceId'], 'desktop.audio-output')
        self.assertEqual(first['evidence']['status'], 'verified')
        self.assertEqual(first['evidence']['verification'], 'state')
        self.assertEqual(first['evidence']['unknownReason'], '')
        self.assertEqual(first['evidence']['expiresAtMs'] - first['evidence']['observedAtMs'],
                         status.EVIDENCE_TTL_MS)
        with patch.object(status, 'read_power_supplies', return_value={'batteries': [], 'external': True}):
            absent = status.reply('What is my battery level?')
            plugged = status.reply('Am I plugged in?')
        self.assertEqual(absent['evidence']['status'], 'unknown')
        self.assertEqual(plugged['evidence']['status'], 'verified')
        self.assertEqual(plugged['evidence']['sourceId'], 'desktop.external-power')

    def test_power_profile_known_and_unavailable(self):
        with patch.object(status.subprocess, 'run') as run:
            run.return_value.stdout = 'power-saver\n'
            self.assertEqual(status.reply('Is power saver on?')['text'], 'Power saver is on.')
            run.assert_called_with(['powerprofilesctl', 'get'], capture_output=True,
                                   text=True, timeout=2, check=True)
            run.return_value.stdout = 'performance\n'
            self.assertIn('power saver is off', status.reply('Is power saver on?')['text'].lower())
            run.return_value.stdout = 'unknown-profile\n'
            self.assertIn('cannot read', status.reply('What is my power profile?')['text'])
            run.side_effect = OSError('not installed')
            self.assertIn('cannot read', status.reply('What is my power profile?')['text'])

    def test_battery_charge_charging_and_external_power(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            battery = root / 'BAT0'
            battery.mkdir()
            for name, value in {'type': 'Battery', 'present': '1', 'capacity': '73',
                                'status': 'Charging'}.items():
                (battery / name).write_text(value)
            adapter = root / 'AC'
            adapter.mkdir()
            (adapter / 'type').write_text('Mains')
            (adapter / 'online').write_text('1')
            reader = status.read_power_supplies
            with patch.object(status, 'read_power_supplies', side_effect=lambda: reader(root)):
                self.assertEqual(status.reply('How much battery do I have?')['text'], 'Battery charge is 73%.')
                self.assertEqual(status.reply('Is my battery charging?')['text'],
                                 'The battery reports that it is charging.')
                self.assertEqual(status.reply('Am I plugged in?')['text'], 'External power is connected.')
                (adapter / 'online').write_text('0')
                (battery / 'status').write_text('Discharging')
                self.assertEqual(status.reply('Am I plugged in?')['text'], 'External power is not connected.')
                self.assertEqual(status.reply('Is my battery charging?')['text'],
                                 'The battery reports that it is discharging.')
                self.assertIn('does not measure battery health', status.reply("How's my battery?")['text'])

    def test_absent_and_unknown_battery_are_distinct(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            adapter = root / 'AC'
            adapter.mkdir()
            (adapter / 'type').write_text('Mains')
            (adapter / 'online').write_text('1')
            reader = status.read_power_supplies
            with patch.object(status, 'read_power_supplies', side_effect=lambda: reader(root)):
                self.assertIn('could not find a battery', status.reply('What is my battery level?')['text'])
                self.assertEqual(status.reply('Am I plugged in?')['text'], 'External power is connected.')
            (adapter / 'type').unlink()
            with patch.object(status, 'read_power_supplies', side_effect=lambda: reader(root)):
                self.assertIn('cannot read', status.reply('What is my battery level?')['text'])
                self.assertIn('cannot confirm', status.reply('Am I plugged in?')['text'])
            with patch.object(status, 'read_power_supplies', return_value={'batteries': None, 'external': None}):
                self.assertIn('cannot read', status.reply('Is my battery charging?')['text'])

    def test_partial_power_supply_readings_do_not_claim_a_disconnection(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for name, online in (('AC', '0'), ('USB_C', None)):
                supply = root / name
                supply.mkdir()
                (supply / 'type').write_text('Mains' if name == 'AC' else 'USB')
                if online is not None:
                    (supply / 'online').write_text(online)
            self.assertIsNone(status.read_power_supplies(root)['external'])
            (root / 'USB_C' / 'online').write_text('1')
            self.assertTrue(status.read_power_supplies(root)['external'])


if __name__ == '__main__':
    unittest.main()
