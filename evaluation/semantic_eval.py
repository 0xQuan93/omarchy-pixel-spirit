"""Reproducible, no-action pilot for optional Wisp semantic proposals.

Run `python3 -B evaluation/semantic_eval.py --dry-run` to inspect the fixed
corpus. `--live` asks only the already installed localhost Ollama model. The
registry is a semantic fixture: all listed controls are marked available so
this measures interpretation rather than the current machine's readiness.
No command is executed and no chat or model response is saved.
"""
import argparse
import json
import statistics
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'plugin'))

from capabilities import ACTIONS, LABELS
from capability_specs import build
from compound_commands import is_candidate
from intent_router import resolve
from semantic_proposal import MAX_CANDIDATES, propose
from smart_commands import match, normalize

CASES = Path(__file__).with_name('semantic_cases.json')
RADIO_ACTIONS = {
    'example_radio_pause': ['example-radio-control', 'pause'],
    'example_radio_resume': ['example-radio-control', 'resume'],
    'example_radio_close': ['example-radio-control', 'close'],
}
RADIO_LABELS = {
    'example_radio_pause': 'Pause Example Radio',
    'example_radio_resume': 'Resume Example Radio',
    'example_radio_close': 'Close Example Radio',
}
RADIO_METADATA = {action: {'sourceId': 'example.radio', 'sourceLabel': 'Example Radio',
                           'operation': action.removeprefix('example_radio_'),
                           'planSafe': False, 'verification': 'state'}
                  for action in RADIO_ACTIONS}


def fixture_registry():
    """Register public Wisp IDs plus a reviewed, inert named-source fixture."""
    return build(dict(ACTIONS) | RADIO_ACTIONS, dict(LABELS) | RADIO_LABELS,
                 availability=lambda _: True, extra_metadata=RADIO_METADATA)


def load_cases(path=CASES, registry=None):
    registry = registry or fixture_registry()
    cases = json.loads(Path(path).read_text())
    if not isinstance(cases, list) or not 1 <= len(cases) <= 64:
        raise ValueError('Expected a bounded semantic evaluation list.')
    seen = set()
    for case in cases:
        if not isinstance(case, dict) or set(case) != {'id', 'request', 'candidates', 'expect', 'tag'}:
            raise ValueError('Invalid semantic evaluation case.')
        ident, request, candidates, expected = (case[key] for key in
                                                 ('id', 'request', 'candidates', 'expect'))
        if (not isinstance(ident, str) or not ident.isidentifier() or ident in seen
                or not isinstance(request, str) or not request.strip() or len(request) > 240
                or not isinstance(candidates, list) or not 1 <= len(candidates) <= MAX_CANDIDATES
                or any(not isinstance(action, str) for action in candidates)
                or len(set(candidates)) != len(candidates)
                or not isinstance(case['tag'], str) or not case['tag']):
            raise ValueError('Invalid semantic evaluation case.')
        seen.add(ident)
        for action in candidates:
            registry.fingerprint(action)
        if (not isinstance(expected, dict) or expected.get('outcome') not in
                {'propose', 'clarify', 'none'} or set(expected) !=
                ({'outcome', 'action'} if expected['outcome'] == 'propose' else {'outcome'})
                or expected.get('action', candidates[0]) not in candidates):
            raise ValueError('Invalid semantic evaluation target.')
    return cases


def assess(case, result):
    """Separate false action proposals from safe misses and exact matches."""
    expected = case['expect']
    observed = result['outcome']
    if observed == 'propose':
        return ('correct' if expected['outcome'] == 'propose'
                and result['action'] == expected['action'] else 'false-proposal')
    if observed == expected['outcome']:
        return 'correct'
    return 'safe-abstention'


def deterministic_route(case, registry):
    """Tag existing local matches; they cannot count as semantic uplift."""
    message = case['request']
    actions, labels = dict(ACTIONS) | RADIO_ACTIONS, dict(LABELS) | RADIO_LABELS
    if match(message, actions):
        return 'fixed-phrase'
    if resolve(message, actions, labels, normalize, extra_targets=registry.intent_targets()) is not None:
        return 'composed-intent'
    if is_candidate(message, normalize):
        return 'compound-parser'
    return ''


def run(cases, registry, model, timeout=15):
    from inference import request

    rows = []
    for case in cases:
        calls = []
        errors = []
        baseline = deterministic_route(case, registry)

        def local_infer(payload, limit):
            started = time.monotonic()
            try:
                return request(payload, timeout=limit, background=True)
            except Exception as error:
                errors.append(type(error).__name__)
                raise
            finally:
                calls.append(round((time.monotonic() - started) * 1000))

        started = time.monotonic()
        result = propose(case['request'], case['candidates'], registry, model,
                         infer=local_infer, timeout=timeout)
        rows.append({'id': case['id'], 'tag': case['tag'], 'expected': case['expect'],
                     'deterministicRoute': baseline,
                     'observed': {'outcome': result['outcome'], 'action': result['action'],
                                  'reason': result['reason']},
                     'verdict': assess(case, result),
                     'elapsedMs': round((time.monotonic() - started) * 1000),
                     'modelMs': calls[0] if calls else None,
                     'modelError': errors[0] if errors else None})
    durations = [row['modelMs'] for row in rows if row['modelMs'] is not None]
    eligible = [row for row in rows if not row['deterministicRoute']]
    return {'cases': len(rows), 'correct': sum(row['verdict'] == 'correct' for row in rows),
            'falseProposals': sum(row['verdict'] == 'false-proposal' for row in rows),
            'safeAbstentions': sum(row['verdict'] == 'safe-abstention' for row in rows),
            'eligibleCases': len(eligible),
            'eligibleCorrect': sum(row['verdict'] == 'correct' for row in eligible),
            'eligibleFalseProposals': sum(row['verdict'] == 'false-proposal' for row in eligible),
            'correctNovelProposals': sum(row['verdict'] == 'correct' and
                                         row['expected']['outcome'] == 'propose' for row in eligible),
            'modelCalls': len(durations),
            'unavailable': sum(row['observed']['reason'] == 'local-judgment-unavailable' for row in rows),
            'medianModelMs': round(statistics.median(durations)) if durations else None,
            'maxModelMs': max(durations) if durations else None,
            'rows': rows}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument('--dry-run', action='store_true', help='validate and count cases without model calls')
    mode.add_argument('--live', action='store_true', help='evaluate with the installed localhost Ollama model')
    parser.add_argument('--model', default='qwen3.5:4b')
    parser.add_argument('--timeout', type=float, default=15)
    parser.add_argument('--case', action='append', default=[], help='run only a named case; repeatable')
    parser.add_argument('--eligible-only', action='store_true',
                        help='skip cases already handled by fixed/composed/compound routes')
    parser.add_argument('--json', action='store_true', help='print one machine-readable report')
    args = parser.parse_args(argv)
    registry = fixture_registry()
    cases = load_cases(registry=registry)
    if args.case:
        names = set(args.case)
        unknown = names - {case['id'] for case in cases}
        if unknown:
            parser.error('unknown case: ' + ', '.join(sorted(unknown)))
        cases = [case for case in cases if case['id'] in names]
    if args.eligible_only:
        cases = [case for case in cases if not deterministic_route(case, registry)]
    if args.dry_run:
        eligible = sum(not deterministic_route(case, registry) for case in cases)
        print(f'{len(cases)} fixed cases, {eligible} without an existing deterministic route; '
              f'{sum(c["expect"]["outcome"] == "propose" for c in cases)} positive, no model calls')
        return 0
    report = run(cases, registry, args.model, args.timeout)
    if args.json:
        print(json.dumps(report, indent=2))
    else:
        print(f'{report["cases"]} cases; {report["correct"]} exact; '
              f'{report["falseProposals"]} false proposals; '
              f'{report["safeAbstentions"]} safe abstentions; '
              f'{report["unavailable"]} unavailable')
        print(f'After deterministic routes: {report["eligibleCases"]} eligible, '
              f'{report["correctNovelProposals"]} correct new proposals, '
              f'{report["eligibleFalseProposals"]} false proposals')
        print(f'Model calls: {report["modelCalls"]}; median {report["medianModelMs"]} ms; '
              f'max {report["maxModelMs"]} ms')
        for row in report['rows']:
            print(f'{row["id"]:25} {row["verdict"]:16} '
                  f'{row["observed"]["outcome"]}:{row["observed"]["action"] or "-"} '
                  f'({row["elapsedMs"]} ms)')
    return 2 if report['unavailable'] == report['modelCalls'] and report['modelCalls'] else 0


if __name__ == '__main__':
    raise SystemExit(main())
