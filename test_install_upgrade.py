"""Exercise staged development installs in a temporary home."""
import contextlib,io,json,os,runpy,subprocess,sys,tempfile,unittest
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
   with patch.object(Path,'home',return_value=home),patch.object(sys,'argv',['install.py']),patch('shutil.which',return_value='/usr/bin/omarchy'),patch('subprocess.run') as invoke,contextlib.redirect_stdout(io.StringIO()):
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
   self.assertTrue(all(c.args[0][:3]==['omarchy','plugin','validate'] for c in invoke.call_args_list))
   self.assertTrue(all(Path(c.args[0][-1]).parent==config for c in invoke.call_args_list))
   for name,data in protected.items():self.assertEqual(json.loads((state/name).read_text()),data)

 def test_private_overlay_survives_a_complete_generation_swap(self):
  with tempfile.TemporaryDirectory() as tmp:
   home=Path(tmp);config=home/'.config/omarchy';config.mkdir(parents=True)
   shell=config/'shell.json';shell.write_text(json.dumps({'bar':{'layout':{'left':[]}},'plugins':[]}))
   with patch.object(Path,'home',return_value=home),patch.object(sys,'argv',['install.py']),patch('shutil.which',return_value='/usr/bin/omarchy'),patch('subprocess.run'),contextlib.redirect_stdout(io.StringIO()):
    runpy.run_path(str(ROOT/'install.py'),run_name='__main__')
    target=config/'plugins/oxquan.pixel-spirit'
    (target/'personal_adapter.py').write_text('VALUE = 42\n')
    (target/'brain.py').write_text('PUBLIC_VERSION = "old"\n')
    runpy.run_path(str(ROOT/'install.py'),run_name='__main__')
   self.assertEqual((target/'personal_adapter.py').read_text(),'VALUE = 42\n')
   self.assertEqual((target/'brain.py').read_bytes(),(ROOT/'plugin/brain.py').read_bytes())
   backups=list((config/'.wisp-install-backups').glob('oxquan.pixel-spirit-*'))
   self.assertEqual(len(backups),1)
   self.assertEqual((backups[0]/'brain.py').read_text(),'PUBLIC_VERSION = "old"\n')
   self.assertFalse(any(config.glob('.wisp-stage-*')))

 def test_managed_local_overlay_cannot_be_silently_replaced(self):
  with tempfile.TemporaryDirectory() as tmp:
   home=Path(tmp);config=home/'.config/omarchy';config.mkdir(parents=True)
   shell=config/'shell.json';shell.write_text(json.dumps({'bar':{'layout':{'left':[]}},'plugins':[]}))
   with patch.object(Path,'home',return_value=home),patch.object(sys,'argv',['install.py']),patch('shutil.which',return_value='/usr/bin/omarchy'),patch('subprocess.run'),contextlib.redirect_stdout(io.StringIO()):
    runpy.run_path(str(ROOT/'install.py'),run_name='__main__')
   target=config/'plugins/oxquan.pixel-spirit'
   marker=target/'.wisp-managed-overlay.json';marker.write_text('{"owner":"local"}')
   previous=(target/'brain.py').read_bytes();old_shell=shell.read_bytes()
   with patch.object(Path,'home',return_value=home),patch.object(sys,'argv',['install.py']),patch('shutil.which',return_value='/usr/bin/omarchy'),patch('subprocess.run'),contextlib.redirect_stdout(io.StringIO()):
    with self.assertRaisesRegex(ValueError,'managed local overlay'):
     runpy.run_path(str(ROOT/'install.py'),run_name='__main__')
   self.assertEqual((target/'brain.py').read_bytes(),previous)
   self.assertEqual(shell.read_bytes(),old_shell)
   self.assertEqual(marker.read_text(),'{"owner":"local"}')

 def test_validator_failure_preserves_live_generation_and_configuration(self):
  with tempfile.TemporaryDirectory() as tmp:
   home=Path(tmp);config=home/'.config/omarchy';config.mkdir(parents=True)
   shell=config/'shell.json';shell.write_text(json.dumps({'bar':{'layout':{'left':[]}},'plugins':[]}))
   with patch.object(Path,'home',return_value=home),patch.object(sys,'argv',['install.py']),patch('shutil.which',return_value='/usr/bin/omarchy'),patch('subprocess.run'),contextlib.redirect_stdout(io.StringIO()):
    runpy.run_path(str(ROOT/'install.py'),run_name='__main__')
   target=config/'plugins/oxquan.pixel-spirit';previous=(target/'brain.py').read_bytes();old_shell=shell.read_bytes()
   with patch.object(Path,'home',return_value=home),patch.object(sys,'argv',['install.py']),patch('shutil.which',return_value='/usr/bin/omarchy'),patch('subprocess.run',side_effect=subprocess.CalledProcessError(1,['omarchy','plugin','validate'])),contextlib.redirect_stdout(io.StringIO()):
    with self.assertRaises(subprocess.CalledProcessError):runpy.run_path(str(ROOT/'install.py'),run_name='__main__')
   self.assertEqual((target/'brain.py').read_bytes(),previous)
   self.assertEqual(shell.read_bytes(),old_shell)
   self.assertFalse(any(config.glob('.wisp-stage-*')))

 def test_switch_failure_restores_previous_generation_and_configuration(self):
  with tempfile.TemporaryDirectory() as tmp:
   home=Path(tmp);config=home/'.config/omarchy';config.mkdir(parents=True)
   shell=config/'shell.json';shell.write_text(json.dumps({'bar':{'layout':{'left':[]}},'plugins':[]}))
   with patch.object(Path,'home',return_value=home),patch.object(sys,'argv',['install.py']),patch('shutil.which',return_value='/usr/bin/omarchy'),patch('subprocess.run'),contextlib.redirect_stdout(io.StringIO()):
    runpy.run_path(str(ROOT/'install.py'),run_name='__main__')
   target=config/'plugins/oxquan.pixel-spirit';(target/'personal_adapter.py').write_text('VALUE = 42\n')
   old_shell=shell.read_bytes();replace=os.replace;failed=False
   def fail_switch(src,dst):
    nonlocal failed
    if not failed and str(src).startswith(str(config/'.wisp-stage-')) and Path(dst)==target:
     failed=True;raise OSError('simulated switch failure')
    return replace(src,dst)
   with patch.object(Path,'home',return_value=home),patch.object(sys,'argv',['install.py']),patch('shutil.which',return_value='/usr/bin/omarchy'),patch('subprocess.run'),patch('os.replace',side_effect=fail_switch),contextlib.redirect_stdout(io.StringIO()):
    with self.assertRaises(OSError):runpy.run_path(str(ROOT/'install.py'),run_name='__main__')
   self.assertTrue(failed)
   self.assertEqual((target/'personal_adapter.py').read_text(),'VALUE = 42\n')
   self.assertEqual(shell.read_bytes(),old_shell)
   self.assertFalse(any(config.glob('.wisp-stage-*')))

 def test_shell_write_failure_restores_previous_generation(self):
  with tempfile.TemporaryDirectory() as tmp:
   home=Path(tmp);config=home/'.config/omarchy';config.mkdir(parents=True)
   shell=config/'shell.json';shell.write_text(json.dumps({'bar':{'layout':{'left':[]}},'plugins':[]}))
   with patch.object(Path,'home',return_value=home),patch.object(sys,'argv',['install.py']),patch('shutil.which',return_value='/usr/bin/omarchy'),patch('subprocess.run'),contextlib.redirect_stdout(io.StringIO()):
    runpy.run_path(str(ROOT/'install.py'),run_name='__main__')
   target=config/'plugins/oxquan.pixel-spirit';(target/'personal_adapter.py').write_text('VALUE = 42\n')
   shell.write_text(json.dumps(json.loads(shell.read_text()),separators=(',',':')))
   old_shell=shell.read_bytes();replace=os.replace;failed=False
   def fail_shell(src,dst):
    nonlocal failed
    if not failed and Path(dst)==shell:
     failed=True;raise OSError('simulated shell write failure')
    return replace(src,dst)
   with patch.object(Path,'home',return_value=home),patch.object(sys,'argv',['install.py']),patch('shutil.which',return_value='/usr/bin/omarchy'),patch('subprocess.run'),patch('os.replace',side_effect=fail_shell),contextlib.redirect_stdout(io.StringIO()):
    with self.assertRaises(OSError):runpy.run_path(str(ROOT/'install.py'),run_name='__main__')
   self.assertTrue(failed)
   self.assertEqual((target/'personal_adapter.py').read_text(),'VALUE = 42\n')
   self.assertEqual(shell.read_bytes(),old_shell)

 def test_symlink_in_existing_plugin_cannot_escape_staging(self):
  with tempfile.TemporaryDirectory() as tmp:
   home=Path(tmp);config=home/'.config/omarchy';config.mkdir(parents=True)
   shell=config/'shell.json';shell.write_text(json.dumps({'bar':{'layout':{'left':[]}},'plugins':[]}))
   with patch.object(Path,'home',return_value=home),patch.object(sys,'argv',['install.py']),patch('shutil.which',return_value='/usr/bin/omarchy'),patch('subprocess.run'),contextlib.redirect_stdout(io.StringIO()):
    runpy.run_path(str(ROOT/'install.py'),run_name='__main__')
   target=config/'plugins/oxquan.pixel-spirit';outside=home/'outside';outside.write_text('protected')
   (target/'manifest.json').unlink();(target/'manifest.json').symlink_to(outside)
   old_shell=shell.read_bytes()
   with patch.object(Path,'home',return_value=home),patch.object(sys,'argv',['install.py']),patch('shutil.which',return_value='/usr/bin/omarchy'),patch('subprocess.run'),contextlib.redirect_stdout(io.StringIO()):
    with self.assertRaisesRegex(ValueError,'symlink'):runpy.run_path(str(ROOT/'install.py'),run_name='__main__')
   self.assertEqual(outside.read_text(),'protected')
   self.assertTrue((target/'manifest.json').is_symlink())
   self.assertEqual(shell.read_bytes(),old_shell)
if __name__=='__main__':unittest.main()
