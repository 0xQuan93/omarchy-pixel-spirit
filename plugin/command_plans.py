"""Reviewed, expiring local plans. Only fixed action IDs cross the process boundary."""
import fcntl
import re
import secrets
import time
from pathlib import Path
from storage import get, put

TTL = 300

def _registry(actions,labels,available):
    from capability_specs import build
    return build(actions,labels,available)

def proposal(message, base, actions, labels, normalize, match, resolve, available, registry=None):
    from compound_commands import propose
    registry=registry or _registry(actions,labels,available)
    def clause(text):
        action = match(text)
        return action or resolve(text)
    reply = propose(message, clause, labels, registry.plan_allowed(), normalize, registry.rewrite_plan)
    if not reply or not reply.get('steps'):
        return reply
    return prepare_steps([step['action'] for step in reply['steps']],base,actions,labels,registry)

def prepare_steps(ids,base,actions,labels,registry,expected_token=None):
    from compound_commands import _conflict
    if (not 1<=len(ids)<=4 or len(set(ids))!=len(ids) or any(a not in registry.plan_allowed() for a in ids)
            or any(_conflict(a,b) for i,a in enumerate(ids) for b in ids[i+1:])):
        raise ValueError('The plan contains unsupported or conflicting steps.')
    ids=registry.rewrite_plan(ids)
    if not ids:raise ValueError('The plan could not be validated.')
    if not all(registry.describe(a)['available'] for a in ids):
        return dict(text='One of those controls is unavailable here. Nothing has run. Try each request separately.',
                    action='', steps=[], emote='idle', route='local')
    token=secrets.token_hex(16);base=Path(base);base.mkdir(parents=True,exist_ok=True)
    with (base/'command-plan.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX)
        if expected_token is not None:
            current=get(base/'command-plan.json',{})
            _validate_saved(current,expected_token,registry)
        put(base/'command-plan.json',dict(token=token,created=time.time(),actions=list(ids),
            fingerprints={a:registry.fingerprint(a) for a in ids}),preserve_previous=False)
    return _preview(token,ids,labels,'Ready: review these steps, then tap Run plan. This plan expires in five minutes.')

def _preview(token,ids,labels,text):
    return dict(action='plan:'+token,actionLabel='Run '+str(len(ids))+(' step' if len(ids)==1 else ' steps'),
                text=text,steps=[dict(action=a,label=labels[a]) for a in ids],emote='working',route='local')

def _validate_token(token):
    if not isinstance(token,str) or not re.fullmatch(r'plan:[0-9a-f]{32}',token):
        raise ValueError('Invalid plan token.')

def _validate_saved(plan,token,registry):
    """One validation contract for pending edits and claimed execution."""
    _validate_token(token)
    if not isinstance(plan,dict):raise ValueError('This plan is invalid or expired.')
    ids=plan.get('actions');created=plan.get('created')
    if (plan.get('token')!=token[5:] or type(created) not in (int,float) or not 0<=time.time()-created<=TTL
            or not isinstance(ids,list) or not 1<=len(ids)<=4
            or any(not isinstance(a,str) or a not in registry.plan_allowed() for a in ids)):
        raise ValueError('That plan expired, changed, or already ran. Please prepare a new plan.')
    if plan.get('fingerprints')!={a:registry.fingerprint(a) for a in ids}:
        raise ValueError('These controls changed since the preview. Prepare a new plan.')
    if registry.rewrite_plan(ids)!=tuple(ids):
        raise ValueError('This plan needs a fresh review.')
    return ids

def pending(base,token,registry):
    return _validate_saved(get(Path(base)/'command-plan.json',{}),token,registry)

def invalidate(base,token):
    _validate_token(token)
    base=Path(base);base.mkdir(parents=True,exist_ok=True)
    with (base/'command-plan.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX)
        current=get(base/'command-plan.json',{})
        if isinstance(current,dict) and current.get('token')==token[5:]:
            put(base/'command-plan.json',{},False)
            return True
    return False

def edit(message,token,base,actions,labels,resolve_clause,registry):
    from plan_edits import propose
    from smart_commands import normalize
    try:_validate_token(token)
    except ValueError as error:return dict(text=str(error),action='',steps=[],emote='idle',route='local')
    if normalize(message) in {'cancel','cancel plan','cancel the plan','cancel this plan','cancel that','never mind','nevermind'}:
        cleared=invalidate(base,token)
        return dict(text='Cancelled the pending plan.' if cleared else 'That plan is no longer pending.',
                    action='',steps=[],emote='idle',route='local',status='cancelled',planEdit=True)
    try:ids=pending(base,token,registry)
    except ValueError as error:return dict(text=str(error),action='',steps=[],emote='idle',route='local')
    result=propose(message,ids,labels,resolve_clause,registry)
    if result is None:
        return _preview(token[5:],ids,labels,'This plan is still waiting for review. Try “skip step two,” “only open files,” or “cancel” before starting a different request.')
    if result.get('reason')=='empty-plan':
        invalidate(base,token);return result
    if not result.get('steps'):
        return _preview(token[5:],ids,labels,result['text']+' Your existing plan is unchanged.')
    try:
        new=prepare_steps([step['action'] for step in result['steps']],base,actions,labels,registry,expected_token=token)
    except ValueError as error:
        return dict(text=str(error),action='',steps=[],emote='idle',route='local')
    if not new.get('action'):
        return _preview(token[5:],ids,labels,new['text']+' Your existing plan is unchanged.')
    return new

def execute(token, base, actions, labels, available, run_step, registry=None):
    import plan_runtime
    with plan_runtime.execution_lock(base):
        return _execute(token,base,actions,labels,available,run_step,registry)

def _execute(token, base, actions, labels, available, run_step, registry=None):
    import plan_runtime
    registry=registry or _registry(actions,labels,available)
    _validate_token(token)
    base = Path(base)
    base.mkdir(parents=True, exist_ok=True)
    with (base / 'command-plan.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX)
        plan=get(base/'command-plan.json',{})
        if not isinstance(plan,dict) or plan.get('token')!=token[5:]:
            raise ValueError('This plan has expired or was already used. Ask again to prepare it.')
        # Claim before validation/effects: failed or interrupted plans never replay.
        put(base/'command-plan.json',{},preserve_previous=False)
        ids=_validate_saved(plan,token,registry)
        if any(a not in actions for a in ids):raise ValueError('A required control is no longer registered.')
        if not all(available(a) for a in ids):
            raise ValueError('A required control is unavailable. Nothing ran; prepare a new plan.')
    plan_runtime.begin(base,token,ids,labels)
    completed = []
    accepted = []
    finished = []
    receipts = []
    for index,action in enumerate(ids):
        if not plan_runtime.start_step(base,token,index):
            text=(_summary(completed,accepted)+'Stopped before: '+labels[action]+'.').strip()
            plan_runtime.update(base,token,status='cancelled',text=text)
            return dict(text=text,action='',emote='idle',route='local',status='cancelled',ok=False,completed=completed,accepted=accepted,receipts=receipts)
        receipt = None
        try:
            receipt = run_step(action)
            if (not isinstance(receipt, dict) or receipt.get('error') or receipt.get('ok') is not True
                    or receipt.get('status') not in {'accepted','completed','verified'}):
                raise ValueError('The control did not confirm success.')
        except Exception:
            remaining = ids[len(finished)+1:]
            text = _summary(completed,accepted) or 'No steps completed. '
            stopped='cancelled' if isinstance(receipt,dict) and receipt.get('status')=='cancelled' and receipt.get('ok') is False else 'failed'
            text += ('Cancelled at: ' if stopped=='cancelled' else 'Stopped at: ') + labels[action] + '.'
            if isinstance(receipt,dict) and isinstance(receipt.get('text'),str) and receipt['text'].strip():
                text += ' '+receipt['text'].strip()
                receipts.append(dict(action=action,status=stopped,text=receipt['text'],verification=receipt.get('verification','process')))
            if remaining: text += ' Not run: ' + '; '.join(labels[a] for a in remaining) + '.'
            plan_runtime.update(base,token,index,stopped,status=stopped,text=text)
            return dict(text=text, action='', emote='idle', route='local', completed=completed, accepted=accepted, receipts=receipts, ok=False, status=stopped)
        plan_runtime.update(base,token,index,'accepted' if receipt['status']=='accepted' else 'completed')
        finished.append(action)
        receipts.append(dict(action=action,status=receipt['status'],verification=receipt.get('verification','process')))
        (accepted if receipt['status']=='accepted' else completed).append(labels[action])
    plan_runtime.update(base,token,status='completed',text=_summary(completed,accepted).strip())
    return dict(text=_summary(completed,accepted).strip(), action='',
                emote='working', route='local', completed=completed, accepted=accepted,
                receipts=receipts, ok=True, status='accepted' if accepted else 'completed')

def _summary(completed,accepted):
    return (('Completed: '+'; '.join(completed)+'. ') if completed else '') + (('Requests accepted: '+'; '.join(accepted)+'. ') if accepted else '')
