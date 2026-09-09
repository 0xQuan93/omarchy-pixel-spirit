"""Regression checks for private, bounded helper requests."""
import io
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from test_brain import b

ROOT = Path(__file__).resolve().parent


def frame(args):
    return (json.dumps(args) + '\n').encode('ascii')


class TransportTests(unittest.TestCase):
    def parse(self, payload):
        with patch.object(sys, 'argv', ['brain.py']):
            return b.read_request(io.BytesIO(payload))

    def test_unicode_newlines_and_shell_characters_roundtrip(self):
        args = ['chat', 'Private 雲 🌱\n"quotes" \\ $(touch nope)', 'eco']
        self.assertEqual(self.parse(frame(args)), args)

    def test_exact_byte_limit_and_oversize(self):
        overhead = len(frame(['chat', '']))
        payload = frame(['chat', 'x' * (b.MAX_REQUEST_BYTES - overhead)])
        self.assertEqual(len(payload), b.MAX_REQUEST_BYTES)
        self.assertEqual(self.parse(payload)[0], 'chat')
        with self.assertRaises(ValueError):
            self.parse(payload[:-1] + b' \n')
        with self.assertRaises(ValueError):
            self.parse(b'x' * (b.MAX_REQUEST_BYTES + 1))

    def test_bad_frames_and_shapes_fail_without_echoing_input(self):
        for payload in [b'', b'["load"]', b'\xff\n', b'private-invalid-json\n',
                        b'[' * 2000 + b'\n', b'{}\n', b'[]\n', b'[null]\n',
                        frame(['chat']), frame(['action', {}]),
                        frame(['load', 'extra']), frame(['unknown-private-command']),
                        frame(['room', 'note', 'text', 'extra'])]:
            with self.subTest(payload=payload[:40]), self.assertRaises(ValueError) as error:
                self.parse(payload)
            self.assertNotIn('private', str(error.exception))

    def test_legacy_argv_is_rejected_before_reading_or_dispatch(self):
        with patch.object(sys, 'argv', ['brain.py', 'chat', 'private']), \
             patch.object(b, 'chat') as chat:
            with self.assertRaisesRegex(ValueError, 'stdin'):
                b.main()
            chat.assert_not_called()

    def test_chat_dispatch_and_speech_use_stdin(self):
        for args in [['chat', 'private\n🌱', 'eco'], ['speak', 'private\n🌱']]:
            with patch.object(sys, 'argv', ['brain.py']), \
                 patch.object(sys, 'stdin') as stdin, \
                 patch.object(b, 'chat', return_value={'text': 'ok'}) as chat, \
                 patch.object(b.subprocess, 'run') as run:
                stdin.buffer = io.BytesIO(frame(args))
                b.main()
                if args[0] == 'chat':
                    chat.assert_called_once_with(args[1], True)
                else:
                    self.assertEqual(run.call_args.args[0], ['espeak-ng', '-s', '165', '--stdin'])
                    self.assertEqual(run.call_args.kwargs['input'], args[1])

    def test_real_helper_save_load_and_invalid_request(self):
        with tempfile.TemporaryDirectory() as tmp:
            env = dict(os.environ, XDG_STATE_HOME=tmp)
            command = [sys.executable, '-B', str(ROOT / 'plugin/brain.py')]
            state = {'x': 123, 'y': 456, 'hidden': True, 'movement': 'stay'}
            for args, expected in [(['save', json.dumps(state)], {'ok': True}),
                                   (['load'], state)]:
                result = subprocess.run(command, input=frame(args), capture_output=True,
                                        env=env, timeout=5, check=True)
                self.assertEqual(json.loads(result.stdout), expected)
            result = subprocess.run(command, input=frame(['action']), capture_output=True,
                                    env=env, timeout=5)
            self.assertEqual(result.returncode, 1)
            self.assertIn('error', json.loads(result.stdout))

    @unittest.skipUnless(shutil.which('quickshell') and Path('/proc/self/cmdline').exists(),
                         'requires Quickshell and Linux procfs')
    def test_qml_pipe_reuse_unicode_limit_and_live_argv(self):
        # Exercise the actual QML transport with a helper that validates requests
        # and inspects its own live argv. No user state or model is touched.
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp)
            shutil.copy2(ROOT / 'plugin/Call.qml', folder / 'Call.qml')
            (folder / 'brain.py').write_text(
                'import sys, json\nfrom pathlib import Path\n'
                f'sys.path.insert(0, {str(ROOT / "plugin")!r})\n'
                'from brain import read_request\n'
                'args = read_request(sys.stdin.buffer)\n'
                'assert len(sys.argv) == 1\n'
                'assert b"private-marker" not in Path("/proc/self/cmdline").read_bytes()\n'
                'print(json.dumps({"args": args}))\n')
            (folder / 'shell.qml').write_text('''
import QtQuick
import Quickshell
Scope {
    property int step: 0
    property string secret: "private-marker 雲 🌱\\nquotes \\\" \\\\ $(nope)"
    Call {
        id: call
        onReceived: function(data) {
            if (step < 2 && (data.error || data.args[1] !== secret)) Qt.exit(1)
            if (step === 2 && !data.error) Qt.exit(2)
            step++
            if (step === 3) { console.log("TRANSPORT_OK"); Qt.quit() }
            else next.start()
        }
    }
    Timer {
        id: next; interval: 30
        onTriggered: call.run(["chat", step === 2 ? "x".repeat(65536) : secret])
    }
    Component.onCompleted: next.start()
    Timer { interval: 8000; running: true; onTriggered: Qt.exit(3) }
}
''')
            env = dict(os.environ, QT_QPA_PLATFORM='offscreen', QT_QPA_PLATFORMTHEME='', XDG_CACHE_HOME=tmp,
                       XDG_RUNTIME_DIR=tmp)
            result = subprocess.run(['quickshell', '--no-color', '-p', str(folder / 'shell.qml')],
                                    capture_output=True, text=True, env=env, timeout=12)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertIn('TRANSPORT_OK', result.stdout + result.stderr)


if __name__ == '__main__':
    unittest.main()
