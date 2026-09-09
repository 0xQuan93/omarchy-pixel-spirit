#!/usr/bin/env python3
"""Explicit optional download. No model is downloaded by enabling the plugin."""
import hashlib,os,tempfile,urllib.request
from pathlib import Path
URL='https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-tiny.en.bin'
SHA256='921e4cf8686fdd993dcd081a5da5b6c365bfde1162e72b08d75ac75289920b1f'
target=Path(os.environ.get('XDG_DATA_HOME',str(Path.home()/'.local/share')))/'pixel-spirit/ggml-tiny.en.bin'
target.parent.mkdir(parents=True,exist_ok=True)
if target.exists():
 if hashlib.sha256(target.read_bytes()).hexdigest()==SHA256:print('Verified model already installed.');raise SystemExit(0)
 raise SystemExit('An existing model has a different checksum. Move it aside deliberately before downloading.')
fd,tmp=tempfile.mkstemp(dir=target.parent)
try:
 digest=hashlib.sha256();size=0
 with os.fdopen(fd,'wb') as out,urllib.request.urlopen(URL,timeout=120) as response:
  while chunk:=response.read(1024*1024):
   size+=len(chunk)
   if size>90*1024*1024:raise ValueError('Unexpected model size')
   digest.update(chunk);out.write(chunk)
 if digest.hexdigest()!=SHA256:raise ValueError('Model checksum mismatch; download discarded')
 os.replace(tmp,target);print('Installed verified tiny.en speech model:',target)
finally:
 if os.path.exists(tmp):os.unlink(tmp)
