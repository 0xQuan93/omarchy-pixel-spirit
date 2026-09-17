"""Small fixed readbacks. No user strings become command arguments."""
import re
import subprocess

def verify(action, invoke=subprocess.run):
    if action in {'mute','unmute','mic_mute','mic_unmute'}:
        target='@DEFAULT_AUDIO_SOURCE@' if action.startswith('mic_') else '@DEFAULT_AUDIO_SINK@'
        result=invoke(['wpctl','get-volume',target],capture_output=True,text=True,timeout=2,check=True)
        match=re.fullmatch(r'Volume:\s+\d+(?:\.\d+)?(?:\s+(\[MUTED\]))?\s*',result.stdout)
        return bool(match) and bool(match[1]) == (action in {'mute','mic_mute'})
    if action in {'power_saver','power_balanced'}:
        result=invoke(['powerprofilesctl','get'],capture_output=True,text=True,timeout=2,check=True)
        return result.stdout.strip() == ('power-saver' if action=='power_saver' else 'balanced')
    return False
