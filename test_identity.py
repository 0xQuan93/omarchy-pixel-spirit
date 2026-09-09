import sys,tempfile,unittest,json,re
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).parent/'plugin'))
import identity as i
class IdentityTests(unittest.TestCase):
 def test_seed_and_name_persist(self):
  with tempfile.TemporaryDirectory() as tmp,patch.object(i,'STATE',Path(tmp)),patch.object(i,'VAULT',Path(tmp)):
   a=i.profile();b=i.profile('rename','Echo Vale')
   self.assertEqual(a['seed'],b['seed']);self.assertEqual(i.profile()['name'],'Echo Vale')
 def test_name_validation(self):
  for name in ['','x'*25,'<script>','$(whoami)','name\nwith\x00nul']:
   with self.assertRaises(ValueError):i.clean_name(name)
  self.assertEqual(i.clean_name('  Écho  Vale '),'Écho Vale')
 def test_class_and_influence(self):
  p={'class':'Auto','interests':['Musician']}
  self.assertEqual(i.appearance(p,{'Maker':3,'Musician':1})['family'],'Musician')
  p['class']='Artist';self.assertEqual(i.appearance(p,{'Maker':20})['className'],'Prismweaver')
 def test_public_package_has_one_root_manifest(self):
  base=Path(__file__).parent
  self.assertEqual([p.relative_to(base).as_posix() for p in base.rglob('manifest.json') if '.git' not in p.parts],['manifest.json'])
  data=json.loads((base/'manifest.json').read_text())
  for entry in data['entryPoints'].values():self.assertTrue((base/entry).is_file())
 def test_all_silhouettes_unique_rectangular(self):
  js=(Path(__file__).parent/'plugin/Forms.js').read_text().split('var families = ',1)[1].split('\nfunction rows',1)[0]
  families=json.loads(re.sub(r'(?m)^(Maker|Artist|Musician|Archivist):',r'"\1":',js))
  shapes=[]
  for forms in families.values():
   self.assertEqual(len(forms),4)
   for rows in forms:
    self.assertEqual({len(row) for row in rows},{16});shapes.append(tuple(rows))
  self.assertEqual(len(set(shapes)),16)
if __name__=='__main__':unittest.main()
