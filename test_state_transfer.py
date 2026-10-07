"""Portable state uses fixed sections and validates a complete import first."""
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent / 'plugin'))
import state_transfer as transfer


def saved_state(base, name='Wisp', xp=34, bond=6, note='private room note'):
    base.mkdir(parents=True, exist_ok=True)
    values = {
        'identity.json': {'name': name, 'seed': 42, 'created': 100.0,
                          'class': 'Auto', 'interests': ['Musician'],
                          'device': 'portable', 'model': 'qwen3.5:4b'},
        'growth.json': {'born': 100.0, 'updated': 101.0, 'xp': xp,
                        'traits': {'Maker': 1, 'Artist': 2, 'Musician': 32, 'Archivist': 0},
                        'day': '2026-10-07', 'daily': 3,
                        'journal': [{'text': 'Updated song.wav', 'at': 101.0, 'xp': 1}],
                        'snapshot': {'files': {'song.wav': [100000000000, 42, 'Musician']},
                                     'repos': {}, 'counts': {'Musician': 1}, 'limited': False},
                        'presence_seconds': {'Musician': 1800}, 'presence_last': 101.0},
        'room.json': {'bond': bond, 'day': '2026-10-07', 'earned': ['note'],
                      'activity': 'read', 'notes': [{'text': note, 'at': 101.0}],
                      'message': 'Reading our little notebook.'},
        'awareness-settings.json': {'enabled': True, 'titles': True, 'quiet_until': 0,
                                    'command_hints': True, 'mouse_gestures': True,
                                    'activity_responses': True, 'revision': 2},
        'position.json': {'x': 918, 'y': 750, 'hidden': True,
                          'voice': True, 'movement': 'follow'},
        'history.json': [{'role': 'user', 'content': 'Hello from the old machine'}],
        'learned-phrases.json': {'version': 1, 'entries': []},
    }
    for filename, value in values.items():
        (base / filename).write_text(json.dumps(value))
    return values


class StateTransferTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        self.source = self.root / 'source'
        self.target = self.root / 'target'
        self.original = saved_state(self.source)
        saved_state(self.target, name='Existing', xp=7, bond=1, note='keep my note')
        (self.target / 'history.json').write_text(json.dumps([
            {'role': 'user', 'content': 'Existing chat'}]))

    def data(self, base, filename):
        return json.loads((base / filename).read_text())

    def test_default_transfer_contains_only_identity(self):
        archive = self.root / 'wisp-identity.json'
        summary = transfer.export_transfer(archive, self.source)
        self.assertEqual(summary['sections'], ['identity'])
        self.assertIn('Other Wisp state stays untouched.', summary['importBehavior'])
        raw = archive.read_bytes()
        self.assertNotIn(b'private room note', raw)
        self.assertNotIn(b'Reading our little notebook', raw)
        self.assertNotIn(b'Updated song.wav', raw)
        self.assertNotIn(b'Hello from the old machine', raw)
        transfer.import_transfer(transfer.load_transfer(archive), self.target, apply=True)
        self.assertEqual(self.data(self.target, 'identity.json')['name'], 'Wisp')
        self.assertEqual(self.data(self.target, 'growth.json')['xp'], 7)
        self.assertEqual(self.data(self.target, 'room.json')['notes'][0]['text'], 'keep my note')

    def test_explicit_continuity_omits_chat_and_notes_then_preserves_destination_notes(self):
        archive = self.root / 'wisp-transfer.json'
        summary = transfer.export_transfer(archive, self.source,
                                           sections='identity,growth,room,settings')
        self.assertEqual(summary['sections'], ['identity', 'growth', 'room', 'settings'])
        self.assertEqual(summary['noteCount'], 0)
        self.assertNotIn(b'private room note', archive.read_bytes())
        self.assertNotIn(b'Hello from the old machine', archive.read_bytes())
        exported_growth = transfer.load_transfer(archive)['data']['growth']
        self.assertEqual(exported_growth['snapshot']['files'], {})
        self.assertNotIn('presence_seconds', exported_growth)
        before = {name: (self.target / name).read_bytes() for name in
                  ('identity.json', 'growth.json', 'room.json', 'history.json')}
        dry_run = transfer.import_transfer(transfer.load_transfer(archive), self.target)
        self.assertFalse(dry_run.get('applied', False))
        self.assertEqual({item['item'] for item in dry_run['conflicts']},
                         {'identity', 'earned XP', 'room bond'})
        self.assertIn({'item': 'earned XP', 'current': 7, 'incoming': 34}, dry_run['conflicts'])
        self.assertEqual((self.target / 'identity.json').read_bytes(), before['identity.json'])
        result = transfer.import_transfer(transfer.load_transfer(archive), self.target, apply=True)
        self.assertTrue(Path(result['backup']).is_dir())
        self.assertEqual(self.data(self.target, 'identity.json')['name'], 'Wisp')
        self.assertEqual(self.data(self.target, 'growth.json')['xp'], 34)
        self.assertEqual(self.data(self.target, 'room.json')['bond'], 6)
        self.assertEqual(self.data(self.target, 'room.json')['notes'][0]['text'], 'keep my note')
        self.assertEqual((self.target / 'history.json').read_bytes(), before['history.json'])
        self.assertEqual(self.data(self.target, 'room.json.bak')['notes'][0]['text'], 'keep my note')
        growth = self.data(self.target, 'growth.json')
        self.assertEqual(growth['snapshot']['files'], {})
        self.assertNotIn('presence_seconds', growth)
        settings = self.data(self.target, 'awareness-settings.json')
        self.assertFalse(settings['enabled'])
        self.assertFalse(settings['titles'])
        self.assertFalse(settings['mouse_gestures'])
        self.assertEqual(self.data(self.target, 'position.json')['x'], 24)
        self.assertFalse(self.data(self.target, 'position.json')['voice'])
        restore_preview = transfer.restore_backup(result['backup'], self.target)
        self.assertFalse(restore_preview.get('applied', False))
        restored = transfer.restore_backup(result['backup'], self.target, apply=True)
        self.assertTrue(Path(restored['safetyBackup']).is_dir())
        for name, raw in before.items():
            self.assertEqual((self.target / name).read_bytes(), raw)

    def test_explicit_notes_and_chat_are_selective_and_validated(self):
        archive = self.root / 'private-transfer.json'
        transfer.export_transfer(archive, self.source,
                                 sections='identity,growth,room,settings',
                                 include_notes=True, include_chat=True)
        payload = transfer.load_transfer(archive)
        self.assertEqual(payload['sections'][-1], 'chat')
        self.assertTrue(payload['notesIncluded'])
        self.assertEqual(transfer.preview(payload)['chatEntries'], 1)
        self.assertIn(b'private room note', archive.read_bytes())
        transfer.import_transfer(payload, self.target, sections='identity,room', skip_notes=True, apply=True)
        self.assertEqual(self.data(self.target, 'room.json')['notes'][0]['text'], 'keep my note')
        self.assertEqual(self.data(self.target, 'history.json')[0]['content'], 'Existing chat')
        transfer.import_transfer(payload, self.target, sections='room,chat', apply=True)
        self.assertEqual(self.data(self.target, 'room.json')['notes'][0]['text'], 'private room note')
        self.assertEqual(self.data(self.target, 'history.json')[0]['content'], 'Hello from the old machine')

    def test_malformed_sections_duplicate_json_and_symlink_are_rejected_without_writes(self):
        payload = transfer.build_transfer(self.source, sections='identity,growth,room,settings')
        original = (self.target / 'identity.json').read_bytes()
        for bad in (
            dict(payload, data={**payload['data'], '../../evil': {}}),
            dict(payload, version=99),
            dict(payload, notesIncluded=False, data={**payload['data'], 'room': self.original['room.json']}),
        ):
            with self.subTest(bad=bad.get('version'), payload=bad):
                with self.assertRaises(ValueError):
                    transfer.import_transfer(bad, self.target, apply=True)
                self.assertEqual((self.target / 'identity.json').read_bytes(), original)
        duplicate = self.root / 'duplicate.json'
        duplicate.write_text('{"format":"one","format":"two"}')
        with self.assertRaises(ValueError):
            transfer.load_transfer(duplicate)
        link = self.root / 'link.json'
        link.symlink_to(duplicate)
        with self.assertRaises(OSError):
            transfer.load_transfer(link)

    def test_failed_second_file_write_restores_all_original_bytes(self):
        payload = transfer.build_transfer(self.source, sections='identity,growth,room,settings')
        before = {name: (self.target / name).read_bytes() for name in
                  ('identity.json', 'growth.json', 'room.json', 'awareness-settings.json', 'position.json')}
        actual = transfer._atomic_bytes
        failed = False

        def fail_once(path, raw, replace=True):
            nonlocal failed
            if Path(path) == self.target / 'growth.json' and not failed:
                failed = True
                raise OSError('simulated disk full')
            return actual(path, raw, replace)

        with patch.object(transfer, '_atomic_bytes', side_effect=fail_once):
            with self.assertRaises(OSError):
                transfer.import_transfer(payload, self.target, apply=True)
        self.assertTrue(failed)
        for name, raw in before.items():
            self.assertEqual((self.target / name).read_bytes(), raw)
        self.assertEqual(len(list(self.target.glob('transfer-backup-*'))), 1)

    def test_retained_backup_restores_a_mixed_generation_after_interruption(self):
        payload = transfer.build_transfer(self.source, sections='identity,growth,room')
        touched = ('identity.json', 'growth.json', 'room.json')
        before = {name + suffix: ((self.target / (name + suffix)).read_bytes()
                                  if (self.target / (name + suffix)).exists() else None)
                  for name in touched for suffix in ('', '.bak')}
        unrelated = (self.target / 'history.json').read_bytes()
        result = transfer.import_transfer(payload, self.target, apply=True)
        self.assertEqual(self.data(self.target, 'identity.json')['name'], 'Wisp')
        # Model a crash between replacements: some files have the imported
        # generation while another has its old bytes again.
        (self.target / 'growth.json').write_bytes(before['growth.json'])
        transfer.restore_backup(result['backup'], self.target, apply=True)
        for name, raw in before.items():
            path = self.target / name
            self.assertEqual(path.read_bytes() if path.exists() else None, raw)
        self.assertEqual((self.target / 'history.json').read_bytes(), unrelated)


if __name__ == '__main__':
    unittest.main()
