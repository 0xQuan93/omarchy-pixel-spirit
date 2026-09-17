"""One local inference job at a time; ambient work never queues behind chat."""
import fcntl
import json
import math
import time
import urllib.request
from growth import STATE


def request(payload, timeout=150, background=False, state_dir=None):
    if type(timeout) not in (int, float) or not math.isfinite(timeout) or timeout <= 0:
        raise ValueError('Inference timeout must be a finite positive number.')
    deadline = time.monotonic() + timeout
    state_dir = state_dir or STATE
    state_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
    with (state_dir / 'model.lock').open('w') as lock:
        while True:
            try:
                fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
                break
            except BlockingIOError:
                if background:
                    raise
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    raise TimeoutError('Local conversation is busy; please try again.') from None
                time.sleep(min(0.05, remaining))
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise TimeoutError('Local conversation timed out before starting.')
        req = urllib.request.Request('http://127.0.0.1:11434/api/chat',
                                     data=json.dumps(payload).encode(),
                                     headers={'Content-Type': 'application/json'})
        with urllib.request.urlopen(req, timeout=remaining) as response:
            return json.load(response)
