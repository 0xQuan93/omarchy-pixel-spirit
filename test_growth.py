import sys,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).parent/'plugin'))
import growth as g

def snapshot(files=None,repos=None):
 return {'files':files or {},'repos':repos or {},'counts':{k:0 for k in g.TYPES},'limited':False}
class GrowthTests(unittest.TestCase):
 def test_baseline_and_idempotence(self):
  snap=snapshot({'song.wav':[1,32,'Musician']});state=g.evolve({},snap,100)
  self.assertEqual(state['xp'],0)
  changed=snapshot({'song.wav':[101000000000,33,'Musician']})
  updated=g.evolve(state,changed,102)
  self.assertEqual(updated['xp'],1)
  self.assertEqual(g.evolve(updated,changed,103)['xp'],1)
 def test_daily_cap_and_no_decay(self):
  state=g.evolve({},snapshot(),100)
  files={str(i)+'.py':[101000000000,20,'Maker'] for i in range(100)}
  updated=g.evolve(state,snapshot(files),102)
  self.assertEqual(updated['xp'],24)
  self.assertEqual(g.view(updated)['stage'],'Sprout')
  self.assertEqual(g.evolve(updated,snapshot(files),200000)['xp'],24)
 def test_old_files_exposed_by_scan_do_not_give_xp(self):
  state=g.evolve({},snapshot(),100)
  self.assertEqual(g.evolve(state,snapshot({'old.py':[1,10,'Maker']}),101)['xp'],0)
 def test_repo_observations_are_not_claimed_pushes(self):
  state=g.evolve({},snapshot(repos={'repo':{'head':'aaa','upstream':'aaa'}}),100)
  result=g.evolve(state,snapshot(repos={'repo':{'head':'bbb','upstream':'bbb'}}),101)
  self.assertEqual(result['xp'],5)
  self.assertIn('not distinguished',result['journal'][-1]['text'])
 def test_hidden_dependencies_and_symlinks_excluded(self):
  with tempfile.TemporaryDirectory() as tmp:
   work=Path(tmp);(work/'node_modules').mkdir();(work/'node_modules/x.py').write_text('x')
   (work/'.secret.py').write_text('x');(work/'code.py').write_text('x');(work/'link.py').symlink_to(work/'code.py')
   result=g.collect(work,work/'memory')
   self.assertEqual(list(result['files']),['code.py'])
 def test_memory_reads_only_startup_and_matching_notes(self):
  with tempfile.TemporaryDirectory() as tmp:
   vault=Path(tmp);(vault/'sessions').mkdir();(vault/'MEMORY.md').write_text('hello')
   (vault/'sessions/project-music.md').write_text('music detail');(vault/'sessions/unrelated.md').write_text('must not load')
   with patch.object(g,'VAULT',vault),patch.object(g,'WORK',vault),patch.object(g,'STATE',vault):
    result=g.memory_context('music')
   text=str(result);self.assertIn('music detail',text);self.assertNotIn('must not load',text)
if __name__=='__main__':unittest.main()
