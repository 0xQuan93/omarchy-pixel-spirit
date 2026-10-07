"""The fixed pilot corpus and safety metric stay honest as it evolves."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from evaluation import semantic_eval


class SemanticEvaluationTests(unittest.TestCase):
    def test_corpus_is_registered_bounded_and_covers_risk_families(self):
        cases = semantic_eval.load_cases()
        ids = {case['id'] for case in cases}
        tags = {case['tag'] for case in cases}
        self.assertIn('push_up', ids)
        self.assertIn('play_some_music', ids)
        self.assertTrue({'everyday', 'negation', 'hypothetical', 'multiple',
                         'source-specific', 'source-ambiguous'} <= tags)
        self.assertGreaterEqual(len(cases), 20)

    def test_wrong_action_is_false_proposal_even_when_control_is_registered(self):
        case = {'expect': {'outcome': 'propose', 'action': 'play_music'}}
        self.assertEqual(semantic_eval.assess(case, {'outcome': 'propose',
                                                     'action': 'play_pause'}), 'false-proposal')
        case['expect'] = {'outcome': 'clarify'}
        self.assertEqual(semantic_eval.assess(case, {'outcome': 'propose',
                                                     'action': 'volume_up'}), 'false-proposal')
        self.assertEqual(semantic_eval.assess(case, {'outcome': 'none',
                                                     'action': ''}), 'safe-abstention')


if __name__ == '__main__':
    unittest.main()
