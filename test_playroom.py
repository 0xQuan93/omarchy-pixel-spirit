import sys,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).parent/'plugin'))
import playroom as p
class RoomTests(unittest.TestCase):
 def test_daily_reward_dedup_and_persistence(self):
  with tempfile.TemporaryDirectory() as tmp,patch.object(p,'STATE',Path(tmp)):
   self.assertEqual(p.update('pat')['bond'],1)
   self.assertEqual(p.update('pat')['bond'],1)
   self.assertEqual(p.update('activity','read')['bond'],2)
   self.assertEqual(p.update()['activity'],'read')
 def test_ambient_activity_does_not_farm_rewards(self):
  with tempfile.TemporaryDirectory() as tmp,patch.object(p,'STATE',Path(tmp)):
   self.assertEqual(p.update('ambient','garden')['bond'],0)
   self.assertEqual(p.update()['activity'],'garden')
 def test_note_validation(self):
  with tempfile.TemporaryDirectory() as tmp:
   path=Path(tmp)/'note.txt';path.write_text('remember the garden')
   self.assertEqual(p.note_text(path.as_uri()),'remember the garden')
   link=Path(tmp)/'link.txt';link.symlink_to(path)
   for value in [link.as_uri(),'file://remote/note.txt','x'*4097,'']:
    with self.assertRaises(ValueError):p.note_text(value)
 def test_notes_bounded_and_clear_preserves_bond(self):
  with tempfile.TemporaryDirectory() as tmp,patch.object(p,'STATE',Path(tmp)):
   for i in range(15):s=p.update('note',str(i))
   self.assertEqual(len(s['notes']),12);self.assertEqual(s['bond'],1)
   s=p.update('clear_notes');self.assertEqual(s['notes'],[]);self.assertEqual(s['bond'],1)
 def test_ai_activity_cannot_execute_other_commands(self):
  with tempfile.TemporaryDirectory() as tmp,patch.object(p,'STATE',Path(tmp)):
   with self.assertRaises(ValueError):p.update('activity','terminal')
if __name__=='__main__':unittest.main()
