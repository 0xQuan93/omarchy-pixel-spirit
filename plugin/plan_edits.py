"""Pure edits to a pending, review-only plan; never persist or execute a step.

The caller supplies the pending IDs, fixed labels, local clause resolver and
reviewed capability registry, and owns issuing a replacement confirmation token.
An empty-plan result means the last step was explicitly removed: invalidate the
old token. Other rejected edits leave the previous plan for the caller to retain.
"""
import re
import unicodedata
from compound_commands import _conflict
from smart_commands import normalize

MAX_STEPS = 4
_NUMBERS = {'1': 0, 'one': 0, 'first': 0, '2': 1, 'two': 1, 'second': 1,
            '3': 2, 'three': 2, 'third': 2, '4': 3, 'four': 3, 'fourth': 3}
_FORBIDDEN = re.compile(r"\b(?:not|never|dont|cannot|if|unless|when|after|before|later|tomorrow|then|and|or|but|without|until|because)\b|n't\b")
_PRONOUNS = frozenset({'it', 'that', 'this', 'them', 'this one', 'that one'})
_START = re.compile(r'^(skip|remove|only|add|also|replace)\b')
_ORDINAL = re.compile(r'^(?:the )?(?:(?:step(?: number)? )?([a-z0-9]+)|([a-z0-9]+) (?:step|one))$')


def _reply(reason, text, steps=()):
    return {'text': text, 'action': '', 'emote': 'working' if steps else 'reading',
            'route': 'local', 'planEdit': True, 'steps': list(steps), 'reason': reason}


def _candidate_ids(result, choices=False):
    if isinstance(result, str):
        return [result] if result else []
    if not isinstance(result, dict):
        return []
    action = result.get('action')
    if result.get('matchType') != 'clarify' and isinstance(action, str) and action:
        return [action]
    if choices and isinstance(result.get('choices'), list):
        return [c['action'] for c in result['choices'][:4]
                if isinstance(c, dict) and isinstance(c.get('action'), str)]
    return []


def _resolve(command, resolve_clause):
    try:
        ids = _candidate_ids(resolve_clause(command))
    except Exception:
        return None
    return ids[0] if len(ids) == 1 else None


def _source(action, registry):
    try:
        source = registry.describe(action).get('sourceId')
    except Exception:
        return None
    # The conservative registry fallback is a category, not a unique target.
    return source if isinstance(source, str) and source and source != 'desktop' else None


def _select(selector, ids, resolve_clause, registry):
    """Return matching indexes; an empty/ambiguous set never chooses a step."""
    if selector in _PRONOUNS:
        return []
    ordinal = _ORDINAL.fullmatch(selector)
    if ordinal:
        number = ordinal[1] or ordinal[2]
        if number in _NUMBERS:
            index = _NUMBERS[number]
            return [index] if index < len(ids) else []
        # Out-of-range step syntax must not turn into a target lookup.
        if selector.startswith(('step ', 'the step ')) or selector.endswith((' step', ' one')) or number.isdigit():
            return []
    try:
        direct = _candidate_ids(resolve_clause(selector))
    except Exception:
        direct = []
    direct_indexes = [index for index, action in enumerate(ids) if action in direct]
    if direct_indexes:
        return direct_indexes
    candidates = set(direct)
    for phrase in ('open ' + selector, 'close ' + selector, 'mute ' + selector):
        try:
            candidates.update(_candidate_ids(resolve_clause(phrase), choices=True))
        except Exception:
            continue
    sources = {_source(action, registry) for action in candidates} - {None}
    return [index for index, action in enumerate(ids)
            if action in candidates or _source(action, registry) in sources]


def _validate(ids, labels, registry):
    if not isinstance(ids, (list, tuple)) or not 1 <= len(ids) <= MAX_STEPS:
        return None, 'step-limit'
    try:
        allowed = registry.plan_allowed()
    except Exception:
        return None, 'invalid-plan'
    if any(not isinstance(action, str) or action not in allowed
           or not isinstance(labels.get(action), str) for action in ids):
        return None, 'unsupported-action'
    if len(set(ids)) != len(ids):
        return None, 'duplicate-step'
    if any(_conflict(first, second) for i, first in enumerate(ids) for second in ids[i + 1:]):
        return None, 'conflicting-steps'
    return list(ids), ''


def propose(message, ids, labels, resolve_clause, registry):
    """Return an edited plan, a local explanation, or None for a non-edit.

    Supported forms: remove/skip <step or target>, only <command>, add/also
    <command>, replace <step or target> with <command>, <command> instead.
    Plain commands are left to the caller's normal command-routing path.
    """
    if not isinstance(message, str):
        return None
    raw = unicodedata.normalize('NFKC', message).casefold().strip()
    text = normalize(message)
    candidate = text if isinstance(text, str) and text else raw
    candidate = re.sub(r'^(?:actually|just) ', '', candidate, count=1)
    if not _START.match(candidate) and not candidate.endswith(' instead'):
        return None
    if (len(message) > 240 or not text or any(c in raw for c in ('"', '“', '”', '`', ';', '\n', '\r', ':'))
            or _FORBIDDEN.search(candidate.replace('do not disturb', 'dnd'))):
        return _reply('unsafe-edit', 'Please give one explicit edit without quotes, conditions or additional actions.')
    current, problem = _validate(ids, labels, registry)
    if problem:
        return _reply('invalid-plan', 'This pending plan can no longer be edited. Please prepare a new plan.')
    remove = re.fullmatch(r'(?:skip|remove) (.+)', candidate)
    replace = re.fullmatch(r'replace (.+?) with (.+)', candidate)
    only = re.fullmatch(r'only (.+)', candidate)
    append = re.fullmatch(r'(?:add|also) (.+)', candidate)
    instead = re.fullmatch(r'(.+) instead', candidate)
    if remove or replace:
        selector = (remove or replace)[1]
        indexes = _select(selector, current, resolve_clause, registry)
        if len(indexes) != 1:
            return _reply('ambiguous-selector', 'Please name one step number or one unambiguous target from the pending plan.')
        if remove:
            del current[indexes[0]]
            if not current:
                return _reply('empty-plan', 'No steps remain. The pending plan should be cancelled.')
        else:
            action = _resolve(replace[2], resolve_clause)
            if action is None:
                return _reply('unresolved-command', 'I could not resolve the replacement. Please give one complete command.')
            current[indexes[0]] = action
    elif only or append or instead:
        command = (only or append or instead)[1]
        action = _resolve(command, resolve_clause)
        if action is None:
            return _reply('unresolved-command', 'I could not resolve that edit. Please give one complete command with an explicit target.')
        if only:
            current = [action]
        elif append:
            current.append(action)
        else:
            source = _source(action, registry)
            indexes = [index for index, pending in enumerate(current)
                       if pending == action or (source is not None and _source(pending, registry) == source)]
            if len(indexes) != 1:
                return _reply('ambiguous-selector', 'Please say which step to replace; this command does not identify exactly one matching source.')
            current[indexes[0]] = action
    else:
        return _reply('unresolved-edit', 'Please specify a step to remove, a command to add, or a replacement.')
    updated, problem = _validate(current, labels, registry)
    if problem:
        return _reply(problem, 'That edit would create an unsupported, repeated, conflicting or oversized plan. Please revise it.')
    try:
        rewritten = registry.rewrite_plan(tuple(updated))
    except Exception:
        rewritten = None
    updated, problem = _validate(rewritten, labels, registry)
    if problem:
        return _reply('rewrite-rejected', 'The edited plan could not be safely combined. No replacement plan is prepared.')
    steps = [{'action': action, 'label': labels[action]} for action in updated]
    return _reply('plan-edited', 'Updated the plan for review. Nothing has run yet.', steps)
