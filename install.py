#!/usr/bin/env python3
"""Install or remove Wisp without touching packaged Omarchy files."""
import datetime, json, shutil, sys, subprocess
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
  shutil.copy2(path,path.with_name(path.name+'.before-wisp-'+stamp))
 path.write_bytes(data)
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
 data['plugins'].append({'id':'oxquan.pixel-spirit'})
 data['bar']['layout']['left'].append({'id':'oxquan.pixel-spirit'})
 model=source/'models/ggml-tiny.en.bin'
 if model.exists():
  target=home/'.local/share/pixel-spirit/ggml-tiny.en.bin'
  target.parent.mkdir(parents=True,exist_ok=True)
  if not target.exists():shutil.copy2(model,target)
write(shell,(json.dumps(data,indent=2)+'\n').encode())
print('Wisp '+('removed from shell configuration' if '--remove' in sys.argv else 'installed')+'. Config backups: .before-wisp-'+stamp)
