"""User-owned companion identity. No hardware identifiers or inferred personal traits."""
import fcntl, re, secrets, time
from pathlib import Path
from growth import STATE, WORK, VAULT, get, put
CLASSES={'Maker':'Forgewright','Artist':'Prismweaver','Musician':'Resonant','Archivist':'Lorekeeper'}
FORMS={'Maker':['Rivet','Circuit cub','Forgewright','Iron aurora'],'Artist':['Dewdrop','Petal sprite','Prismweaver','Aurora manta'],'Musician':['Pulse','Echo fox','Resonant','Celestial ray'],'Archivist':['Mote','Paper owl','Lorekeeper','Astral owl']}
def clean_name(value):
 if not isinstance(value,str):raise ValueError('The name must be text.')
 value=' '.join(value.split())
 if not re.fullmatch(r'[^\W_][\w -]{0,23}',value,re.UNICODE):raise ValueError('Use 1–24 letters, numbers, spaces or hyphens, starting with a letter or number.')
 return value

def profile(command='status',value=''):
 STATE.mkdir(parents=True,exist_ok=True,mode=0o700)
 with (STATE/'identity.lock').open('w') as lock:
  fcntl.flock(lock,fcntl.LOCK_EX)
  p=get(STATE/'identity.json',{})
  if not p:
   # Only explicit interest words from an existing optional shared user profile.
   interests=[]
   try:
    with (VAULT/'USER.md').open() as f:words=f.read(3000).lower()
    if 'music' in words:interests.append('Musician')
    if re.search(r'\b(art|design|drawing)\b',words):interests.append('Artist')
   except OSError:pass
   p={'name':'Wisp','seed':secrets.randbelow(65536),'created':time.time(),'class':'Auto','interests':interests,'device':'portable' if list(Path('/sys/class/power_supply').glob('BAT*')) else 'stationary','model':'qwen3.5:4b'}
  if command=='rename':p['name']=clean_name(value)
  elif command=='class':
   if value not in ['Auto']+list(CLASSES):raise ValueError('Unknown evolution class')
   p['class']=value
  elif command=='interest':
   if value not in CLASSES:raise ValueError('Unknown influence')
   p['interests']=([i for i in p['interests'] if i!=value] if value in p['interests'] else p['interests']+[value])
  elif command=='model':
   if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.:/-]{0,99}',value):raise ValueError('Enter a local Ollama model name.')
   p['model']=value
  elif command!='status':raise ValueError('Unknown identity setting')
  put(STATE/'identity.json',p)
  return p

def appearance(p,traits):
 weights=traits.copy()
 for interest in p['interests']:weights[interest]=weights.get(interest,0)+4
 family=p['class'] if p['class'] in CLASSES else max(weights,key=weights.get) if weights else 'Maker'
 return {'family':family,'className':CLASSES[family],'forms':FORMS[family]}
