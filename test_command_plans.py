import sys, tempfile, unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).parent/'plugin'))
import command_plans as plans
from storage import put, get

class Plans(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup);self.base=Path(self.temp.name)
  self.actions={'browser':['browser'], 'terminal':['terminal'], 'files':['files']};self.labels={a:a.title() for a in self.actions}
  self.calls=[]
 def prepare(self,ids=('browser','terminal'),created=None):
  import time
  put(self.base/'command-plan.json',dict(token='a'*32,created=time.time() if created is None else created,actions=list(ids),fingerprints={a:plans._registry(self.actions,self.labels,lambda a:True).fingerprint(a) for a in ids if a in self.actions}),False)
  return 'plan:'+'a'*32
 def execute(self,token,available=lambda a:True,run=None):
  def default(a):self.calls.append(a);return {'text':'ok','action':'','ok':True,'status':'completed'}
  return plans.execute(token,self.base,self.actions,self.labels,available,run or default)
 def test_once(self):
  token=self.prepare();self.assertTrue(self.execute(token)['ok']);self.assertEqual(self.calls,['browser','terminal'])
  with self.assertRaises(ValueError):self.execute(token)
 def test_preflight(self):
  with self.assertRaises(ValueError):self.execute(self.prepare(),lambda a:a!='terminal')
  self.assertEqual(self.calls,[])
 def test_expired_or_unregistered(self):
  for ids,created in [(('browser',),0),(('shell',),None)]:
   with self.assertRaises(ValueError):self.execute(self.prepare(ids,created))
  self.assertEqual(self.calls,[])
 def test_failure_stops(self):
  def run(a):self.calls.append(a);return {'text':'result','action':'','ok':a!='terminal','status':'completed' if a!='terminal' else 'failed'}
  reply=self.execute(self.prepare(('browser','terminal','files')),run=run)
  self.assertFalse(reply['ok']);self.assertEqual(self.calls,['browser','terminal']);self.assertIn('Not run: Files',reply['text'])
 def test_changed_registration_requires_new_review(self):
  token=self.prepare();self.actions['browser']=['different-browser']
  with self.assertRaisesRegex(ValueError,'changed'):self.execute(token)
  self.assertEqual(self.calls,[])
 def test_no_execution_during_proposal(self):
  result=plans.proposal('open browser and terminal',self.base,self.actions,self.labels,lambda s:s,lambda s:{'open browser':'browser','open terminal':'terminal'}.get(s),lambda s:None,lambda a:True)
  self.assertTrue(result['action'].startswith('plan:'));self.assertEqual(self.calls,[])
 def test_pending_and_execution_reject_identical_malformed_state(self):
  registry=plans._registry(self.actions,self.labels,lambda a:True)
  for mutate in (lambda p: [], lambda p: dict(p,actions=['browser','browser']),
                 lambda p: dict(p,created=True),lambda p: dict(p,fingerprints={})):
   token=self.prepare();record=mutate(get(self.base/'command-plan.json',{}))
   with patch.object(plans,'get',return_value=record):
    with self.assertRaises(ValueError):plans.pending(self.base,token,registry)
    with self.assertRaises(ValueError):self.execute(token)
  self.assertEqual(self.calls,[])
 def test_invalidation_rejects_malformed_or_foreign_tokens(self):
  token=self.prepare();before=get(self.base/'command-plan.json',{})
  for value in (None,123,'wrong'+token[5:],'plan:../../file'):
   with self.assertRaises(ValueError):plans.invalidate(self.base,value)
  self.assertFalse(plans.invalidate(self.base,'plan:'+'b'*32))
  self.assertEqual(get(self.base/'command-plan.json',{}),before)
 def test_edit_cannot_resurrect_consumed_token(self):
  token=self.prepare();registry=plans._registry(self.actions,self.labels,lambda a:True)
  def resolve(_):
   plans.invalidate(self.base,token)
   return 'files'
  reply=plans.edit('only open files',token,self.base,self.actions,self.labels,resolve,registry)
  self.assertEqual(reply['action'],'')
  self.assertEqual(get(self.base/'command-plan.json',{}),{})
  self.assertEqual(self.calls,[])
 def test_backend_exact_cancel_clears_pending_plan(self):
  registry=plans._registry(self.actions,self.labels,lambda a:True)
  for text in ('cancel','cancel plan','please cancel the plan','never mind'):
   token=self.prepare()
   reply=plans.edit(text,token,self.base,self.actions,self.labels,lambda _:self.fail('resolved cancellation'),registry)
   self.assertEqual(reply['action'],'');self.assertEqual(reply['status'],'cancelled')
   self.assertEqual(get(self.base/'command-plan.json',{}),{})
if __name__=='__main__':unittest.main()
