"""Lock contention tests never contact a model or network."""
import fcntl
import io
from pathlib import Path
import sys
import tempfile
import time
import unittest
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).parent/'plugin'))
import inference

class InferenceDeadlines(unittest.TestCase):
    def setUp(self):
        temp=tempfile.TemporaryDirectory();self.addCleanup(temp.cleanup)
        self.base=Path(temp.name)
    def test_foreground_contended_lock_expires_without_network(self):
        with (self.base/'model.lock').open('w') as holder:
            fcntl.flock(holder,fcntl.LOCK_EX|fcntl.LOCK_NB)
            with patch.object(inference.urllib.request,'urlopen') as network:
                started=time.monotonic()
                with self.assertRaises(TimeoutError):inference.request({},timeout=0.03,state_dir=self.base)
                self.assertLess(time.monotonic()-started,1)
                network.assert_not_called()
    def test_background_never_waits(self):
        with (self.base/'model.lock').open('w') as holder:
            fcntl.flock(holder,fcntl.LOCK_EX|fcntl.LOCK_NB)
            with patch.object(inference.time,'sleep') as sleep,patch.object(inference.urllib.request,'urlopen') as network:
                with self.assertRaises(BlockingIOError):inference.request({},background=True,state_dir=self.base)
                sleep.assert_not_called();network.assert_not_called()
    def test_http_receives_only_remaining_budget(self):
        with patch.object(inference.time,'monotonic',side_effect=[100,104]),patch.object(inference.urllib.request,'urlopen',return_value=io.BytesIO(b'{"message":{}}')) as network:
            self.assertEqual(inference.request({},timeout=10,state_dir=self.base),{'message':{}})
            self.assertEqual(network.call_args.kwargs['timeout'],6)
    def test_exception_releases_lock_for_next_request(self):
        with patch.object(inference.urllib.request,'urlopen',side_effect=OSError('offline')):
            with self.assertRaises(OSError):inference.request({},state_dir=self.base)
        with (self.base/'model.lock').open('w') as holder:
            fcntl.flock(holder,fcntl.LOCK_EX|fcntl.LOCK_NB)
    def test_invalid_deadline_has_no_effects(self):
        for value in (0,-1,float('inf'),float('nan'),True,'5'):
            with self.assertRaises(ValueError):inference.request({},timeout=value,state_dir=self.base)
        self.assertEqual(list(self.base.iterdir()),[])

if __name__=='__main__':unittest.main()
