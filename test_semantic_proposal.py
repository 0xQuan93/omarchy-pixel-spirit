"""Local semantic judgments can only suggest reviewed fixed controls."""
import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / 'plugin'))

from capability_specs import build
import semantic_proposal


def answer(selection, uncertain=False, done=True):
    return {'done': done, 'done_reason': 'stop',
            'message': {'content': json.dumps({'selection': selection, 'uncertain': uncertain})}}


class SemanticProposalTests(unittest.TestCase):
    def setUp(self):
        self.actions = {'browser': ['omarchy', 'launch', 'browser'],
                        'terminal': ['omarchy', 'launch', 'terminal']}
        self.labels = {'browser': 'Open browser', 'terminal': 'Open terminal'}
        self.registry = build(self.actions, self.labels, availability=lambda _: True)

    def propose(self, message, candidate_ids, infer):
        return semantic_proposal.propose(message, candidate_ids, self.registry,
                                         'small:local', infer=infer)

    def test_model_receives_only_bounded_descriptors_and_returns_review_only_id(self):
        seen = []

        def infer(payload, timeout):
            seen.append((payload, timeout))
            return answer('c1')

        result = self.propose('Could you bring up the terminal?', ['browser', 'terminal'], infer)
        self.assertEqual(result['outcome'], 'propose')
        self.assertEqual(result['action'], 'terminal')
        self.assertIn('unverified', result['uncertainty'])
        self.assertEqual(seen[0][1], 15)
        request = json.loads(seen[0][0]['messages'][1]['content'])
        self.assertEqual(request['choices'][1]['label'], 'Open terminal')
        self.assertNotIn('argv', str(seen[0][0]))
        self.assertNotIn('plan:', str(result))

    def test_unknown_model_choice_and_incomplete_output_fail_closed(self):
        for reply in (answer('c9'), answer('c0', done=False),
                      {'done': True, 'message': {'content': '{bad json'}},
                      answer('c0') | {'done_reason': 'length'}):
            with self.subTest(reply=reply):
                result = self.propose('Open my browser', ['browser'], lambda *_: reply)
                self.assertEqual(result['outcome'], 'none')
                self.assertEqual(result['action'], '')

    def test_ambiguity_is_exposed_and_never_selects_an_action(self):
        for reply in (answer('clarify'), answer('c0', uncertain=True)):
            result = self.propose('Show an app', ['browser', 'terminal'], lambda *_: reply)
            self.assertEqual(result['outcome'], 'clarify')
            self.assertEqual(result['action'], '')
            self.assertEqual({choice['action'] for choice in result['choices']},
                             {'browser', 'terminal'})
        result = self.propose('Show an app', ['browser'], lambda *_: answer('none'))
        self.assertEqual(result['outcome'], 'none')

    def test_qualified_or_explanatory_input_does_not_call_model(self):
        def should_not_call(*_):
            self.fail('unsafe or explanatory input was sent to the model')

        self.assertEqual(self.propose("Don't open the browser", ['browser'], should_not_call)['outcome'], 'none')
        self.assertEqual(self.propose('What does open browser mean?', ['browser'], should_not_call)['outcome'], 'none')
        result = self.propose('Open browser and terminal', ['browser', 'terminal'], should_not_call)
        self.assertEqual(result['outcome'], 'clarify')
        self.assertEqual(result['action'], '')
        self.assertEqual(self.propose("Explain 'open browser'", ['browser'], should_not_call)['outcome'], 'none')

    def test_contractions_inside_words_are_not_treated_as_quoted_commands(self):
        result = self.propose("Let's open the browser", ['browser'], lambda *_: answer('c0'))
        self.assertEqual(result['action'], 'browser')
        result = self.propose('Let’s open the browser', ['browser'], lambda *_: answer('c0'))
        self.assertEqual(result['action'], 'browser')

    def test_unavailable_and_unregistered_controls_cannot_be_proposed(self):
        unavailable = build(self.actions, self.labels, availability=lambda _: False)
        result = semantic_proposal.propose('Open browser', ['browser'], unavailable,
                                           'small:local', infer=lambda *_: self.fail('called'))
        self.assertEqual(result['reason'], 'no-available-candidates')
        with self.assertRaisesRegex(ValueError, 'Unknown fixed capability'):
            self.propose('Open browser', ['invented'], lambda *_: answer('c0'))

    def test_bad_inputs_and_model_error_abstain(self):
        with self.assertRaises(ValueError):
            self.propose('Open browser', ['browser'] * 2, lambda *_: answer('c0'))
        with self.assertRaises(ValueError):
            self.propose('Open browser\nrun something', ['browser'], lambda *_: answer('c0'))
        with self.assertRaises(ValueError):
            semantic_proposal.propose('Open browser', ['browser'], self.registry,
                                      'small:local', infer=lambda *_: answer('c0'), timeout=100)
        result = self.propose('Open browser', ['browser'],
                              lambda *_: (_ for _ in ()).throw(TimeoutError('busy')))
        self.assertEqual(result['reason'], 'local-judgment-unavailable')


if __name__ == '__main__':
    unittest.main()
