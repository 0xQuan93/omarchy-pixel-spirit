import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).parent / 'plugin'))
import command_bank as bank


class CommandBankTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.config, self.system, self.state = [self.root / p for p in ('config', 'system', 'state')]
        self.config.mkdir(); self.state.mkdir()
        self.kw = dict(state_dir=self.state, config_dir=self.config, system_dir=self.system)
        (self.system / 'themes/tokyo-night').mkdir(parents=True)

    def plugin(self, ident='demo.weather', name='Weather', kinds=None):
        kinds = kinds or ['panel']
        path = self.config / 'plugins' / ident / 'manifest.json'
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(dict(schemaVersion=1, id=ident, name=name, version='1',
                                       kinds=kinds, entryPoints={k: 'Panel.qml' for k in kinds})))
        (self.config / 'shell.json').write_text(json.dumps({'plugins': [{'id': ident}]}))
        return path

    def test_named_theme_and_runtime_removal(self):
        descriptor = bank.match('Could you switch the theme to Tokyo Night please?', **self.kw)
        self.assertEqual(bank.resolve(descriptor, **self.kw), ['omarchy', 'theme', 'set', 'tokyo-night'])
        (self.system / 'themes/tokyo-night').rmdir()
        with self.assertRaises(ValueError): bank.resolve(descriptor, **self.kw)
        self.assertIsNone(bank.match('switch theme to tokyo night', **self.kw))

    def test_plugin_lifecycle_and_disabled(self):
        self.plugin()
        descriptor = bank.match('open weather', **self.kw)
        self.assertEqual(bank.resolve(descriptor, **self.kw), ['omarchy', 'shell', 'shell', 'summon', 'demo.weather', '{}'])
        (self.config / 'shell.json').write_text('{"plugins":[{"id":"demo.weather"}],"disabledPlugins":["demo.weather"]}')
        self.assertIsNone(bank.match('open weather', **self.kw))
        with self.assertRaises(ValueError): bank.resolve(descriptor, **self.kw)

    def test_everyday_named_requests_keep_exact_target_and_direction(self):
        self.plugin()
        for phrase in ('show me the weather plugin', 'pull up weather',
                       'let me see weather', 'take me to weather plugin'):
            self.assertEqual(bank.match(phrase, **self.kw)['target'], 'demo.weather')
        for phrase in ('apply the Tokyo Night theme', 'use Tokyo Night as my theme',
                       'switch to Tokyo Night theme', 'make Tokyo Night my theme'):
            self.assertEqual(bank.match(phrase, **self.kw)['target'], 'tokyo-night')
        for phrase in ('close weather', 'hide weather', 'take me to weather later',
                       'do not apply the Tokyo Night theme', 'show me weather and open files'):
            self.assertIsNone(bank.match(phrase, **self.kw))

    def test_bar_and_service_do_not_create_unsafe_open_alias(self):
        for kind in ('bar-widget', 'service'):
            self.plugin(kinds=[kind])
            self.assertIsNone(bank.match('open weather', **self.kw))
            self.assertEqual(len(bank.scan(**self.kw)['plugins']), 1)

    def test_user_plugin_cannot_claim_reserved_namespace(self):
        self.plugin(ident='omarchy.fake', name='Fake')
        self.assertIsNone(bank.match('open fake', **self.kw))
        self.assertEqual(bank.scan(**self.kw)['plugins'], [])

    def test_tampered_generated_bank_is_not_executable(self):
        (self.state / bank.GENERATED).write_text('{"aliases":{"open evil":{"argv":["sh","-c","bad"]}}}')
        self.assertIsNone(bank.match('open evil', **self.kw))
        with self.assertRaises(ValueError): bank.resolve({'kind': 'theme', 'target': '$(bad)'}, **self.kw)

    def test_personal_aliases_are_preserved_and_collisions_removed(self):
        self.plugin()
        personal = [{'phrase': 'my colors', 'kind': 'theme', 'target': 'tokyo-night', 'argv': ['bad']},
                    {'phrase': 'open weather', 'kind': 'theme', 'target': 'tokyo-night'}]
        raw = json.dumps(personal)
        (self.state / bank.PERSONAL).write_text(raw)
        self.assertEqual(bank.match('my colors', **self.kw)['kind'], 'theme')
        self.assertIsNone(bank.match('open weather', **self.kw))
        self.assertEqual((self.state / bank.PERSONAL).read_text(), raw)

    def test_bad_metadata_and_special_files(self):
        path = self.plugin()
        path.write_text('[' * 10000)
        self.assertIsNone(bank.match('open weather', **self.kw))
        path.unlink(); path.symlink_to(self.config / 'shell.json')
        self.assertIsNone(bank.match('open weather', **self.kw))
        path.unlink()
        import os
        os.mkfifo(path)
        self.assertIsNone(bank.match('open weather', **self.kw))

    def test_exact_phrases_only(self):
        for phrase in ('do not switch theme to tokyo night', 'if possible switch theme to tokyo night',
                       'why would I switch theme to tokyo night', 'switch theme to tokyo night and reboot'):
            self.assertIsNone(bank.match(phrase, **self.kw))

    def test_shared_normalization_and_legitimate_plugin_names(self):
        self.plugin(name='Wisp · Machine Familiar')
        self.assertEqual(len(bank.scan(**self.kw)['plugins']), 1)
        self.assertIsNotNone(bank.match('please change my theme to Tokyo Night', **self.kw))
        self.assertIsNone(bank.match('switch theme to tokyo night; reboot', **self.kw))

    def test_read_only_state_still_matches_and_reports_unsaved_bank(self):
        for operation in ('tempfile.mkstemp', 'os.replace'):
            with patch('command_bank.' + operation, side_effect=PermissionError('read only')):
                result = bank.scan(**self.kw)
                self.assertIn('persistence_warning', result)
                self.assertIsNotNone(bank.match('change my theme to tokyo night', **self.kw))
                self.assertIsNone(bank.match('hello', **self.kw))
        self.assertFalse(list(self.state.glob('.command-bank-*')))
        with patch.object(Path, 'mkdir', side_effect=PermissionError('read only')):
            self.assertIn('persistence_warning', bank.scan(**self.kw))

    def test_personal_negation_and_compound_are_not_commands(self):
        phrases = ["do not change colors", "don't change colors", 'if I change colors',
                   'my colors and reboot', 'my colors then open browser']
        (self.state / bank.PERSONAL).write_text(json.dumps([
            {'phrase': p, 'kind': 'theme', 'target': 'tokyo-night'} for p in phrases]))
        for phrase in phrases:
            self.assertIsNone(bank.match(phrase, **self.kw))

    def test_no_rewrite_when_unchanged(self):
        bank.scan(**self.kw)
        before = (self.state / bank.GENERATED).stat().st_mtime_ns
        bank.scan(**self.kw)
        self.assertEqual(before, (self.state / bank.GENERATED).stat().st_mtime_ns)


if __name__ == '__main__':
    unittest.main()
