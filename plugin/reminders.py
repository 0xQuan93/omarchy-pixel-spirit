"""Bounded reminders delegated to the existing Omarchy session timer service."""
import json
import re
import subprocess


def run(args):
    try:
        return subprocess.run(args, capture_output=True, text=True, check=True, timeout=10).stdout
    except (OSError, subprocess.SubprocessError):
        raise ValueError('Omarchy could not complete the reminder request. Check the desktop session and try again.') from None


def upcoming():
    data = json.loads(run(['omarchy', 'reminder', 'show', '--json']))
    if not isinstance(data, dict) or not isinstance(data.get('reminders'), list):
        raise ValueError('Could not read upcoming reminders.')
    return {'reminders': data['reminders']}


def create(minutes, message):
    if not re.fullmatch(r'[0-9]{1,4}', minutes) or not 1 <= int(minutes) <= 1440:
        raise ValueError('Choose a whole number from 1 to 1440 minutes.')
    message = message.strip()
    if len(message) > 240 or any(ord(c) < 32 or ord(c) == 127 for c in message):
        raise ValueError('Use a single-line reminder of at most 240 characters.')
    run(['omarchy', 'reminder', str(int(minutes)), message or 'Your timer is up'])
    return {'text': f'Reminder set for {int(minutes)} minute(s). Omarchy will notify you.'}


def cancel(unit):
    if not re.fullmatch(r'omarchy-reminder-[0-9]+m-[0-9]+', unit):
        raise ValueError('Unknown reminder.')
    if unit not in {r.get('unit') for r in upcoming()['reminders']}:
        raise ValueError('That reminder already finished or was cancelled.')
    # The service may not be loaded before its timer first fires.
    run(['systemctl', '--user', 'stop', unit+'.timer'])
    from pathlib import Path
    import os
    runtime = Path(os.environ.get('XDG_RUNTIME_DIR', '/tmp')) / 'omarchy-reminders'
    (runtime / (unit+'.message')).unlink(missing_ok=True)
    try:
        run(['omarchy', 'shell', 'omarchy.indicators', 'refresh'])
    except ValueError:
        pass
    return {'text': 'Reminder cancelled.'}


def parse_request(message):
    """Recognize explicit requests only. Return a draft for the user to submit."""
    match = re.fullmatch(r'(?:please )?remind me in ([0-9]{1,4}) (minutes?|mins?|hours?|hrs?) to (.{1,240})', message.strip(), re.I)
    timer = False
    if not match:
        match = re.fullmatch(r'(?:please )?set (?:a )?timer for ([0-9]{1,4}) (minutes?|mins?|hours?|hrs?)', message.strip(), re.I)
        timer = True
    if not match:
        return None
    minutes = int(match[1]) * (60 if match[2].lower().startswith('h') else 1)
    if not 1 <= minutes <= 1440:
        raise ValueError('Choose a timer between 1 minute and 24 hours.')
    return {'minutes': str(minutes), 'message': '' if timer else match[3]}
