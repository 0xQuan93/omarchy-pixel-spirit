"""Private exact-request memory. Saved model output never becomes executable code.

Authored routes take precedence. Actions remain reviewed proposals; text is a
clearly dated snapshot. Failed/contextual requests retain a retry explanation,
never a fabricated answer or a repeating side effect.
"""
from contextlib import contextmanager
from datetime import datetime
import fcntl
import hashlib
import json
import math
from pathlib import Path
import re
import secrets
import time
import unicodedata

from storage import get, put

FILE = 'learned-phrases.json'
MAX_ENTRIES = 512
MAX_BYTES = 4 * 1024 * 1024
MAX_TEXT = 4000
KEY = re.compile(r'[0-9a-f]{64}')
KINDS = {'answer', 'action', 'unresolved'}
EMOTES = {'idle','thinking','working','playing','reading','happy','sleeping'}


def canonical(message):
    if not isinstance(message, str) or not message.strip() or len(message) > 4000:
        raise ValueError('A learned request must be one to 4000 characters.')
    # Keep punctuation, quotations, line breaks, negation and timing words.
    return unicodedata.normalize('NFC', message).strip()


def key_for(message):
    return hashlib.sha256(canonical(message).encode()).hexdigest()


def _valid(entry):
    if not isinstance(entry, dict): return False
    try:
        return (KEY.fullmatch(entry['key']) is not None and key_for(entry['phrase']) == entry['key']
            and entry['kind'] in KINDS and isinstance(entry['generation'], str)
            and re.fullmatch(r'[0-9a-f]{32}', entry['generation']) is not None
            and all(type(entry[k]) in (int,float) and math.isfinite(entry[k]) and 0 <= entry[k] <= 32503680000
                    for k in ('created','used'))
            and isinstance(entry.get('text',''), str) and len(entry.get('text','')) <= MAX_TEXT
            and isinstance(entry.get('reason',''), str)
            and (entry['kind'] != 'action' or isinstance(entry.get('action'),str)
                 and isinstance(entry.get('fingerprint'),str) and KEY.fullmatch(entry['fingerprint']) is not None)
            and (entry['kind'] != 'answer' or bool(entry.get('text','').strip())))
    except (KeyError,TypeError,ValueError): return False


def _read(base):
    data = get(Path(base)/FILE, {})
    if not data: return []
    if data.get('version') != 1 or not isinstance(data.get('entries'),list):
        raise ValueError('Unrecognized learned phrase bank; saved files were preserved.')
    if len(data['entries']) > MAX_ENTRIES or len(json.dumps(data).encode()) > MAX_BYTES:
        raise ValueError('Learned phrase bank exceeds its limit; saved files were preserved.')
    return [e for e in data['entries'] if _valid(e)]


@contextmanager
def _locked(base):
    base = Path(base)
    base.mkdir(parents=True, exist_ok=True, mode=0o700)
    with (base/'learned-phrases.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        yield


def _write(base, entries):
    entries = sorted(entries, key=lambda e:(e['used'],e['created']), reverse=True)[:MAX_ENTRIES]
    while len(json.dumps({'version':1,'entries':entries}).encode()) > MAX_BYTES:
        entries.pop()
    # Deleted phrases must disappear from recovery copies as well.
    put(Path(base)/FILE, {'version':1,'entries':entries}, preserve_previous=False)


def _metadata(entry):
    return dict(learnedKey=entry['key'], learnedKind=entry['kind'], savedAt=entry['created'])


def begin(base, message):
    now = time.time()
    entry = dict(key=key_for(message), phrase=message, kind='unresolved',
                 created=now, used=now, generation=secrets.token_hex(16), reason='interrupted')
    with _locked(base):
        entries = [e for e in _read(base) if e['key'] != entry['key']]
        _write(base, [entry]+entries)
    return entry['generation']


def _contextual(message):
    text=canonical(message).casefold().rstrip('.!?')
    return (text in {'yes','no','okay','ok','again','do it','do that','that one','this one',
                     'tell me more','go on','continue','what about that','why','why not'}
            or bool(re.search(r'\b(?:it|that|this|them|those|these|he|she|they)\b',text))
            and len(text.split()) <= 5)


def complete(base, message, generation, data, registry, reason=''):
    key = key_for(message)
    with _locked(base):
        entries = _read(base)
        entry = next((e for e in entries if e['key']==key and e['generation']==generation),None)
        # A concurrent forget/refresh must never resurrect an older generation.
        if entry is None: return {}
        entry['reason'] = reason or 'invalid'
        if not reason and isinstance(data,dict):
            text,action=data.get('text'),data.get('action','')
            failed = (data.get('ok') is False or bool(data.get('error')) or bool(data.get('errors'))
                      or data.get('status') in ('failed','error','cancelled','interrupted'))
            effects = any(data.get(k) for k in ('automationScript','chosenName','roomActivity'))
            if failed: entry['reason']='invalid'
            elif _contextual(message): entry['reason']='context'
            elif effects: entry['reason']='side-effect'
            elif isinstance(text,str) and text.strip() and len(text)<=MAX_TEXT and isinstance(data.get('emote'),str) and data['emote'] in EMOTES:
                if action:
                    try:
                        registry.describe(action)
                        entry.update(kind='action', action=action, fingerprint=registry.fingerprint(action))
                    except (ValueError,TypeError): pass
                elif action == '':
                    entry.update(kind='answer', text=text, emote=data['emote'])
        _write(base, entries)
        return _metadata(entry)


def lookup(base, message, registry):
    key = key_for(message)
    try:
        with _locked(base):
            entries = _read(base)
            entry = next((e for e in entries if e['key']==key),None)
            if entry is None: return None
            entry['used']=time.time()
            try:_write(base,entries)
            except (OSError,ValueError):pass
    except (OSError,ValueError): return None
    result=dict(action='',emote='reading',route='learned',**_metadata(entry))
    if entry['kind']=='action':
        try:
            info=registry.describe(entry['action'])
            if registry.fingerprint(entry['action']) != entry['fingerprint']:
                raise ValueError('This control changed since it was learned. Ask again to review a new match.')
            if not info['available']: raise ValueError(info['availabilityReason'])
            result.update(text='Learned command: '+info['label']+'. Tap Run below.',
                          action=entry['action'],actionLabel=info['label'],emote='working')
        except ValueError as error:
            result['text']='Saved command unavailable. '+str(error)
    elif entry['kind']=='answer':
        date=datetime.fromtimestamp(entry['created']).astimezone().strftime('%b %d, %Y at %H:%M')
        result.update(text='Saved local AI reply · '+date+'\n'+entry['text'], emote=entry.get('emote','reading'))
    else:
        reasons={'context':'That phrase depends on an earlier conversation. Name its target, or choose Ask again.',
                 'side-effect':'This request changes a room, identity, or creative artifact. Its earlier result cannot be rerun as a learned phrase.',
                 'unavailable':'The previous local-model attempt was unavailable.',
                 'incomplete':'The previous local-model reply was incomplete.',
                 'interrupted':'The previous local-model attempt did not finish.',
                 'invalid':'The previous local-model reply was not usable.'}
        result['text']=reasons.get(entry.get('reason'),reasons['invalid'])+'\nThe phrase is saved. Choose Ask again to retry, or Forget phrase to remove it.'
    return result


def phrase(base,key):
    if not isinstance(key,str) or not KEY.fullmatch(key): raise ValueError('Invalid learned phrase key.')
    with _locked(base):
        entry=next((e for e in _read(base) if e['key']==key),None)
    if entry is None: raise ValueError('That learned phrase was removed. Enter the request again.')
    return entry['phrase']


def forget(base,key=None):
    if key is not None and (not isinstance(key,str) or not KEY.fullmatch(key)):
        raise ValueError('Invalid learned phrase key.')
    with _locked(base):
        entries=_read(base)
        remaining=[] if key is None else [e for e in entries if e['key']!=key]
        _write(base,remaining)
    return dict(text='Forgot all learned phrases.' if key is None else 'Forgot that learned phrase. Your next request can be learned afresh.',
                action='',emote='idle',route='local')


def maintenance(message,base):
    text=canonical(message).casefold()
    if text in {'forget learned phrases','forget all learned phrases','clear learned phrases'}:
        return forget(base)
    if text not in {'show learned phrases','list learned phrases','show my learned phrases','what have you learned'}:
        return None
    with _locked(base): entries=_read(base)
    lines=[e['phrase'][:100].replace('\n',' ')+' · '+e['kind'] for e in sorted(entries,key=lambda e:e['used'],reverse=True)[:12]]
    return dict(text=f'{len(entries)} learned phrases saved on this computer.'+
                ('\n'+'\n'.join(lines) if lines else '\nRequests answered by the local model will appear here.')+
                '\nRepeat one to reuse it. Ask again refreshes it; Forget phrase removes it. Say “forget all learned phrases” to clear the bank.',
                action='',emote='reading',route='local')
