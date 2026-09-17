import sys, tempfile, unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).parent/'plugin'))
import command_plans as plans
from storage import put

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
if __name__=='__main__':unittest.main()
