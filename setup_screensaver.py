#!/usr/bin/env python3
"""Opt-in screensaver integration: clone Omarchy idle, change only its launcher."""
import getpass,json,shutil,subprocess,sys,time
from pathlib import Path
home=Path.home();target=home/'.config/omarchy/plugins'/f'{getpass.getuser()}.idle'
marker=target/'.wisp-screensaver.json'
if '--remove' in sys.argv:
 if marker.exists():
  info=json.loads(marker.read_text());service=target/'Service.qml'
  if service.read_text()==info['modified']:service.write_text(info['original']);marker.unlink();print('Restored the cloned idle service launcher. The clone remains installed.')
  else:raise SystemExit('Idle clone changed since integration; see .wisp-screensaver.json before restoring.')
 else:print('No Wisp idle integration to remove.')
 sys.exit()
if target.exists() and not marker.exists():raise SystemExit('An existing idle clone needs a manual merge; no files changed.')
if not target.exists():subprocess.run(['omarchy','plugin','clone','omarchy.idle'],check=True)
service=target/'Service.qml';original=json.loads(marker.read_text())['original'] if marker.exists() else service.read_text()
needle='|| omarchy-launch-screensaver'
if original.count(needle)!=1:raise SystemExit('Idle launcher contract changed. No replacement made.')
# The variable is expanded by bash at runtime; no username or checkout path is baked in.
entry='plugin/Screensaver.qml' if (home/'.config/omarchy/plugins/oxquan.pixel-spirit/plugin/Screensaver.qml').exists() else 'Screensaver.qml'
replacement='|| quickshell -n -d -p \\"$HOME/.config/omarchy/plugins/oxquan.pixel-spirit/'+entry+'\\"'
modified=original.replace(needle,replacement)
if not marker.exists():shutil.copy2(service,target/('Service.qml.before-wisp-'+str(int(time.time()))))
service.write_text(modified)
marker.write_text(json.dumps({'original':original,'modified':modified},indent=2))
print('Enabled the native Wisp dream room through the user-owned idle clone. Lock timing is unchanged.')
