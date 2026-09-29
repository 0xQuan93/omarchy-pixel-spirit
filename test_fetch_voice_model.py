"""Offline checks for the optional voice-model download boundary."""

import hashlib
import importlib.util
import io
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch


SCRIPT = Path(__file__).resolve().parent / 'tools/fetch_voice_model.py'
SPEC = importlib.util.spec_from_file_location('fetch_voice_model', SCRIPT)
downloader = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(downloader)


class Response:
    def __init__(self, content, content_length=None):
        self.stream = io.BytesIO(content)
        self.headers = {} if content_length is None else {'Content-Length': str(content_length)}
        self.bytes_read = 0

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        self.stream.close()

    def read(self, count):
        chunk = self.stream.read(count)
        self.bytes_read += len(chunk)
        return chunk


class VoiceModelDownloadTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.target = Path(self.temp.name) / 'pixel-spirit/model.bin'

    def files(self):
        return list(self.target.parent.iterdir())

    def test_valid_download_and_existing_model_do_not_fetch_twice(self):
        data = b'abcdefgh'
        response = Response(data, len(data))
        with patch.object(downloader.urllib.request, 'urlopen', return_value=response) as fetch:
            downloader.download_model(self.target, expected_sha256=hashlib.sha256(data).hexdigest(), max_bytes=8)
            downloader.download_model(self.target, expected_sha256=hashlib.sha256(data).hexdigest(), max_bytes=8)
        fetch.assert_called_once()
        self.assertEqual(self.target.read_bytes(), data)
        self.assertEqual(self.files(), [self.target])

    def test_oversized_header_rejects_before_read_or_temp_file(self):
        response = Response(b'x', 9)
        with patch.object(downloader.urllib.request, 'urlopen', return_value=response):
            with self.assertRaisesRegex(ValueError, 'Content-Length'):
                downloader.download_model(self.target, max_bytes=8)
        self.assertEqual(response.bytes_read, 0)
        self.assertEqual(self.files(), [])

    def test_stream_overflow_rejects_missing_or_false_header_and_cleans_up(self):
        for header in (None, 8):
            with self.subTest(header=header):
                response = Response(b'123456789', header)
                with patch.object(downloader.urllib.request, 'urlopen', return_value=response):
                    with self.assertRaisesRegex(ValueError, 'size limit'):
                        downloader.download_model(self.target, max_bytes=8)
                self.assertEqual(response.bytes_read, 9)
                self.assertEqual(self.files(), [])

    def test_bad_checksum_discards_temp_and_existing_mismatch_is_preserved(self):
        with patch.object(downloader.urllib.request, 'urlopen', return_value=Response(b'bad')):
            with self.assertRaisesRegex(ValueError, 'checksum mismatch'):
                downloader.download_model(self.target, max_bytes=8)
        self.assertEqual(self.files(), [])
        self.target.write_bytes(b'existing')
        with patch.object(downloader.urllib.request, 'urlopen') as fetch:
            with self.assertRaisesRegex(ValueError, 'existing model'):
                downloader.download_model(self.target, max_bytes=8)
        fetch.assert_not_called()
        self.assertEqual(self.target.read_bytes(), b'existing')


if __name__ == '__main__':
    unittest.main()
