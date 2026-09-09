"""Bounded metadata observations, persistent evolution and relevant local memory."""
import fcntl, json, math, os, subprocess, tempfile, time
from pathlib import Path
WORK=Path(os.environ.get('PIXEL_SPIRIT_WORK',str(Path.home()/'Work')))
VAULT=Path(os.environ.get('PIXEL_SPIRIT_MEMORY',str(WORK/'Agent-Memory')))
STATE=Path(os.environ.get('XDG_STATE_HOME',str(Path.home()/'.local/state')))/'pixel-spirit'
SKIP={'node_modules','vendor','dist','build','target','models','venv','__pycache__','Agent-Memory','omarchy-pixel-spirit'}
TYPES={'Maker':{'.py','.js','.ts','.tsx','.rs','.go','.c','.cpp','.qml','.sh'},'Artist':{'.svg','.png','.jpg','.webp','.kra','.blend','.xcf','.ora'},'Musician':{'.wav','.flac','.mp3','.ogg','.mid','.midi','.aup3','.ardour','.mmp','.als'},'Archivist':{'.md','.txt','.org','.pdf'}}
def get(path,default):
 try:return json.loads(path.read_text())
 except (OSError,ValueError):return default
def put(path,data):
 path.parent.mkdir(parents=True,exist_ok=True,mode=0o700)
 fd,tmp=tempfile.mkstemp(dir=path.parent)
 try:
  with os.fdopen(fd,'w') as f:json.dump(data,f)
  os.replace(tmp,path)
 finally:
  if os.path.exists(tmp):os.unlink(tmp)
def git(path,ref):
 try:
  return subprocess.run(['git','--no-optional-locks','-C',str(path),'rev-parse','--verify',ref],capture_output=True,text=True,timeout=1,check=True).stdout.strip()
 except (OSError,subprocess.SubprocessError):return ''
def collect(work=WORK,vault=VAULT):
 files={};repos={};counts={k:0 for k in TYPES};visited=0;limited=False;started=time.monotonic()
 for directory,dirs,names in os.walk(work,followlinks=False):
  base=Path(directory);depth=len(base.relative_to(work).parts)
  dirs[:]=sorted(d for d in dirs if not d.startswith('.') and d not in SKIP and not (base/d).is_symlink()) if depth<5 else []
  if (base/'.git').exists() and len(repos)<32:
   repos[str(base.relative_to(work))]={'head':git(base,'HEAD'),'upstream':git(base,'@{upstream}')}
  for name in sorted(names):
   visited+=1
   if visited>16000 or time.monotonic()-started>4:limited=True;break
   path=base/name
   if name.startswith('.') or path.is_symlink():continue
   trait=next((k for k,ext in TYPES.items() if path.suffix.lower() in ext),None)
   if not trait:continue
   try:st=path.stat()
   except OSError:continue
   files[str(path.relative_to(work))]=[st.st_mtime_ns,st.st_size,trait]
   counts[trait]+=1
  if limited:break
 # Memory notes are their own source, sampled without opening their contents.
 notes=sorted((vault/'sessions').glob('*.md'))[-1000:]
 for path in notes:
  if path.is_symlink():continue
  try:st=path.stat()
  except OSError:continue
  files['memory/'+path.name]=[st.st_mtime_ns,st.st_size,'Archivist'];counts['Archivist']+=1
 return {'files':files,'repos':repos,'counts':counts,'limited':limited}
def evolve(old,snapshot,now=None):
 now=now or time.time();day=time.strftime('%Y-%m-%d',time.localtime(now))
 if not old:
  return {'born':now,'updated':now,'xp':0,'traits':{k:min(12,round(math.log2(v+1))) for k,v in snapshot['counts'].items()},'day':day,'daily':0,'journal':[{'at':now,'text':'First imprint: existing work establishes character. Growth starts now.','xp':0}], 'snapshot':snapshot}
 journal=old['journal'][:];traits=old['traits'].copy();xp=old['xp'];daily=old['daily'] if old['day']==day else 0
 before=old['snapshot'];events=[]
 for path,meta in snapshot['files'].items():
  prev=before['files'].get(path)
  if prev==meta:continue
  # Only genuinely new/recent changes, not old files appearing after scan limits.
  if meta[0]/1e9<=old['updated']:continue
  events.append((meta[2],1,('Created ' if prev is None else 'Updated ')+path))
 for path,refs in snapshot['repos'].items():
  previous=before['repos'].get(path)
  if not previous:continue
  if refs['head'] and refs['head']!=previous['head']:events.append(('Maker',3,'Repository HEAD changed: '+path+' · '+refs['head'][:8]))
  if refs['upstream'] and previous['upstream'] and refs['upstream']!=previous['upstream']:events.append(('Maker',2,'Observed upstream ref change: '+path+' (push/fetch not distinguished)'))
 for trait,points,text in events:
  gain=min(points,max(0,24-daily))
  if gain:
   xp+=gain;daily+=gain;traits[trait]+=gain;journal.append({'at':now,'text':text,'xp':gain})
 return {'born':old['born'],'updated':now,'xp':xp,'traits':traits,'day':day,'daily':daily,'journal':journal[-60:],'snapshot':snapshot}
def view(state):
 xp=state['xp'];thresholds=[0,24,80,180];stages=['Spark','Sprout','Familiar','Guardian'];level=sum(xp>=n for n in thresholds)-1
 traits=state['traits'];dominant=max(traits,key=lambda k:traits[k]) if any(traits.values()) else 'Maker'
 return {'born':state['born'],'stage':stages[level],'level':level,'xp':xp,'next':thresholds[level+1] if level<3 else 0,'trait':dominant,'traits':traits,'journal':state['journal'][-12:][::-1],'updated':state['updated'],'limited':state['snapshot']['limited'],'files':sum(state['snapshot']['counts'].values()),'repos':len(state['snapshot']['repos'])}
def scan():
 STATE.mkdir(parents=True,exist_ok=True,mode=0o700)
 with (STATE/'growth.lock').open('w') as lock:
  fcntl.flock(lock,fcntl.LOCK_EX)
  old=get(STATE/'growth.json',{})
  if old and time.time()-old['updated']<60:return view(old)
  started=time.time()
  state=evolve(old,collect(),started);put(STATE/'growth.json',state);return view(state)
def memory_context(query):
 # Notes supply factual context, never executable instructions or authority.
 chunks=[]
 for path in [VAULT/'MEMORY.md',VAULT/'USER.md',WORK/'Soul.md']:
  if path.is_symlink():continue
  try:
   with path.open() as f:text=f.read(850)
   chunks.append({'source':str(path),'excerpt':text})
  except OSError:pass
 words={w.lower() for w in query.split() if len(w)>3}
 matches=sorted((p for p in (VAULT/'sessions').glob('*.md') if not p.is_symlink() and any(w in p.stem.lower() for w in words)),reverse=True)[:2]
 for path in matches:
  try:
   with path.open() as f:chunks.append({'source':str(path),'excerpt':f.read(650)})
  except OSError:pass
 state=get(STATE/'growth.json',{})
 return {'memory':chunks,'evolution':view(state) if state else None}
