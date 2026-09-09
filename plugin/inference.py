"""One local inference job at a time; ambient work never queues behind chat."""
import fcntl
import json
import urllib.request
from growth import STATE


def request(payload, timeout=150, background=False, state_dir=None):
    state_dir = state_dir or STATE
    state_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
    with (state_dir / 'model.lock').open('w') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | (fcntl.LOCK_NB if background else 0))
        req = urllib.request.Request('http://127.0.0.1:11434/api/chat',
                                     data=json.dumps(payload).encode(),
                                     headers={'Content-Type': 'application/json'})
        with urllib.request.urlopen(req, timeout=timeout) as response:
            return json.load(response)
