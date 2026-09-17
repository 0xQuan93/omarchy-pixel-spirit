"""Recover malformed nested saves without following unsafe state files."""
import copy
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).parent/'plugin'))
import storage
import awareness
import growth
import playroom

class StateSafety(unittest.TestCase):
    def setUp(self):
        temp=tempfile.TemporaryDirectory();self.addCleanup(temp.cleanup);self.base=Path(temp.name)
    def recover(self,name,good,bad):
        path=self.base/name;path.write_text(json.dumps(bad));backup=path.with_name(name+'.bak');backup.write_text(json.dumps(good))
        self.assertEqual(storage.get(path,{}),good)
        self.assertEqual(json.loads(path.read_text()),bad)
        self.assertIn(name,storage.RECOVERED)
    def test_nested_awareness_and_revision_recover_good_backup(self):
        good=awareness.empty()
        for bad in (dict(good,seconds={'Maker':'broken'}),dict(good,events=['bad']),
                    dict(good,reflections=[{}]),dict(good,pending={'reflection':'bad'})):
            self.recover('awareness.json',good,bad)
        settings=awareness.defaults()
        for bad in (dict(settings,revision='bad'),dict(settings,enabled=1),dict(settings,command_hints='false')):
            self.recover('awareness-settings.json',settings,bad)
    def test_nested_growth_and_room_recover_good_backup(self):
        snapshot={'files':{'project/main.py':[123,456,'Maker']},'repos':{'project':{'head':'a','upstream':''}},
                  'counts':{k:0 for k in growth.TYPES},'limited':False}
        good=growth.evolve({},snapshot)
        for field,value in (('counts',{'Maker':'bad'}),('files',{'name':[1]}),('repos',{'project':None})):
            bad=copy.deepcopy(good);bad['snapshot'][field]=value;self.recover('growth.json',good,bad)
        bad=dict(good,journal=[{}]);self.recover('growth.json',good,bad)
        room=playroom.default();self.recover('room.json',room,dict(room,notes=[{'text':5,'at':1}]))
    def test_old_and_private_optional_fields_remain_compatible(self):
        old=awareness.empty();old.pop('pending');old.pop('last_delivered')
        self.assertEqual(storage.validate(Path('awareness.json'),old,{}),old)
        settings={'enabled':False,'titles':False,'quiet_until':0,'private_future_setting':{'value':1}}
        self.assertEqual(storage.validate(Path('awareness-settings.json'),settings,{}),settings)
        pending=dict(awareness.empty(),pending={'reflection':{'id':'a'*32,'text':'tip'},'settings':settings,
                       'context':{},'expires':100,'effects':{'private':True},'script':None,'draft':None})
        self.assertEqual(storage.validate(Path('awareness.json'),pending,{}),pending)
    def test_nonfinite_numbers_never_reach_state(self):
        for value in (float('inf'),float('-inf'),float('nan')):
            with self.assertRaises(ValueError):storage.put(self.base/'position.json',{'nested':[value]})
        self.assertEqual(list(self.base.iterdir()),[])
    def test_fifo_symlink_and_oversize_primary_use_good_backup(self):
        path=self.base/'position.json';backup=self.base/'position.json.bak';backup.write_text('{"x":12}')
        os.mkfifo(path)
        self.assertEqual(storage.get(path,{}),{'x':12});path.unlink()
        target=self.base/'target';target.write_text('{"x":999}');path.symlink_to(target)
        self.assertEqual(storage.get(path,{}),{'x':12});path.unlink()
        with path.open('wb') as stream:stream.truncate(storage.MAX_STATE_BYTES+1)
        self.assertEqual(storage.get(path,{}),{'x':12})
    def test_bad_backup_is_never_used_or_overwritten(self):
        path=self.base/'position.json';path.write_text('{broken');backup=self.base/'position.json.bak';os.mkfifo(backup)
        with self.assertRaises(storage.StateError):storage.put(path,{'x':2})
        self.assertEqual(path.read_text(),'{broken');self.assertTrue(backup.exists())
    def test_oversize_write_preserves_primary(self):
        path=self.base/'position.json';storage.put(path,{'x':1})
        with patch.object(storage,'MAX_STATE_BYTES',32):
            with self.assertRaises(ValueError):storage.put(path,{'x':'a'*100})
        self.assertEqual(storage.get(path,{}),{'x':1})
    def test_archived_pre_epoch_file_timestamp_survives_growth_save(self):
        work=self.base/'archive';work.mkdir()
        note=work/'historical.txt';note.write_text('Archived document')
        os.utime(note,(-1,-1))
        self.assertLess(note.stat().st_mtime_ns,0)
        snapshot=growth.collect(work,self.base/'missing-vault')
        self.assertEqual(snapshot['files']['historical.txt'][0],note.stat().st_mtime_ns)
        data=growth.evolve({},snapshot);path=self.base/'growth.json'
        storage.put(path,data)
        self.assertEqual(storage.get(path,{}),data)

    def test_capped_growth_inventory_fits_limit(self):
        # 16k work records plus 1k optional memory records, with long filenames.
        files={str(i)+'x'*240:[1234567890000000000,1024,'Maker'] for i in range(17000)}
        snapshot={'files':files,'repos':{},'counts':{k:0 for k in growth.TYPES},'limited':True}
        data=growth.evolve({},snapshot);path=self.base/'growth.json';storage.put(path,data)
        self.assertEqual(len(storage.get(path,{})['snapshot']['files']),17000)
        self.assertLess(path.stat().st_size,storage.MAX_STATE_BYTES)

if __name__=='__main__':unittest.main()
