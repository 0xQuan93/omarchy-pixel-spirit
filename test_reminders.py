import subprocess
import unittest
import tempfile
from pathlib import Path
from unittest.mock import patch
from test_brain import b
import reminders as r


class ReminderTests(unittest.TestCase):
    def test_duration_and_message_validation_precede_execution(self):
        with patch.object(r, 'run') as run:
            for minutes in ('0','1441','-1','1.5','5;echo x','99999'):
                with self.assertRaises(ValueError):r.create(minutes,'hello')
            for message in ('x'*241,'line\nline','bad\x00'):
                with self.assertRaises(ValueError):r.create('5',message)
            run.assert_not_called()

    def test_literal_message_passed_as_single_argument(self):
        message='Check $(something) and "quotes"; nothing executes'
        with patch.object(r, 'run') as run:
            r.create('05',message)
            run.assert_called_once_with(['omarchy','reminder','5',message])

    def test_cancel_refuses_unrelated_or_finished_unit(self):
        with patch.object(r, 'run') as run:
            with self.assertRaises(ValueError):r.cancel('quan-dashboard')
            run.assert_not_called()
        with patch.object(r,'upcoming',return_value={'reminders':[]}), patch.object(r,'run') as run:
            with self.assertRaises(ValueError):r.cancel('omarchy-reminder-5m-123')
            run.assert_not_called()

    def test_explicit_chat_request_creates_draft_without_execution(self):
        with patch.object(r,'run') as run, patch.object(b,'run') as brain_run:
            draft=b.chat('Remind me in 2 hours to check the oven')['reminderDraft']
            self.assertEqual(draft,{'minutes':'120','message':'check the oven'})
            self.assertEqual(r.parse_request('set a timer for 25 minutes')['minutes'],'25')
            for text in ('do not remind me in 5 minutes to go','if I say remind me in 5 minutes to go','"remind me in 5 minutes to go"'):
                self.assertIsNone(r.parse_request(text))
            run.assert_not_called();brain_run.assert_not_called()

    def test_cancel_stops_only_the_pending_timer_and_removes_its_message(self):
        unit='omarchy-reminder-5m-123'
        with tempfile.TemporaryDirectory() as tmp, patch.dict('os.environ',{'XDG_RUNTIME_DIR':tmp}), \
             patch.object(r,'upcoming',return_value={'reminders':[{'unit':unit}]}), patch.object(r,'run') as run:
            folder=Path(tmp)/'omarchy-reminders';folder.mkdir()
            message=folder/(unit+'.message');message.write_text('test')
            r.cancel(unit)
            self.assertEqual(run.call_args_list[0].args[0],['systemctl','--user','stop',unit+'.timer'])
            self.assertFalse(message.exists())

    def test_native_failure_is_reported_without_message_content(self):
        with patch.object(r.subprocess,'run',side_effect=subprocess.CalledProcessError(1,['secret'])):
            with self.assertRaisesRegex(ValueError,'could not complete') as caught:r.create('1','secret')
            self.assertNotIn('secret',str(caught.exception))


if __name__=='__main__':unittest.main()
