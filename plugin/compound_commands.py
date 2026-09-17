"""Pure, bounded compound-command planning; nothing here executes a step.

propose(message, resolve_clause, labels, allowed_actions, normalize, rewrite=None)
returns None for noncompound input. Any recognized compound that cannot be fully
resolved returns a local explanation with no steps, never a partial plan.
Only an "and" target list inherits a verb; "then" and "but" need an explicit
action so a correction such as "open browser but terminal" is not guessed.

resolve_clause receives one complete request and returns a fixed action ID,
a proposal dictionary with that action, or None. Clarifications are unresolved.
rewrite, if provided, receives a tuple of resolved action IDs and returns a
list/tuple of replacement IDs, or None to reject. It is called once, before
final validation. For example, a source-aware adapter can replace
('cartoons_on', 'cartoons_mute') with ('cartoons_on_muted',) to avoid an audible
launch. The adapter, not this grammar, owns source-specific guarantees.
"""
import re
import unicodedata

MAX_STEPS = 4
MAX_LENGTH = 240
_CONNECTOR = re.compile(r'\b(?:and|then|but)\b')
_SPLIT = re.compile(r'\s+(?:and then|and|then|but)\s+')
_SEPARATORS = re.compile(r'\s+(and then|and|then|but)\s+')
# Longer verb phrases come first. Only this explicit vocabulary can be inherited
# by a coordinated target list; no arbitrary text is treated as a new verb.
_VERB = re.compile(
    r'^(show me|bring up|pull up|shut down|turn on|turn off|turn up|turn down|'
    r'open|launch|show|start|close|quit|exit|pause|resume|unpause|play|stop|hide|'
    r'mute|unmute|enable|disable|activate|deactivate|raise|lower|increase|decrease|'
    r'set|change|use|switch to|switch|apply|configure|adjust|toggle|focus|shut|turn|bring|pull|put)\s+(.+)$')
_FORBIDDEN = re.compile(
    r'\b(?:not|never|no|dont|cannot|cant|if|unless|when|after|before|later|tomorrow|'
    r'while|until|once|because|without|except|instead|maybe|perhaps)\b|n\x27t\b')
_PRONOUN = re.compile(r'\b(?:it|them)\b|^(?:this|that)(?: one)?$')
_SHELL = re.compile(r'[;\r\n&|`]|\$\(')
_OPPOSITES = frozenset(frozenset(pair) for pair in (
    ('mute', 'unmute'), ('pause_music', 'play_music'),
    ('volume_up', 'volume_down'), ('brightness_up', 'brightness_down'),
    ('keyboard_brightness_up', 'keyboard_brightness_down'),
    ('keyboard_brightness_off', 'keyboard_brightness_restore'),
    ('power_saver', 'power_balanced'), ('bar_show', 'bar_hide'),
    ('idle_inhibit', 'idle_allow'),
))


def _reply(reason, text, steps=()):
    return {'text': text, 'emote': 'working' if steps else 'reading',
            'route': 'local', 'action': '', 'steps': list(steps), 'reason': reason}


def _action(result):
    if isinstance(result, str):
        return result or None
    if isinstance(result, dict) and result.get('matchType') != 'clarify':
        action = result.get('action')
        return action if isinstance(action, str) and action else None
    return None


def _conflict(first, second):
    if frozenset((first, second)) in _OPPOSITES:
        return True
    for suffix, opposite in (('_on', '_off'), ('_on', '_close'), ('_open', '_close'),
                             ('_mute', '_unmute'), ('_pause', '_resume')):
        if first.endswith(suffix) and second == first[:-len(suffix)] + opposite:
            return True
        if second.endswith(suffix) and first == second[:-len(suffix)] + opposite:
            return True
    return first == 'close_' + second or second == 'close_' + first


def propose(message, resolve_clause, labels, allowed_actions, normalize, rewrite=None):
    """Return a complete review-only plan, a local rejection, or no compound.

    This parser has no state, observation, execution, or model access. It relies
    on the caller's fixed action allowlist, trustworthy labels and local-only
    callbacks. Unknown modifiers remain part of the clause sent to the resolver.
    """
    if not is_candidate(message,normalize):return None
    probe = unicodedata.normalize('NFKC', message).casefold()
    failure = lambda reason, text: _reply(reason, text)
    if len(message) > MAX_LENGTH:
        return failure('too-long', 'Please shorten the request to at most four explicit steps.')
    if _SHELL.search(probe) or any(c in probe for c in ('"', '“', '”', ':')):
        return failure('unsafe-compound', 'Please give separate, unquoted commands joined with and or then.')
    quoted = probe.strip().replace('’', "'")
    if quoted.startswith("'") or quoted.endswith("'") or re.search(r"\s'|'\s", quoted):
        return failure('unsafe-compound', 'Quoted text is not a command plan. Please state the steps directly.')
    text = normalize(message)
    if not isinstance(text, str) or not text:
        return failure('unsafe-compound', 'I could not read a complete command plan. Please state each step directly.')
    if _FORBIDDEN.search(text.replace('do not disturb', 'dnd')):
        return failure('unsafe-compound', 'Please use immediate, explicit steps without conditions or negation.')
    # Permit a punctuation comma immediately before an explicit connector only.
    # Commas alone never create an inferred target list or a command boundary.
    text = re.sub(r',\s+(?=(?:and then|and|then|but)\b)', ' ', text)
    parts = _SEPARATORS.split(text)
    clauses, separators = parts[::2], parts[1::2]
    if len(clauses) < 2:
        return failure('ambiguous-compound', 'Please name each action and target in separate steps.')
    if len(clauses) > MAX_STEPS:
        return failure('too-many-steps', 'I can prepare at most four steps at a time. Please split this request.')
    if any(not clause.strip() or _CONNECTOR.search(clause) or ',' in clause for clause in clauses):
        return failure('ambiguous-compound', 'I could not separate every step clearly. Please repeat each action and target.')
    try:
        # If the whole string names one known target/action, splitting it could
        # mistake a connector-bearing target name for a sequence of commands.
        if _action(resolve_clause(text)):
            return failure('ambiguous-compound', 'This wording also matches one command. Please clarify whether you want one action or separate steps.')
    except Exception:
        return failure('unresolved-step', 'I could not resolve the full request locally. No steps are prepared.')
    actions = []
    inherited = None
    for index, clause in enumerate(clauses):
        clause = normalize(clause.strip())
        if not isinstance(clause, str) or not clause:
            return failure('unresolved-step', 'I could not read every step as a complete command.')
        clause = re.sub(r'^(?:just|i want to|i need to|let me|help me) ', '', clause, count=1)
        explicit = _VERB.fullmatch(clause)
        if explicit:
            inherited, target = explicit.groups()
            complete = clause
        elif inherited and separators[index - 1] == 'and':
            target = clause
            complete = inherited + ' ' + clause
        else:
            return failure('unresolved-step', 'Please start each request with an explicit action and target.')
        if _PRONOUN.search(target):
            return failure('ambiguous-target', 'Please name the target for every step instead of using a pronoun.')
        try:
            action = _action(resolve_clause(complete))
        except Exception:
            action = None
        if action is None:
            return failure('unresolved-step', 'I could not resolve every step. Please name each action and target explicitly.')
        if action not in allowed_actions or not isinstance(labels.get(action), str):
            return failure('unsupported-action', 'One requested step is not available in the local command catalogue.')
        actions.append(action)
    if len(set(actions)) != len(actions):
        return failure('duplicate-step', 'The request repeats a command. Please simplify the steps before running them.')
    if any(_conflict(first, second) for index, first in enumerate(actions) for second in actions[index + 1:]):
        return failure('conflicting-steps', 'Some requested steps reverse one another. Please choose the final state you want.')
    if rewrite is not None:
        try:
            replacement = rewrite(tuple(actions))
        except Exception:
            return failure('rewrite-rejected', 'I could not prepare a safe combined operation. No steps are prepared.')
        if replacement is None:
            return failure('rewrite-rejected', 'These steps cannot be safely combined in that order. No steps are prepared.')
        if not isinstance(replacement, (list, tuple)) or not 1 <= len(replacement) <= MAX_STEPS:
            return failure('invalid-rewrite', 'The combined operation could not be validated. No steps are prepared.')
        actions = list(replacement)
    if any(not isinstance(action, str) or action not in allowed_actions
           or not isinstance(labels.get(action), str) for action in actions):
        return failure('unsupported-action', 'One combined step is outside the local command catalogue. No steps are prepared.')
    if len(set(actions)) != len(actions):
        return failure('duplicate-step', 'The request repeats a command. Please simplify the steps before running them.')
    if any(_conflict(first, second) for index, first in enumerate(actions) for second in actions[index + 1:]):
        return failure('conflicting-steps', 'Some requested steps reverse one another. Please choose the final state you want.')
    steps = [{'action': action, 'label': labels[action]} for action in actions]
    return _reply('compound-plan', 'Ready to review ' + str(len(steps)) + ' step' + ('s' if len(steps) != 1 else '') + '. Nothing has run yet.', steps)


def is_candidate(message,normalize):
    if not isinstance(message, str):
        return False
    probe = unicodedata.normalize('NFKC', message).casefold()
    if not _CONNECTOR.search(probe) and not _SHELL.search(probe):
        return False
    # Conjunctions occur in normal conversation, routine definitions and quoted
    # explanations too. Only an explicit command-leading first clause belongs
    # to this planner. Inspect the first clause separately so unsafe delimiters
    # later in an actual command still receive a local rejection.
    first_raw = re.split(r'\b(?:and|then|but)\b|[;\r\n&|]', probe, maxsplit=1)[0]
    first_raw = first_raw.strip().strip('\"“”`').strip()
    if first_raw.startswith("'"):
        first_raw = first_raw[1:]
    first = normalize(first_raw) or first_raw
    first = re.sub(r'^(?:just|i want to|i need to|let me|help me) ', '', first, count=1)
    first = re.sub(r"^(?:do not|don't|dont|never|not) ", '', first, count=1)
    if not _VERB.fullmatch(first):
        return False
    return True
