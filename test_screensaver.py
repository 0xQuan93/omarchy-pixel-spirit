import json,os,subprocess,sys,tempfile,unittest
from pathlib import Path
SCRIPT=Path(__file__).parent/'setup_screensaver.py'
class ScreensaverSetupTests(unittest.TestCase):
 def fixture(self,tmp):
  env=dict(os.environ,HOME=tmp,LOGNAME='wisp_test',USER='wisp_test')
  target=Path(tmp)/'.config/omarchy/plugins/wisp_test.idle';target.mkdir(parents=True)
  original='runProcess("label", "false || omarchy-launch-screensaver")'
  (target/'Service.qml').write_text(original)
  (target/'.wisp-screensaver.json').write_text(json.dumps({'original':original,'modified':original}))
  return env,target,original
 def test_setup_respects_off_and_restores(self):
  with tempfile.TemporaryDirectory() as tmp:
   env,target,original=self.fixture(tmp)
   subprocess.run([sys.executable,str(SCRIPT)],env=env,check=True,capture_output=True)
   text=(target/'Service.qml').read_text()
   command=json.loads(text.removeprefix('runProcess("label", ').removesuffix(')'))
   for status,expected in [(0,''),(1,'DREAM')]:
    stub='omarchy-toggle-enabled(){ return '+str(status)+'; }; quickshell(){ echo DREAM; }; '+command
    result=subprocess.run(['bash','-c',stub],env=env,check=True,capture_output=True,text=True)
    self.assertEqual(result.stdout.strip(),expected)
   subprocess.run([sys.executable,str(SCRIPT),'--remove'],env=env,check=True,capture_output=True)
   self.assertEqual((target/'Service.qml').read_text(),original)
 def test_subsequent_user_edits_not_overwritten(self):
  with tempfile.TemporaryDirectory() as tmp:
   env,target,original=self.fixture(tmp)
   changed=original+'\n// user customization';(target/'Service.qml').write_text(changed)
   for args in [[],['--remove']]:
    result=subprocess.run([sys.executable,str(SCRIPT)]+args,env=env,capture_output=True)
    self.assertNotEqual(result.returncode,0)
    self.assertEqual((target/'Service.qml').read_text(),changed)
if __name__=='__main__':unittest.main()
