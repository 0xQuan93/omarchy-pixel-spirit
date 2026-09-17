import sys
from pathlib import Path
import unittest
from unittest.mock import patch, call
from types import SimpleNamespace
import subprocess
sys.path.insert(0,str(Path(__file__).parent/'plugin'))
import parameter_commands as controls

class PercentageControls(unittest.TestCase):
 def test_every_valid_percentage_is_typed_and_bounded(self):
  for kind,low in [('volume',0),('brightness',1)]:
   for value in range(low,101):
    p=controls.proposal(f'Please set my {kind} to {value} percent.')
    self.assertEqual(p['action'],f'param:{kind}:{value}')
    self.assertEqual(controls.resolve(p['action'])[-1],f'{value}%')
 def test_invalid_percentage_is_actionable_without_model(self):
  for request in ['set volume to 101%','set brightness to 0 percent','set brightness to 999%']:
   self.assertEqual(controls.proposal(request)['action'],'')
 def test_unsafe_and_ambiguous_requests_do_not_match(self):
  for request in ['do not set volume to 50%', 'set volume to 50% tomorrow',
                  'set volume to 50% and open files','set volume to -20%',
                  'set volume to 20.5%', 'set app volume to 10%',
                  '"set volume to 50%"', 'if I ask set volume to 50%']:
   self.assertIsNone(controls.proposal(request))
 def test_untrusted_action_ids_never_run(self):
  with patch.object(controls.subprocess,'run') as run:
   for action in ['param:volume:101','param:brightness:0','param:volume:01',
                  'param:volume:50;bad','param:arbitrary:50','param:volume:-2']:
    with self.assertRaises(ValueError):controls.execute(action)
   run.assert_not_called()
 def test_execution_fixed_argv_no_shell(self):
  with patch.object(controls.shutil,'which',return_value='/tool'),patch.object(controls.subprocess,'run',return_value=SimpleNamespace(stdout='Volume: 0.25')) as run:
   reply=controls.execute('param:volume:25')
   self.assertEqual(run.call_args_list,[
    call(['wpctl','set-volume','-l','1','@DEFAULT_AUDIO_SINK@','25%'],capture_output=True,text=True,timeout=12,check=True),
    call(['wpctl','get-volume','@DEFAULT_AUDIO_SINK@'],capture_output=True,text=True,timeout=2,check=True)])
   self.assertTrue(reply['verified']);self.assertEqual(reply['status'],'verified')
 def test_volume_readback_tolerance_and_muted_level(self):
  for value in ('0.245','0.255','0.25 [MUTED]'):
   with self.subTest(value=value),patch.object(controls.shutil,'which',return_value='/tool'),patch.object(controls.subprocess,'run',return_value=SimpleNamespace(stdout='Volume: '+value)):
    self.assertTrue(controls.execute('param:volume:25')['verified'])
 def test_volume_mismatch_and_malformed_readback_fail(self):
  for output in ('Volume: 0.2449','Volume: 0.2551','Volume: 0.90','ok','Volume: nan','Volume: 0.25 unexpected'):
   with self.subTest(output=output),patch.object(controls.shutil,'which',return_value='/tool'),patch.object(controls.subprocess,'run',return_value=SimpleNamespace(stdout=output)):
    reply=controls.execute('param:volume:25')
    self.assertFalse(reply['ok']);self.assertFalse(reply['verified']);self.assertEqual(reply['status'],'failed')
 def test_missing_tool_set_failure_and_readback_failure_are_truthful(self):
  with patch.object(controls.shutil,'which',return_value=None),patch.object(controls.subprocess,'run') as run:
   self.assertFalse(controls.execute('param:volume:25')['ok']);run.assert_not_called()
  for effects in ([OSError('missing')], [subprocess.TimeoutExpired('wpctl',12)],
                  [SimpleNamespace(stdout=''),subprocess.TimeoutExpired('wpctl',2)],
                  [SimpleNamespace(stdout=''),subprocess.CalledProcessError(1,'wpctl')]):
   with patch.object(controls.shutil,'which',return_value='/tool'),patch.object(controls.subprocess,'run',side_effect=effects):
    reply=controls.execute('param:volume:25')
    self.assertFalse(reply['ok']);self.assertEqual(reply['status'],'failed')
 def test_brightness_receipt_reports_process_completion_only(self):
  with patch.object(controls.shutil,'which',return_value='/tool'),patch.object(controls.subprocess,'run') as run:
   reply=controls.execute('param:brightness:45')
   run.assert_called_once_with(['omarchy','brightness','display','45%'],capture_output=True,text=True,timeout=12,check=True)
   self.assertEqual(reply['text'],'Brightness command finished (45%).')
   self.assertEqual(reply['verification'],'process');self.assertEqual(reply['status'],'completed');self.assertNotIn('verified',reply)
 def test_catalogue_reports_sources_verification_and_missing_tools(self):
  with patch.object(controls.shutil,'which',return_value=None):entries=controls.catalogue()
  self.assertEqual([e['verification'] for e in entries],['state','process'])
  for entry in entries:
   self.assertFalse(entry['available']);self.assertTrue(entry['availabilityReason']);self.assertTrue(entry['planSafe']);self.assertTrue(entry['sourceLabel'])
if __name__=='__main__':unittest.main()
