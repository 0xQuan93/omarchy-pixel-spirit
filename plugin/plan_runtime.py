"""Private progress receipts for one foreground plan; never resumes work."""
import contextlib
import fcntl
import os
import re
import time
from pathlib import Path
from storage import get,put
TOKEN=re.compile(r'plan:[0-9a-f]{32}')

def _start(pid):
    try:return Path(f'/proc/{pid}/stat').read_text().rsplit(')',1)[1].split()[19]
    except (OSError,IndexError):return ''

@contextlib.contextmanager
def execution_lock(base):
    base=Path(base);base.mkdir(parents=True,exist_ok=True)
    with (base/'command-execution.lock').open('a') as lock:
        try:fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        except BlockingIOError:raise ValueError('Another plan is still running. Wait for its result.') from None
        yield

@contextlib.contextmanager
def _locked(base):
    base=Path(base);base.mkdir(parents=True,exist_ok=True)
    with (base/'command-progress.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX)
        yield base/'command-progress.json'

def begin(base,token,ids,labels):
    if not TOKEN.fullmatch(token):raise ValueError('Invalid plan token.')
    data=dict(token=token,status='running',current=0,total=len(ids),pid=os.getpid(),
              processStart=_start(os.getpid()),updated=time.time(),cancelRequested=False,
              text='Running the reviewed plan.',steps=[dict(action=a,label=labels[a],status='pending') for a in ids])
    if not data['processStart']:raise ValueError('Cannot track this plan process safely.')
    with _locked(base) as path:put(path,data,False)

def update(base,token,index=None,step_status=None,status=None,text=None):
    with _locked(base) as path:
        data=get(path,{})
        if data.get('token')!=token:return
        if index is not None:
            data['current']=index
            data['steps'][index]['status']=step_status
        if status is not None:
            data['status']=status
            for step in data['steps']:
                if step['status']=='pending':step['status']='skipped'
        if text is not None:data['text']=text
        data['updated']=time.time();put(path,data,False)

def status(base,token=None):
    if token is not None and (not isinstance(token,str) or not TOKEN.fullmatch(token)):
        raise ValueError('Invalid plan token.')
    with _locked(base) as path:
        data=get(path,{})
        if not data or (token and data.get('token')!=token):return {'status':'unknown','steps':[],'text':'No matching running plan.'}
        if data.get('status')=='running' and (not data.get('processStart') or _start(data.get('pid'))!=data['processStart']):
            data['status']='interrupted';data['text']='The previous plan was interrupted. Check its results before preparing a new one; it will not resume.'
            for step in data.get('steps',[]):
                if step['status']=='running':step['status']='unknown'
                elif step['status']=='pending':step['status']='skipped'
            put(path,data,False)
        return {key:value for key,value in data.items() if key not in {'pid','processStart'}}

def cancel(base,token):
    if not isinstance(token,str) or not TOKEN.fullmatch(token):raise ValueError('Invalid plan token.')
    with _locked(base) as path:
        data=get(path,{})
        if data.get('token')!=token or data.get('status')!='running':
            return {'text':'That plan is no longer running.','route':'local','action':''}
        data['cancelRequested']=True;put(path,data,False)
    return {'text':'I will stop before the next step. The current operation may still finish.','route':'local','action':''}

def cancelled(base,token):
    data=status(base,token)
    return data.get('cancelRequested') is True


def start_step(base,token,index):
    """Atomically honor cancellation before declaring the next operation active."""
    with _locked(base) as path:
        data=get(path,{})
        if (data.get('token')!=token or data.get('status')!='running' or data.get('cancelRequested')
                or data.get('pid')!=os.getpid() or data.get('processStart')!=_start(os.getpid())):
            return False
        data['current']=index;data['steps'][index]['status']='running';data['updated']=time.time()
        put(path,data,False)
        return True
