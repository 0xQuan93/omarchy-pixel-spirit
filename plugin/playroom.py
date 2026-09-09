"""Private room, notes, and capped interaction rewards."""
import fcntl, json, time
from pathlib import Path
from urllib.parse import urlparse, unquote
from growth import STATE, get, put
ACTIVITIES={'rest','read','play','garden'}
def default():return {'bond':0,'day':'','earned':[],'activity':'rest','notes':[],'message':'A little room between the pixels.'}
def note_text(value):
 if value.startswith('file:'):
  url=urlparse(value)
  if url.netloc not in ('','localhost'):raise ValueError('Drop a local text note.')
  path=Path(unquote(url.path))
  if path.is_symlink() or path.suffix.lower() not in ('.md','.txt') or not path.is_file():raise ValueError('Drop a small .txt or .md file, or plain text.')
  with path.open() as f:value=f.read(4097)
 if len(value)>4096:raise ValueError('Keep notes under 4096 characters.')
 value=value.strip()
 if not value:raise ValueError('That note was empty.')
 return value

def update(command='status',value=''):
 STATE.mkdir(parents=True,exist_ok=True,mode=0o700)
 with (STATE/'room.lock').open('w') as lock:
  fcntl.flock(lock,fcntl.LOCK_EX)
  state=get(STATE/'room.json',default());today=time.strftime('%Y-%m-%d')
  if state['day']!=today:state['day']=today;state['earned']=[]
  reward=''
  if command=='note':
   text=note_text(value);state['notes']=(state['notes']+[{'text':text,'at':time.time()}])[-12:]
   state['message']='A new note for my shelf. Thank you.';state['activity']='read';reward='note'
  elif command=='pat':state['message']='Three head pats! Little pixels, big affection.';reward='pat'
  elif command=='catch':state['message']='Three fireflies found their way home.';reward='catch';state['activity']='play'
  elif command in ('activity','ambient'):
   if value not in ACTIVITIES:raise ValueError('Unknown room activity')
   state['activity']=value;state['message']={'rest':'Settling into my little nest.','read':'Reading our little notebook.','play':'Time to chase a few sparks.','garden':'Tending the pixel garden.'}[value];reward=value if command=='activity' else ''
  elif command=='clear_notes':state['notes']=[];state['message']='The note shelf is empty.'
  elif command!='status':raise ValueError('Unknown room interaction')
  if reward and reward not in state['earned']:
   state['earned'].append(reward);state['bond']+=1
  put(STATE/'room.json',state,preserve_previous=command!='clear_notes')
  return state

def context():
 state=get(STATE/'room.json',default())
 return {k:state[k] for k in ['bond','activity','message']} | {'notes':[n['text'][:350] for n in state['notes'][-3:]]}
