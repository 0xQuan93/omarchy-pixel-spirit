"""User request learning exercises the real broker, with no model or desktop effects."""
from contextlib import ExitStack
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0,str(Path(__file__).parent/'plugin'))
import brain
import learned_phrases as learned


def answer(text='Windows tile to share the screen.',action='',**extra):
    return {'message':{'content':json.dumps(dict(text=text,action=action,emote='reading',**extra))},'done_reason':'stop'}


class LearningIntegration(unittest.TestCase):
    def setUp(self):
        self.stack=ExitStack();self.addCleanup(self.stack.close)
        self.stack.enter_context(patch.object(sys,'argv',['brain.py']))
        self.base=Path(self.stack.enter_context(tempfile.TemporaryDirectory()))
        for target,value in [('brain.BASE',self.base),('growth.memory_context',{}),
                             ('identity.profile',{'name':'Test','model':'test-model'}),
                             ('awareness.context',{}),('playroom.context',{}),('brain.context',{})]:
            self.stack.enter_context(patch(target,value) if target=='brain.BASE' else patch(target,return_value=value))
        self.stack.enter_context(patch('shutil.which',return_value='/test/tool'))
        self.stack.enter_context(patch('command_bank.defaults',return_value=(self.base/'config',self.base/'system',self.base)))
        self.effects=self.stack.enter_context(patch.object(brain,'execute',side_effect=AssertionError('Unexpected desktop effect')))
        self.model=self.stack.enter_context(patch('inference.request',return_value=answer()))
        self.message='Explain the concept of tiling window managers'

    def test_first_request_learns_and_repeat_skips_model_and_context(self):
        first=brain.chat(self.message)
        self.assertEqual(first['route'],'model');self.assertEqual(first['learnedKind'],'answer')
        with patch('growth.memory_context',side_effect=AssertionError('Rebuilt model context')):
            repeated=brain.chat(self.message)
        self.assertEqual(repeated['route'],'learned');self.assertIn('Saved local AI reply',repeated['text'])
        self.assertIn('Windows tile',repeated['text']);self.assertEqual(self.model.call_count,1)
        self.assertEqual(len(brain.read('history.json',[])),4)
        self.effects.assert_not_called()

    def test_action_repeat_is_fresh_run_proposal_not_execution(self):
        self.model.return_value=answer(action='mute')
        phrase='Would you help silence this machine?'
        first=brain.chat(phrase);second=brain.chat(phrase)
        self.assertEqual(first['learnedKind'],'action');self.assertEqual(second['action'],'mute')
        self.assertIn('Tap Run',second['text']);self.assertEqual(second['route'],'learned')
        self.assertEqual(self.model.call_count,1);self.effects.assert_not_called()

    def test_refresh_and_forget_use_stored_request_and_relearn(self):
        first=brain.chat(self.message)
        self.model.return_value=answer('An updated explanation.')
        args=['learning','refresh',first['learnedKey'],'eco']
        with patch.object(brain,'read_request',return_value=args): updated=brain.main()
        self.assertEqual(updated['route'],'model');self.assertEqual(self.model.call_count,2)
        self.assertEqual(self.model.call_args.args[0]['keep_alive'],0)
        self.assertIn('updated explanation',brain.chat(self.message)['text'])
        with patch.object(brain,'read_request',return_value=['learning','forget',first['learnedKey']]): brain.main()
        brain.chat(self.message);self.assertEqual(self.model.call_count,3)

    def test_omarchy_help_has_local_resources_without_model(self):
        local=self.base/'system/shell/README.md';local.parent.mkdir(parents=True);local.write_text('Local guide')
        with patch('omarchy_help._roots',return_value=(self.base/'system',self.base/'config')):
            for phrase in ('tell me about Omarchy','help me learn Omarchy','Omarchy docs','how do I change themes in Omarchy'):
                reply=brain.chat(phrase)
                self.assertEqual(reply['route'],'local');self.assertTrue(reply['resources'])
                if phrase=='tell me about Omarchy':self.assertTrue(any(r['kind']=='local' for r in reply['resources']))
                self.assertIn('omarchy.',reply['helpTopic'])
        self.model.assert_not_called();self.effects.assert_not_called()

    def test_model_cannot_inject_resources_plans_or_learning_controls(self):
        self.model.return_value=answer(resources=[{'url':'file:///secret'}],helpTopic='omarchy.docs',
                                      choices=[{'action':'browser'}],steps=[{'action':'browser'}],
                                      learnedKey='bad-key',route='local',autoCommand=True)
        result=brain.chat(self.message)
        for field in ('resources','helpTopic','choices','steps','autoCommand'):self.assertNotIn(field,result)
        self.assertNotEqual(result['learnedKey'],'bad-key');self.assertEqual(result['route'],'model')
        repeated=brain.chat(self.message)
        for field in ('resources','helpTopic','choices','steps','autoCommand'):self.assertNotIn(field,repeated)

    def test_failed_incomplete_or_invalid_model_result_is_not_a_saved_answer(self):
        cases=[TimeoutError('busy'),{'message':{'content':'invalid'}},
               dict(answer(),done_reason='length'),dict(answer(),done=False),answer(ok=False)]
        for index,case in enumerate(cases):
            phrase=self.message+' '+str(index)
            self.model.reset_mock()
            self.model.side_effect=case if isinstance(case,Exception) else None
            self.model.return_value=case
            first=brain.chat(phrase);second=brain.chat(phrase)
            self.assertEqual(first['learnedKind'],'unresolved');self.assertEqual(second['learnedKind'],'unresolved')
            self.assertEqual(second['action'],'');self.assertEqual(self.model.call_count,1)
            self.assertIn('Ask again',second['text'])

    def test_authored_route_overrides_old_learned_interpretation(self):
        ticket=learned.begin(self.base,'open browser')
        learned.complete(self.base,'open browser',ticket,dict(text='Wrong old answer',emote='idle',action=''),brain.controls())
        result=brain.chat('open browser')
        self.assertEqual(result['action'],'browser');self.assertEqual(result['route'],'local')
        self.model.assert_not_called()

    def test_internal_room_or_naming_requests_do_not_learn(self):
        self.model.return_value=answer('Try reading.',roomActivity='read')
        for _ in range(2):self.assertEqual(brain.chat(self.message,learn=False)['roomActivity'],'read')
        self.assertEqual(self.model.call_count,2);self.assertFalse((self.base/learned.FILE).exists())

    def test_learning_transport_bounds(self):
        for args in (['learning','forget','a'*64],['learning','refresh','a'*64,'eco']):
            self.assertEqual(brain.read_request(io.BytesIO((json.dumps(args)+'\n').encode())),args)
        for args in (['learning'],['learning','refresh']):
            with self.assertRaises(ValueError):brain.read_request(io.BytesIO((json.dumps(args)+'\n').encode()))
        for args in (['learning','forget','bad'],['learning','refresh','a'*64,'arbitrary']):
            with patch.object(brain,'read_request',return_value=args),self.assertRaises(ValueError):brain.main()

if __name__=='__main__':unittest.main()
