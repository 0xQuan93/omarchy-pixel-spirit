"""Persistence across fresh helper processes and interrupted/damaged saves."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent / "plugin"))
import growth
import storage

ROOT = Path(__file__).resolve().parent


class StorageTests(unittest.TestCase):
    def test_backup_recovers_missing_and_invalid_primary(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'position.json'
            storage.put(path, {'x': 12})
            storage.put(path, {'x': 34})
            for broken in ('{', '[]'):
                path.write_text(broken)
                self.assertEqual(storage.get(path, {}), {'x': 12})
            path.unlink()
            self.assertEqual(storage.get(path, {}), {'x': 12})
            self.assertEqual(path.with_name(path.name + '.bak').stat().st_mode & 0o777, 0o600)

    def test_unrecoverable_damage_never_overwrites_progress(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'room.json'
            path.write_text('{broken primary')
            backup = path.with_name(path.name + '.bak')
            backup.write_text('{}')
            with self.assertRaises(storage.StateError):
                storage.get(path, {})
            from playroom import default
            with self.assertRaises(storage.StateError):
                storage.put(path, default())
            self.assertEqual(path.read_text(), '{broken primary')
            self.assertEqual(backup.read_text(), '{}')

    def test_failed_replace_preserves_last_save(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'position.json'
            storage.put(path, {'x': 12})
            replace = os.replace
            def fail_primary(source, target):
                if target == path:
                    raise OSError('simulated interrupted save')
                replace(source, target)
            with patch.object(storage.os, 'replace', side_effect=fail_primary):
                with self.assertRaises(OSError):
                    storage.put(path, {'x': 99})
            self.assertEqual(storage.get(path, {}), {'x': 12})
            self.assertEqual(json.loads(path.with_name(path.name + '.bak').read_text()), {'x': 12})


class RestartTests(unittest.TestCase):
    def test_full_companion_survives_restarts_and_continues_growing(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp)
            work = folder / 'work'
            work.mkdir()
            state = folder / 'state/pixel-spirit'
            env = dict(os.environ, XDG_STATE_HOME=str(folder / 'state'),
                       PIXEL_SPIRIT_WORK=str(work), PIXEL_SPIRIT_MEMORY=str(folder / 'memory'))
            def call(args, ok=True):
                proc = subprocess.run([sys.executable, '-B', str(ROOT / 'plugin/brain.py')],
                                      input=json.dumps(args) + '\n', capture_output=True,
                                      text=True, env=env, timeout=10)
                self.assertEqual(proc.returncode, 0 if ok else 1, proc.stdout + proc.stderr)
                return json.loads(proc.stdout)
            initial = call(['restore'])
            call(['identity', 'rename', 'Persistent Test'])
            call(['identity', 'class', 'Artist'])
            call(['identity', 'interest', 'Musician'])
            call(['room', 'note', 'A remembered note'])
            call(['room', 'pat'])
            position = {'x': 0, 'y': 125, 'hidden': False, 'voice': True, 'movement': 'stay'}
            call(['save', json.dumps(position)])
            saved = json.loads((state / 'growth.json').read_text())
            saved.update(xp=80, daily=0, updated=time.time() - 120)
            storage.put(state / 'growth.json', saved)
            storage.put(state / 'history.json', [{'role': 'assistant', 'content': json.dumps({'text': 'A remembered reply'})}])
            # A real observed file change earns XP without resetting the saved stage.
            (work / 'new.py').write_text('print("test")')
            evolved = call(['growth'])
            self.assertEqual(evolved['xp'], 81)
            for _ in range(3):
                restored = call(['restore'])
                self.assertEqual(restored['profile']['name'], 'Persistent Test')
                self.assertEqual(restored['profile']['seed'], initial['profile']['seed'])
                self.assertEqual(restored['profile']['created'], initial['profile']['created'])
                self.assertEqual(restored['profile']['class'], 'Artist')
                self.assertIn('Musician', restored['profile']['interests'])
                self.assertEqual(restored['growth']['xp'], 81)
                self.assertEqual(restored['growth']['stage'], 'Familiar')
                self.assertEqual(restored['growth']['born'], initial['growth']['born'])
                self.assertEqual(restored['room']['bond'], 2)
                self.assertEqual(restored['room']['notes'][0]['text'], 'A remembered note')
                self.assertEqual(restored['position'], position)
                self.assertEqual(restored['reply'], 'A remembered reply')
            dream = call(['dream_snapshot'])
            self.assertEqual(dream['profile'], restored['profile'])
            self.assertEqual(dream['growth'], restored['growth'])
            self.assertEqual(dream['appearance']['family'], 'Artist')
            self.assertEqual(dream['room']['bond'], 2)
            self.assertEqual(dream['room']['notes'], [{}])  # no note text in screensaver
            call(['forget'])
            call(['room', 'clear_notes'])
            cleared = call(['restore'])
            self.assertEqual(cleared['growth']['xp'], 81)
            self.assertEqual(cleared['room']['bond'], 2)
            self.assertEqual(json.loads((state / 'history.json.bak').read_text()), [])
            self.assertEqual(json.loads((state / 'room.json.bak').read_text())['notes'], [])
            (state / 'identity.json').write_text('{}')
            recovered = call(['restore'])
            self.assertEqual(recovered['profile']['name'], 'Persistent Test')
            self.assertIn('identity.json', recovered['recovered'])
            (state / 'growth.json').write_text('{broken')
            (state / 'growth.json.bak').write_text('{also broken')
            self.assertIn('error', call(['restore'], ok=False))
            self.assertEqual((state / 'growth.json').read_text(), '{broken')


if __name__ == '__main__':
    unittest.main()
