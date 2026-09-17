"""Independent progress/cancellation tests; all plans use inert callbacks."""
from pathlib import Path
import sys
import tempfile
import time
import unittest
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).parent/'plugin'))
import plan_runtime as runtime
import command_plans as plans
from storage import get, put

TOKEN = 'plan:' + 'a'*32
FOREIGN = 'plan:' + 'b'*32


class PlanRuntimeTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory(); self.addCleanup(temp.cleanup)
        self.base = Path(temp.name)
        self.labels = {'first': 'First control', 'second': 'Second control'}
        p = patch.object(runtime, '_start', return_value='original-process-start')
        p.start(); self.addCleanup(p.stop)

    def begin(self):
        runtime.begin(self.base, TOKEN, list(self.labels), self.labels)

    def prepare(self):
        registry = Mock()
        registry.plan_allowed.return_value = frozenset(self.labels)
        registry.fingerprint.side_effect = lambda action: 'fingerprint-' + action
        registry.rewrite_plan.side_effect = tuple
        put(self.base/'command-plan.json', {'token':TOKEN[5:], 'created':time.time(),
            'actions':list(self.labels), 'fingerprints':{a:'fingerprint-'+a for a in self.labels}}, False)
        return registry

    def execute(self, callback):
        registry = self.prepare()
        return plans.execute(TOKEN, self.base, {a:['inert'] for a in self.labels},
                             self.labels, lambda _:True, callback, registry=registry)

    def test_running_steps_keep_accepted_distinct_from_completed(self):
        self.begin()
        initial = runtime.status(self.base,TOKEN)
        self.assertEqual(initial['status'],'running')
        self.assertEqual([s['status'] for s in initial['steps']],['pending','pending'])
        runtime.update(self.base,TOKEN,0,'running')
        self.assertEqual(runtime.status(self.base,TOKEN)['steps'][0]['status'],'running')
        runtime.update(self.base,TOKEN,0,'accepted')
        runtime.update(self.base,TOKEN,1,'running')
        runtime.update(self.base,TOKEN,1,'completed',status='completed')
        result = runtime.status(self.base,TOKEN)
        self.assertEqual([s['status'] for s in result['steps']],['accepted','completed'])
        self.assertNotIn('pid',result); self.assertNotIn('processStart',result)

    def test_cancel_is_cooperative_and_foreign_token_cannot_cancel(self):
        self.begin()
        runtime.cancel(self.base,FOREIGN)
        self.assertFalse(runtime.cancelled(self.base,TOKEN))
        before = runtime.status(self.base,TOKEN)
        runtime.cancel(self.base,TOKEN)
        after = runtime.status(self.base,TOKEN)
        self.assertTrue(after['cancelRequested'])
        self.assertEqual(after['status'],'running')
        self.assertEqual(after['steps'],before['steps'])
        self.assertEqual(runtime.status(self.base,FOREIGN)['status'],'unknown')

    def test_cancel_before_first_step_prevents_all_execution(self):
        original = runtime.begin
        def begin_then_cancel(*args):
            original(*args); runtime.cancel(self.base,TOKEN)
        callback = Mock()
        with patch.object(runtime,'begin',side_effect=begin_then_cancel):
            result = self.execute(callback)
        callback.assert_not_called()
        self.assertEqual(result['status'],'cancelled')
        self.assertEqual([s['status'] for s in runtime.status(self.base,TOKEN)['steps']],['skipped','skipped'])

    def test_cancel_during_current_step_keeps_receipt_and_skips_next(self):
        calls=[]
        def callback(action):
            calls.append(action)
            runtime.cancel(self.base,TOKEN)
            return {'ok':True,'status':'accepted'}
        result=self.execute(callback)
        self.assertEqual(calls,['first'])
        self.assertEqual(result['accepted'],['First control'])
        self.assertEqual(result['completed'],[])
        self.assertEqual(result['status'],'cancelled')
        self.assertEqual([s['status'] for s in runtime.status(self.base,TOKEN)['steps']],['accepted','skipped'])

    def test_missing_process_or_reused_pid_is_interrupted_without_resume(self):
        for current_start in ('', 'replacement-process-start'):
            self.begin(); runtime.update(self.base,TOKEN,0,'running')
            with patch.object(runtime,'_start',return_value=current_start):
                result=runtime.status(self.base,TOKEN)
            self.assertEqual(result['status'],'interrupted')
            self.assertEqual([s['status'] for s in result['steps']],['unknown','skipped'])
            self.assertIn('will not resume',result['text'])
            # Restored process visibility cannot make interrupted work runnable.
            self.assertEqual(runtime.status(self.base,TOKEN)['status'],'interrupted')
            self.assertEqual(get(self.base/'command-progress.json',{})['status'],'interrupted')

    def test_second_execution_lock_fails_without_waiting_and_releases(self):
        with runtime.execution_lock(self.base):
            with self.assertRaisesRegex(ValueError,'Another plan'):
                with runtime.execution_lock(self.base):
                    self.fail('Concurrent execution was allowed')
        with runtime.execution_lock(self.base):
            pass

    def test_lock_contention_never_claims_or_executes_reviewed_plan(self):
        registry=self.prepare(); callback=Mock()
        with runtime.execution_lock(self.base):
            with self.assertRaisesRegex(ValueError,'Another plan'):
                plans.execute(TOKEN,self.base,{a:['inert'] for a in self.labels},self.labels,
                              lambda _:True,callback,registry=registry)
        callback.assert_not_called()
        self.assertEqual(get(self.base/'command-plan.json',{})['token'],TOKEN[5:])

    def test_mixed_receipts_remain_truthful_and_failed_step_skips_remaining(self):
        def callback(action):
            live=runtime.status(self.base,TOKEN)
            self.assertEqual(live['steps'][list(self.labels).index(action)]['status'],'running')
            return {'ok':True,'status':'accepted' if action=='first' else 'completed'}
        result=self.execute(callback)
        self.assertEqual(result['status'],'accepted')
        self.assertEqual(result['accepted'],['First control'])
        self.assertEqual(result['completed'],['Second control'])
        result=self.execute(lambda _: {'ok':False,'status':'failed'})
        self.assertEqual(result['status'],'failed')
        self.assertEqual([s['status'] for s in runtime.status(self.base,TOKEN)['steps']],['failed','skipped'])

    def test_foreign_updates_and_malformed_cancellation_do_not_mutate(self):
        self.begin(); before=get(self.base/'command-progress.json',{})
        runtime.update(self.base,FOREIGN,0,'completed',status='completed')
        for value in ('plan:../../other',None,123):
            with self.assertRaises(ValueError):runtime.cancel(self.base,value)
        self.assertEqual(get(self.base/'command-progress.json',{}),before)


if __name__=='__main__':unittest.main()
