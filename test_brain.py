import importlib.util,json,tempfile,unittest,struct,wave
from pathlib import Path
from unittest.mock import patch
import sys
sys.path.insert(0,str(Path(__file__).parent/"plugin"))
spec=importlib.util.spec_from_file_location('brain',Path(__file__).parent/'plugin/brain.py')
b=importlib.util.module_from_spec(spec);spec.loader.exec_module(b)
class BrokerTests(unittest.TestCase):
 def test_untrusted_actions_never_execute(self):
  with patch.object(b,'run') as run:
   for action in ['rm -rf ~','browser; touch /tmp/pwn','shutdown','',None]:
    with self.assertRaises(ValueError):b.execute(action)
   run.assert_not_called()
 def test_action_uses_fixed_argv_and_reports_failure(self):
  with patch.object(b,'run') as run, patch.object(b.shutil,'which',return_value='/test/tool'):
   b.execute('volume_down');run.assert_called_once_with(b.ACTIONS['volume_down'])
  with patch.object(b,'run',side_effect=RuntimeError('failed')), patch.object(b.shutil,'which',return_value='/test/tool'):
   with self.assertRaises(RuntimeError):b.execute('volume_down')
 def test_chat_is_proposal_and_battery_policy(self):
  response={'message':{'content':json.dumps({'text':'I can mute it.','emote':'working','action':'mute'})}}
  with tempfile.TemporaryDirectory() as t, patch.object(b,'BASE',Path(t)), patch.object(b,'context',return_value={}), patch('identity.profile',return_value={'name':'Test','model':'qwen3.5:4b'}), patch.object(b.urllib.request,'urlopen') as url, patch.object(b.shutil,'which',return_value='/test/tool'):
   url.return_value.__enter__.return_value.read.return_value=json.dumps(response).encode()
   with patch.object(b,'execute') as execute:
    result=b.chat('Would you help silence this machine?',True); execute.assert_not_called()
   payload=json.loads(url.call_args.args[0].data)
   self.assertEqual(payload['keep_alive'],0);self.assertEqual(payload['options']['num_thread'],2)
   self.assertEqual(result['action'],'mute');self.assertIn('Tap Run',result['text']);self.assertEqual(len(b.read('history.json',[])),2)
 def test_direct_commands_are_anchored(self):
  self.assertEqual(b.direct_action('Please turn the volume down.'),'volume_down')
  self.assertEqual(b.direct_action('pause music'),'pause_music')
  self.assertEqual(b.ACTIONS['mute'][-1],'1')
  for text in ['do not turn the volume down', 'if I ask, turn the volume down', 'say "volume down"', 'volume down; rm ~']:
   self.assertEqual(b.direct_action(text),'')
 def test_state_private_and_roundtrip(self):
  with tempfile.TemporaryDirectory() as t,patch.object(b,'BASE',Path(t)):
   b.save('position.json',{'x':25});self.assertEqual(b.read('position.json',{}),{'x':25})
   self.assertEqual((Path(t)/'position.json').stat().st_mode&0o777,0o600)
class RecordingTests(unittest.TestCase):
 def make_wav(self,path,frames=16000,value=1000):
  with wave.open(str(path),'wb') as w:
   w.setparams((1,2,16000,0,'NONE','not compressed'))
   w.writeframes(struct.pack('<h',value)*frames)
 def test_complete_capture_with_pipewire_exit_one(self):
  with tempfile.TemporaryDirectory() as tmp:
   p=Path(tmp)/'audio.wav';self.make_wav(p)
   self.assertEqual(b.validate_recording(p,1,16000)['seconds'],1)
 def test_partial_missing_and_failed_captures_rejected(self):
  with tempfile.TemporaryDirectory() as tmp:
   p=Path(tmp)/'audio.wav'
   with self.assertRaises(ValueError):b.validate_recording(p,1,16000)
   self.make_wav(p,8000)
   with self.assertRaises(ValueError):b.validate_recording(p,1,16000)
   self.make_wav(p)
   with self.assertRaises(ValueError):b.validate_recording(p,2,16000)
 def test_silent_input_is_actionable(self):
  with tempfile.TemporaryDirectory() as tmp:
   p=Path(tmp)/'audio.wav';self.make_wav(p,value=0)
   with self.assertRaisesRegex(ValueError,'silent or too quiet'):b.validate_recording(p,1,16000)
if __name__=='__main__':unittest.main()
