#!/usr/bin/env python3
"""Install or remove Wisp without touching packaged Omarchy files."""
import datetime, json, os, shutil, stat, sys, subprocess, tempfile
from pathlib import Path
source=Path(__file__).resolve().parent
home=Path.home()
plugin=home/'.config/omarchy/plugins/oxquan.pixel-spirit'
shell=home/'.config/omarchy/shell.json'
stamp=datetime.datetime.now().strftime('%Y%m%d-%H%M%S')
def write(path,data):
 path.parent.mkdir(parents=True,exist_ok=True)
 if path.exists():
  if path.read_bytes()==data:return
  # Reserve each backup exclusively: repeated updates may share a timestamp.
  backup=path.with_name(path.name+'.before-wisp-'+stamp)
  suffix=0
  while True:
   try:
    backup_fd=os.open(backup,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
    break
   except FileExistsError:
    suffix+=1
    backup=path.with_name(path.name+'.before-wisp-'+stamp+'-'+str(suffix))
  try:
   with os.fdopen(backup_fd,'wb') as stream, path.open('rb') as original:
    shutil.copyfileobj(original,stream)
    stream.flush()
    os.fsync(stream.fileno())
   shutil.copystat(path,backup)
  except BaseException:
   backup.unlink(missing_ok=True)
   raise
 # Follow an existing configuration symlink without replacing the link itself.
 destination=path.resolve() if path.is_symlink() else path
 mode=stat.S_IMODE(destination.stat().st_mode) if destination.exists() else None
 fd,temporary=tempfile.mkstemp(prefix='.'+destination.name+'.wisp-',dir=destination.parent)
 try:
  with os.fdopen(fd,'wb') as stream:
   if mode is not None:os.fchmod(stream.fileno(),mode)
   stream.write(data)
   stream.flush()
   os.fsync(stream.fileno())
  os.replace(temporary,destination)
 finally:
  Path(temporary).unlink(missing_ok=True)
if '--remove' in sys.argv:
 subprocess.run([sys.executable,str(source/'setup_screensaver.py'),'--remove'],check=True)
data=json.loads(shell.read_text())
for section in data['bar']['layout'].values(): section[:]=[p for p in section if p.get('id')!='oxquan.pixel-spirit']
data['plugins']=[p for p in data.get('plugins',[]) if p.get('id')!='oxquan.pixel-spirit']
if '--remove' not in sys.argv:
 for path in (source/'plugin').iterdir():
  if path.is_file():write(plugin/path.name,path.read_bytes())
 write(plugin/'setup_screensaver.py',(source/'setup_screensaver.py').read_bytes())
 write(plugin/'tools/fetch_voice_model.py',(source/'tools/fetch_voice_model.py').read_bytes())
 local_manifest=json.loads((source/'manifest.json').read_text())
 local_manifest['entryPoints']={key:value.removeprefix('plugin/') for key,value in local_manifest['entryPoints'].items()}
 local_manifest.pop('icon',None)
 write(plugin/'manifest.json',(json.dumps(local_manifest,indent=2)+'\n').encode())
 data['plugins'].append({'id':'oxquan.pixel-spirit'})
 data['bar']['layout']['left'].append({'id':'oxquan.pixel-spirit'})
 model=source/'models/ggml-tiny.en.bin'
 if model.exists():
  target=home/'.local/share/pixel-spirit/ggml-tiny.en.bin'
  target.parent.mkdir(parents=True,exist_ok=True)
  if not target.exists():shutil.copy2(model,target)
if '--remove' not in sys.argv:
 subprocess.run([sys.executable,'-B',str(plugin/'command_bank.py'),'scan'],check=True)
write(shell,(json.dumps(data,indent=2)+'\n').encode())
disabled=data.get('disabledPlugins',[])
explicitly_disabled=isinstance(disabled,list) and 'oxquan.pixel-spirit' in disabled
result='removed from shell configuration' if '--remove' in sys.argv else 'installed but disabled' if explicitly_disabled else 'installed'
print('Wisp '+result+'. Config backups: .before-wisp-'+stamp)
if '--remove' not in sys.argv and explicitly_disabled:
 print('Your disabled setting was preserved. To enable Wisp, open Omarchy menu > Setup > Plugins > Enable Plugin and choose Wisp (oxquan.pixel-spirit).')
