"""Versioned contract for reviewed, source-specific Wisp adapters.

Only application code may call ``extension``. Plugin manifests and saved files
are discovery data; Wisp must never load either as an adapter specification.
"""
import json
import math
import re
import time

from capability_registry import Registry

VERSION = 1
MAX_CONTROLS = 32
MAX_FACT_BYTES = 16 * 1024
MAX_VALUE_NODES = 256
MAX_VALUE_DEPTH = 8
MAX_INT_BITS = 4096
FUTURE_SKEW_MS = 2000
SOURCE = re.compile(r"[a-zA-Z0-9][a-zA-Z0-9_.:'-]{0,119}")
ACTION = re.compile(r'[a-z][a-z0-9_:-]{0,119}')
OPERATION = re.compile(r'[a-zA-Z0-9][a-zA-Z0-9_:-]{0,119}')
VERIFY = frozenset({'process', 'accepted', 'state'})
FACT_STATUS = frozenset({'verified', 'unknown'})
TOP_FIELDS = frozenset({'schemaVersion', 'sourceId', 'sourceLabel', 'controls'})
CONTROL_FIELDS = frozenset({'id', 'label', 'argv', 'operation', 'planSafe', 'verification'})
FACT_FIELDS = frozenset({'schemaVersion', 'sourceId', 'sourceLabel', 'observedAtMs',
                         'expiresAtMs', 'status', 'verification', 'unknownReason', 'value'})


def _label(value):
    return isinstance(value, str) and bool(value.strip()) and len(value) <= 160 and all(c.isprintable() for c in value)


def _bounded_value(value):
    """Limit nested fact values before JSON serialization can grow unbounded."""
    pending = [(value, 0)]
    count = 0
    while pending:
        item, depth = pending.pop()
        count += 1
        if count > MAX_VALUE_NODES or depth > MAX_VALUE_DEPTH:
            raise ValueError('Adapter fact value is too complex.')
        if type(item) is dict:
            if len(item) > MAX_VALUE_NODES or any(type(key) is not str or len(key) > 160
                                                   or not all(c.isprintable() for c in key) for key in item):
                raise ValueError('Invalid adapter fact value.')
            pending.extend((part, depth + 1) for part in item.values())
        elif type(item) is list:
            if len(item) > MAX_VALUE_NODES:
                raise ValueError('Adapter fact value is too complex.')
            pending.extend((part, depth + 1) for part in item)
        elif type(item) is str:
            if len(item) > MAX_FACT_BYTES:
                raise ValueError('Adapter fact value is too large.')
        elif type(item) is int:
            if item.bit_length() > MAX_INT_BITS:
                raise ValueError('Adapter fact value is too large.')
        elif type(item) is float:
            if not math.isfinite(item):
                raise ValueError('Invalid adapter fact value.')
        elif item is not None and type(item) is not bool:
            raise ValueError('Invalid adapter fact value.')


def extension(spec):
    """Return (fixed argv, labels, metadata) for ``capabilities.registry``.

    The caller must be a reviewed Python module, imported by application code.
    This validator does not authorize loading a manifest or executing a command.
    """
    if (not isinstance(spec, dict) or set(spec) != TOP_FIELDS
            or type(spec.get('schemaVersion')) is not int or spec['schemaVersion'] != VERSION):
        raise ValueError('Unsupported adapter contract.')
    source, label, controls = spec['sourceId'], spec['sourceLabel'], spec['controls']
    if (not isinstance(source, str) or not SOURCE.fullmatch(source) or not _label(label)
            or not isinstance(controls, list) or not 1 <= len(controls) <= MAX_CONTROLS):
        raise ValueError('Invalid adapter source or control count.')
    actions, labels, metadata = {}, {}, {}
    for control in controls:
        if not isinstance(control, dict) or set(control) != CONTROL_FIELDS:
            raise ValueError('Invalid adapter control fields.')
        ident, argv = control['id'], control['argv']
        if (not isinstance(ident, str) or not ACTION.fullmatch(ident) or ident in actions
                or not isinstance(argv, list) or not 1 <= len(argv) <= 16
                or any(not isinstance(arg, str) or not arg or len(arg) > 512 or '\x00' in arg for arg in argv)
                or not _label(control['label'])
                or not isinstance(control['operation'], str) or not OPERATION.fullmatch(control['operation'])
                or type(control['planSafe']) is not bool
                or not isinstance(control['verification'], str) or control['verification'] not in VERIFY):
            raise ValueError('Invalid adapter control.')
        actions[ident] = list(argv)
        labels[ident] = control['label']
        metadata[ident] = {'sourceId': source, 'sourceLabel': label,
                           'operation': control['operation'], 'planSafe': control['planSafe'],
                           'verification': control['verification']}
    # Reuse the same validation the live capability registry applies.
    Registry(actions, labels, metadata=metadata)
    return actions, labels, metadata


def validate_fact(fact, expected_source=None, expected_label=None, now_ms=None):
    """Validate a bounded observed/unknown fact and return display evidence."""
    if (type(fact) is not dict or set(fact) != FACT_FIELDS
            or type(fact.get('schemaVersion')) is not int or fact['schemaVersion'] != VERSION):
        raise ValueError('Invalid adapter fact envelope.')
    now = time.time_ns() // 1_000_000 if now_ms is None else now_ms
    if type(now) is not int or now < 0:
        raise ValueError('Invalid observation clock.')
    source, label = fact['sourceId'], fact['sourceLabel']
    observed, expires = fact['observedAtMs'], fact['expiresAtMs']
    status, verification, reason = fact['status'], fact['verification'], fact['unknownReason']
    if (not isinstance(source, str) or not SOURCE.fullmatch(source)
            or expected_source is not None and source != expected_source
            or not _label(label)
            or expected_label is not None and label != expected_label
            or type(observed) is not int or not 0 <= observed <= 2**63 - 1
            or type(expires) is not int or not observed <= expires <= observed + 60000
            or observed > now + FUTURE_SKEW_MS or expires < now
            or not isinstance(status, str) or status not in FACT_STATUS or verification != 'state'
            or not isinstance(reason, str) or len(reason) > 240
            or not all(char.isprintable() for char in reason)
            or (status == 'unknown' and (not reason.strip() or fact['value'] is not None))
            or (status == 'verified' and (reason or fact['value'] is None))):
        raise ValueError('Invalid adapter fact evidence.')
    _bounded_value(fact['value'])
    try:
        raw = json.dumps(fact, allow_nan=False, ensure_ascii=False).encode('utf-8')
    except (TypeError, ValueError, OverflowError, RecursionError) as error:
        raise ValueError('Invalid adapter fact value.') from error
    if len(raw) > MAX_FACT_BYTES:
        raise ValueError('Adapter fact is too large.')
    return {key: fact[key] for key in ('sourceId', 'sourceLabel', 'observedAtMs',
                                       'expiresAtMs', 'status', 'verification', 'unknownReason')}
