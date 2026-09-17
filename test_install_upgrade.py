"""Exercise the real installer in a temporary home with an inert scanner."""
import contextlib,io,json,runpy,sys,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
ROOT=Path(__file__).resolve().parent
class InstallUpgrade(unittest.TestCase):
 def test_clean_install_and_repeat_preserve_state_and_other_plugins(self):
  with tempfile.TemporaryDirectory() as tmp:
   home=Path(tmp);config=home/'.config/omarchy';config.mkdir(parents=True)
   (config/'shell.json').write_text(json.dumps({'bar':{'layout':{'left':[{'id':'example.clock'}],'right':[]}},'plugins':[{'id':'example.clock'}],'userFlag':True}))
   state=home/'.local/state/pixel-spirit';state.mkdir(parents=True)
   protected={'identity.json':{'name':'Saved companion'},'growth.json':{'xp':123},'room.json':{'bond':17},'personal-command-bank.json':[{'phrase':'my private alias'}]}
   for name,data in protected.items():(state/name).write_text(json.dumps(data))
   with patch.object(Path,'home',return_value=home),patch.object(sys,'argv',['install.py']),patch('subprocess.run') as invoke,contextlib.redirect_stdout(io.StringIO()):
    runpy.run_path(str(ROOT/'install.py'),run_name='__main__')
    runpy.run_path(str(ROOT/'install.py'),run_name='__main__')
   target=config/'plugins/oxquan.pixel-spirit'
   for name in ['capability_registry.py','capability_specs.py','plan_edits.py','plan_extensions.py','plan_runtime.py','SetupPanel.qml','onboarding.py']:
    self.assertEqual((target/name).read_bytes(),(ROOT/'plugin'/name).read_bytes())
   manifest=json.loads((target/'manifest.json').read_text())
   self.assertEqual(manifest['version'],json.loads((ROOT/'manifest.json').read_text())['version']);self.assertEqual(manifest['entryPoints']['service'],'Desktop.qml')
   shell=json.loads((config/'shell.json').read_text());self.assertTrue(shell['userFlag'])
   self.assertEqual([p['id'] for p in shell['plugins']],['example.clock','oxquan.pixel-spirit'])
   self.assertEqual([p['id'] for p in shell['bar']['layout']['left']],['example.clock','oxquan.pixel-spirit'])
   self.assertEqual(invoke.call_count,2)
   self.assertTrue(all(c.args[0][-2:]==[str(target/'command_bank.py'),'scan'] for c in invoke.call_args_list))
   for name,data in protected.items():self.assertEqual(json.loads((state/name).read_text()),data)
if __name__=='__main__':unittest.main()
