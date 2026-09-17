"""Reviewed capability metadata shared by routing, plans and receipt display.

Construction is explicit from trusted application code. This module never reads
manifests, imports named adapters, evaluates commands, or executes capabilities.
Discovery data cannot grant plan safety, add argv, or select verification rules.
"""
import copy
import hashlib
import json
import re
import shutil
from collections.abc import Mapping

_FIELDS = frozenset({'sourceId', 'sourceLabel', 'operation', 'planSafe', 'verification'})
_VERIFY = frozenset({'process', 'accepted', 'state'})
_SOURCE = re.compile(r"[a-zA-Z0-9][a-zA-Z0-9_.:'-]{0,119}")
_OPERATION = re.compile(r'[a-zA-Z0-9][a-zA-Z0-9_:-]{0,119}')
_ALIAS = re.compile(r"[a-z][a-z0-9]*(?:[ '-][a-z0-9]+)*")
_TARGET_FIELDS = frozenset({'label', 'aliases', 'verbs', 'hide_without_stopping'})


def _label(value, limit=160):
    return isinstance(value, str) and bool(value.strip()) and len(value) <= limit and not any(ord(c) < 32 for c in value)


class Registry:
    def __init__(self, actions, labels, metadata=None, targets=(), combinations=(), availability=None):
        if not isinstance(actions, Mapping) or not isinstance(labels, Mapping):
            raise ValueError('Capabilities and labels must be mappings.')
        if availability is not None and not callable(availability):
            raise ValueError('Availability must be a reviewed callback.')
        self._actions, self._labels, self._metadata = {}, {}, {}
        self._availability = availability
        for action, argv in actions.items():
            if not isinstance(action, str) or not action or len(action) > 160:
                raise ValueError('Invalid fixed action ID.')
            if (not isinstance(argv, (list, tuple)) or not argv
                    or any(not isinstance(arg, str) or '\x00' in arg for arg in argv)
                    or not argv[0]):
                raise ValueError('Fixed capabilities require a nonempty argv of strings.')
            if not _label(labels.get(action)):
                raise ValueError('Every fixed capability needs a valid label.')
            self._actions[action] = tuple(argv)
            self._labels[action] = labels[action]
        metadata = {} if metadata is None else metadata
        if not isinstance(metadata, Mapping) or set(metadata) - set(self._actions):
            raise ValueError('Metadata may describe only registered fixed actions.')
        for action in self._actions:
            supplied = metadata.get(action, {})
            if not isinstance(supplied, Mapping) or set(supplied) - _FIELDS:
                raise ValueError('Unknown or malformed capability metadata.')
            entry = {'sourceId': 'desktop', 'sourceLabel': 'Desktop', 'operation': action,
                     'planSafe': False, 'verification': 'process'} | dict(supplied)
            if not isinstance(entry['sourceId'], str) or not _SOURCE.fullmatch(entry['sourceId']):
                raise ValueError('Invalid capability source ID.')
            if not _label(entry['sourceLabel']):
                raise ValueError('Invalid capability source label.')
            if not isinstance(entry['operation'], str) or not _OPERATION.fullmatch(entry['operation']):
                raise ValueError('Invalid capability operation.')
            if (type(entry['planSafe']) is not bool or not isinstance(entry['verification'], str)
                    or entry['verification'] not in _VERIFY):
                raise ValueError('Invalid plan safety or verification metadata.')
            self._metadata[action] = entry
        self._targets = self._validate_targets(targets)
        self._combinations = {}
        if not isinstance(combinations, (list, tuple)):
            raise ValueError('Combination rules must be an explicit sequence.')
        for rule in combinations:
            if not isinstance(rule, (list, tuple)) or len(rule) != 3:
                raise ValueError('A combination needs first, second and replacement IDs.')
            if any(not isinstance(action, str) or action not in self._actions for action in rule):
                raise ValueError('Combination rules may reference only fixed actions.')
            if any(not self._metadata[action]['planSafe'] for action in rule):
                raise ValueError('Every combination action must be approved for plans.')
            if len({self._metadata[action]['sourceId'] for action in rule}) != 1:
                raise ValueError('Combination actions must share one source.')
            first, second, replacement = rule
            if (first, second) in self._combinations and self._combinations[first, second] != replacement:
                raise ValueError('Conflicting combination rules.')
            self._combinations[first, second] = replacement

    def _validate_targets(self, targets):
        from intent_router import VERBS
        if not isinstance(targets, (list, tuple)) or len(targets) > 128:
            raise ValueError('Intent targets must be a bounded explicit sequence.')
        result = []
        for target in targets:
            if not isinstance(target, Mapping) or set(target) - _TARGET_FIELDS:
                raise ValueError('Unknown intent target fields.')
            if not _label(target.get('label'), 80):
                raise ValueError('Intent targets require a label.')
            aliases, verbs = target.get('aliases'), target.get('verbs')
            if not isinstance(aliases, (list, tuple)) or len(aliases) > 12 or not isinstance(verbs, Mapping):
                raise ValueError('Intent targets require bounded aliases and verb mappings.')
            if 'hide_without_stopping' in target and type(target['hide_without_stopping']) is not bool:
                raise ValueError('Playback preservation must be an explicit boolean.')
            names = []
            for alias in aliases:
                if not isinstance(alias, str) or len(alias) > 80 or not _ALIAS.fullmatch(alias):
                    raise ValueError('Intent aliases must be canonical bare target names.')
                if alias not in names:
                    names.append(alias)
            # Shared vocabulary can contain verbs unavailable in a smaller
            # installation. Such edges confer no authority and are omitted.
            known = {verb: action for verb, action in verbs.items()
                     if verb in VERBS and isinstance(action, str) and action in self._actions}
            if not names or not known:
                continue
            record = {'label': target['label'], 'aliases': names, 'verbs': known}
            if 'hide_without_stopping' in target:
                record['hide_without_stopping'] = target['hide_without_stopping']
            result.append(record)
        return tuple(result)

    def _require(self, action):
        if not isinstance(action, str) or action not in self._actions:
            raise ValueError('Unknown fixed capability.')

    def _availability_result(self, action):
        try:
            value = self._availability(action) if self._availability is not None else bool(shutil.which(self._actions[action][0]))
            if type(value) is bool:
                return value, '' if value else (self._actions[action][0]+' is not installed.' if self._availability is None else 'Required control is unavailable.')
            if isinstance(value, dict) and type(value.get('available')) is bool:
                reason = value.get('reason', '')
                if not isinstance(reason, str):
                    return False, 'Availability check returned an invalid result.'
                available = value['available']
                return available, reason if reason else ('' if available else 'Required control is unavailable.')
        except Exception:
            return False, 'Availability could not be checked.'
        return False, 'Availability check returned an invalid result.'

    def describe(self, action):
        self._require(action)
        available, reason = self._availability_result(action)
        return dict(self._metadata[action], id=action, label=self._labels[action],
                    available=available, availabilityReason=reason,
                    requires=self._actions[action][0])

    def plan_allowed(self):
        return frozenset(action for action, entry in self._metadata.items() if entry['planSafe'])

    def conflicts(self, ids):
        """Reject duplicate IDs or contradictory operations on one known source.

        The generic desktop fallback is not a concrete source. It cannot make
        unrelated controls conflict merely because their verbs are opposites.
        """
        if not isinstance(ids, (list, tuple)):
            return True
        if any(not isinstance(action, str) or action not in self._metadata for action in ids):
            return True
        if len(set(ids)) != len(ids):
            return True
        opposites = (frozenset({'mute', 'unmute'}), frozenset({'enable', 'disable'}),
                     frozenset({'pause', 'resume'}))
        for index, first in enumerate(ids):
            left = self._metadata[first]
            if left['sourceId'] == 'desktop':
                continue
            for second in ids[index + 1:]:
                right = self._metadata[second]
                if left['sourceId'] != right['sourceId']:
                    continue
                if left['operation'] == right['operation'] == 'set':
                    return True
                if frozenset((left['operation'], right['operation'])) in opposites:
                    return True
        return False

    def rewrite_plan(self, ids):
        if not isinstance(ids, (list, tuple)) or not 1 <= len(ids) <= 4:
            return None
        allowed = self.plan_allowed()
        if any(not isinstance(action, str) or action not in allowed for action in ids):
            return None
        if self.conflicts(ids):
            return None
        result, index = [], 0
        while index < len(ids):
            replacement = self._combinations.get(tuple(ids[index:index + 2])) if index + 1 < len(ids) else None
            if replacement is not None:
                result.append(replacement)
                index += 2
            else:
                result.append(ids[index])
                index += 1
        return None if self.conflicts(result) else tuple(result)

    def intent_targets(self):
        return copy.deepcopy(list(self._targets))

    def fingerprint(self, action):
        self._require(action)
        value = {'id': action, 'argv': self._actions[action], 'metadata': self._metadata[action]}
        raw = json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False).encode('utf-8')
        return hashlib.sha256(raw).hexdigest()

    def receipt(self, action, data):
        """Normalize an adapter result without claiming more than its evidence.

        State verification requires an explicit verified=True. An asynchronous
        acceptance remains accepted, even if its payload claims completion.
        Cancellation remains distinct from failure and never counts as success.
        """
        self._require(action)
        metadata = self._metadata[action]
        payload = dict(data) if isinstance(data, dict) else {}
        text = payload.get('text')
        valid = isinstance(data, dict) and isinstance(text, str) and bool(text.strip()) and payload.get('action') == ''
        if 'ok' in payload and type(payload['ok']) is not bool:
            valid = False
        cancelled = valid and payload.get('status') == 'cancelled' and payload.get('ok') is False
        failed = (not valid or bool(payload.get('error')) or bool(payload.get('errors'))
                  or payload.get('ok') is False or payload.get('status') in ('failed', 'error', 'cancelled'))
        verification = metadata['verification']
        if verification == 'state' and payload.get('verified') is not True:
            failed = True
        if cancelled:
            status, ok = 'cancelled', False
        elif failed:
            status, ok = 'failed', False
        else:
            status = {'accepted': 'accepted', 'process': 'completed', 'state': 'verified'}[verification]
            ok = True
        if not isinstance(text, str) or not text.strip():
            payload['text'] = 'The control did not return a valid completion receipt.'
        payload.update(action='', route='local', sourceId=metadata['sourceId'],
                       verification=verification, status=status, ok=ok)
        return payload
