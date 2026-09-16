import sys
from pathlib import Path
import unittest
from unittest.mock import patch
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
  with patch.object(controls.shutil,'which',return_value='/tool'),patch.object(controls.subprocess,'run') as run:
   controls.execute('param:volume:25')
   run.assert_called_once_with(['wpctl','set-volume','-l','1','@DEFAULT_AUDIO_SINK@','25%'],capture_output=True,text=True,timeout=12,check=True)
if __name__=='__main__':unittest.main()
