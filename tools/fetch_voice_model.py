#!/usr/bin/env python3
"""Explicit optional download. No model is downloaded by enabling the plugin."""

import hashlib
import os
import tempfile
import urllib.request
from pathlib import Path

URL = 'https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-tiny.en.bin'
SHA256 = '921e4cf8686fdd993dcd081a5da5b6c365bfde1162e72b08d75ac75289920b1f'
# The pinned model is 77,704,715 bytes; its SHA-256 still pins the exact content.
MAX_MODEL_BYTES = 80 * 1024 * 1024


def file_sha256(path):
    digest = hashlib.sha256()
    with path.open('rb') as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b''):
            digest.update(chunk)
    return digest.hexdigest()


def download_model(target, url=URL, expected_sha256=SHA256, max_bytes=MAX_MODEL_BYTES):
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists():
        if file_sha256(target) == expected_sha256:
            print('Verified model already installed.')
            return
        raise ValueError('An existing model has a different checksum. Move it aside deliberately before downloading.')

    with urllib.request.urlopen(url, timeout=120) as response:
        content_length = response.headers.get('Content-Length')
        if content_length is not None:
            try:
                declared_size = int(content_length)
            except ValueError as exc:
                raise ValueError('Invalid model Content-Length') from exc
            if declared_size < 0 or declared_size > max_bytes:
                raise ValueError('Model Content-Length exceeds the download limit')

        fd, tmp = tempfile.mkstemp(dir=target.parent)
        try:
            digest = hashlib.sha256()
            size = 0
            with os.fdopen(fd, 'wb') as out:
                while chunk := response.read(min(1024 * 1024, max_bytes - size + 1)):
                    size += len(chunk)
                    if size > max_bytes:
                        raise ValueError('Model download exceeds the size limit')
                    digest.update(chunk)
                    out.write(chunk)
            if digest.hexdigest() != expected_sha256:
                raise ValueError('Model checksum mismatch; download discarded')
            os.replace(tmp, target)
        finally:
            if os.path.exists(tmp):
                os.unlink(tmp)
    print('Installed verified tiny.en speech model:', target)


if __name__ == '__main__':
    data_home = Path(os.environ.get('XDG_DATA_HOME', str(Path.home() / '.local/share')))
    download_model(data_home / 'pixel-spirit/ggml-tiny.en.bin')
