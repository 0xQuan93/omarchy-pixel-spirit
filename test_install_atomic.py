"""Installer writes use only a temporary home and an inert discovery subprocess."""
import contextlib
import io
import json
import os
from pathlib import Path
import runpy
import stat
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parent


class AtomicInstallWrites(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.home = Path(temporary.name)
        config = self.home / '.config/omarchy'
        config.mkdir(parents=True)
        (config / 'shell.json').write_text(json.dumps({'bar': {'layout': {'left': []}}, 'plugins': []}))
        with patch.object(Path, 'home', return_value=self.home), \
             patch.object(sys, 'argv', ['install.py']), patch('subprocess.run'), \
             contextlib.redirect_stdout(io.StringIO()):
            namespace = runpy.run_path(str(ROOT / 'install.py'), run_name='__main__')
        self.write = namespace['write']
        self.stamp = namespace['stamp']
        self.target = self.home / 'shell.json'
        self.original = b'{"existing": true}\n'
        self.updated = b'{"existing": true, "wisp": true}\n'
        self.target.write_bytes(self.original)
        self.target.chmod(0o640)

    def backup(self):
        return self.target.with_name(self.target.name + '.before-wisp-' + self.stamp)

    def assert_no_temporary_files(self):
        self.assertEqual(list(self.home.glob('.shell.json.wisp-*')), [])

    def test_success_replaces_only_after_complete_synced_write_and_preserves_mode(self):
        replace = os.replace
        def observe(source, destination):
            self.assertEqual(Path(source).parent, self.target.parent)
            self.assertEqual(Path(destination), self.target)
            self.assertEqual(self.target.read_bytes(), self.original)
            self.assertEqual(Path(source).read_bytes(), self.updated)
            self.assertEqual(stat.S_IMODE(Path(source).stat().st_mode), 0o640)
            self.assertEqual(synced.call_count, 2)  # Backup and replacement both synced.
            return replace(source, destination)
        with patch('os.fsync', wraps=os.fsync) as synced, patch('os.replace', side_effect=observe):
            self.write(self.target, self.updated)
        self.assertEqual(self.target.read_bytes(), self.updated)
        self.assertEqual(self.backup().read_bytes(), self.original)
        self.assertEqual(stat.S_IMODE(self.target.stat().st_mode), 0o640)
        self.assert_no_temporary_files()

    def test_failed_sync_or_replace_keeps_original_and_backup_and_cleans_temp(self):
        for operation in ('os.fsync', 'os.replace'):
            with self.subTest(operation=operation), patch(operation, side_effect=OSError('simulated disk failure')):
                with self.assertRaises(OSError):
                    self.write(self.target, self.updated)
            self.assertEqual(self.target.read_bytes(), self.original)
            if operation == 'os.replace':
                self.assertEqual(self.backup().read_bytes(), self.original)
            else:
                self.assertFalse(self.backup().exists())
            self.assertEqual(stat.S_IMODE(self.target.stat().st_mode), 0o640)
            self.assert_no_temporary_files()

    def test_unchanged_write_has_no_backup_or_replacement(self):
        before = self.target.stat()
        with patch('os.replace', side_effect=AssertionError('unchanged file replaced')):
            self.write(self.target, self.original)
        self.assertEqual(self.target.stat().st_ino, before.st_ino)
        self.assertFalse(self.backup().exists())
        self.assert_no_temporary_files()

    def test_partial_write_failure_cannot_truncate_live_configuration(self):
        fdopen = os.fdopen
        @contextlib.contextmanager
        def short_writer(fd, mode):
            with fdopen(fd, mode) as stream:
                def fail_after_prefix(data):
                    stream.write(data[:5])
                    raise OSError('simulated full disk')
                yield SimpleNamespace(fileno=stream.fileno, write=fail_after_prefix)
        # Fail the replacement, after the backup has completed normally.
        calls = 0
        def replacement_only(fd, mode):
            nonlocal calls
            calls += 1
            return fdopen(fd, mode) if calls == 1 else short_writer(fd, mode)
        with patch('os.fdopen', side_effect=replacement_only):
            with self.assertRaises(OSError):
                self.write(self.target, self.updated)
        self.assertEqual(self.target.read_bytes(), self.original)
        self.assertEqual(self.backup().read_bytes(), self.original)
        self.assert_no_temporary_files()

    def test_same_timestamp_keeps_each_distinct_previous_value(self):
        self.write(self.target, self.updated)
        newest = b'{"latest": true}\n'
        self.write(self.target, newest)
        self.assertEqual(self.backup().read_bytes(), self.original)
        second = self.backup().with_name(self.backup().name + '-1')
        self.assertEqual(second.read_bytes(), self.updated)
        self.assertEqual(self.target.read_bytes(), newest)
        self.assertEqual(stat.S_IMODE(second.stat().st_mode), 0o640)

    def test_replacement_sync_failure_preserves_completed_backup(self):
        with patch('os.fsync', side_effect=[None, OSError('replacement sync failed')]):
            with self.assertRaises(OSError):
                self.write(self.target, self.updated)
        self.assertEqual(self.target.read_bytes(), self.original)
        self.assertEqual(self.backup().read_bytes(), self.original)
        self.assert_no_temporary_files()

    def test_failed_backup_copy_removes_partial_backup_and_preserves_original(self):
        def partial_copy(source, destination):
            destination.write(source.read(4))
            raise OSError('backup disk full')
        with patch('shutil.copyfileobj', side_effect=partial_copy):
            with self.assertRaises(OSError):
                self.write(self.target, self.updated)
        self.assertEqual(self.target.read_bytes(), self.original)
        self.assertFalse(self.backup().exists())
        self.assert_no_temporary_files()

    def test_existing_symlink_stays_linked_and_target_is_atomic(self):
        actual = self.home / 'dotfiles' / 'shell.json'
        actual.parent.mkdir()
        self.target.rename(actual)
        self.target.symlink_to(actual)
        self.write(self.target, self.updated)
        self.assertTrue(self.target.is_symlink())
        self.assertEqual(actual.read_bytes(), self.updated)
        self.assertEqual(stat.S_IMODE(actual.stat().st_mode), 0o640)
        self.assertEqual(self.backup().read_bytes(), self.original)
        self.assertEqual(list(actual.parent.glob('.shell.json.wisp-*')), [])

    def test_install_preserves_explicit_disable_and_explains_how_to_enable(self):
        shell = self.home / '.config/omarchy/shell.json'
        config = json.loads(shell.read_text())
        config['disabledPlugins'] = ['example.clock', 'oxquan.pixel-spirit']
        shell.write_text(json.dumps(config))
        output = io.StringIO()
        with patch.object(Path, 'home', return_value=self.home), \
             patch.object(sys, 'argv', ['install.py']), patch('subprocess.run'), \
             contextlib.redirect_stdout(output):
            runpy.run_path(str(ROOT / 'install.py'), run_name='__main__')
        self.assertEqual(json.loads(shell.read_text())['disabledPlugins'], config['disabledPlugins'])
        self.assertIn('Wisp installed but disabled.', output.getvalue())
        self.assertIn('Setup > Plugins > Enable Plugin', output.getvalue())
        self.assertIn('oxquan.pixel-spirit', output.getvalue())


if __name__ == '__main__':
    unittest.main()
