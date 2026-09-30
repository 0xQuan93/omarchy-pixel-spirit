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

class Response(io.BytesIO):
    def __init__(self, content, content_length=None):
        super().__init__(content)
        self.headers = {} if content_length is None else {'Content-Length': str(content_length)}
        self.bytes_read = 0
    def read(self, count=-1):
        chunk = super().read(count)
        self.bytes_read += len(chunk)
        return chunk

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

    def test_exact_response_limit_is_accepted(self):
        body = b'{"message":{}}'
        response = Response(body, len(body))
        with patch.object(inference, 'MAX_RESPONSE_BYTES', len(body)), \
             patch.object(inference.urllib.request, 'urlopen', return_value=response):
            self.assertEqual(inference.request({}, state_dir=self.base), {'message': {}})
        self.assertEqual(response.bytes_read, len(body))

    def test_oversized_header_rejects_before_read_or_parse(self):
        response = Response(b'{}', 9)
        with patch.object(inference, 'MAX_RESPONSE_BYTES', 8), \
             patch.object(inference.urllib.request, 'urlopen', return_value=response), \
             patch.object(inference.json, 'loads') as parse:
            with self.assertRaisesRegex(OSError, 'Content-Length exceeds'):
                inference.request({}, state_dir=self.base)
        self.assertEqual(response.bytes_read, 0)
        parse.assert_not_called()
        with (self.base/'model.lock').open('w') as holder:
            fcntl.flock(holder, fcntl.LOCK_EX | fcntl.LOCK_NB)

    def test_stream_overflow_rejects_missing_or_false_header_before_parse(self):
        for header in (None, 8):
            with self.subTest(header=header):
                response = Response(b'123456789', header)
                with patch.object(inference, 'MAX_RESPONSE_BYTES', 8), \
                     patch.object(inference.urllib.request, 'urlopen', return_value=response), \
                     patch.object(inference.json, 'loads') as parse:
                    with self.assertRaisesRegex(OSError, 'size limit'):
                        inference.request({}, state_dir=self.base)
                self.assertEqual(response.bytes_read, 9)
                parse.assert_not_called()

    def test_invalid_content_length_rejects_before_read(self):
        for header in (-1, 'invalid'):
            with self.subTest(header=header):
                response = Response(b'{}', header)
                with patch.object(inference.urllib.request, 'urlopen', return_value=response):
                    with self.assertRaisesRegex(OSError, 'Content-Length'):
                        inference.request({}, state_dir=self.base)
                self.assertEqual(response.bytes_read, 0)

if __name__=='__main__':unittest.main()
