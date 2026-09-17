import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).parent / 'plugin'))
import omarchy_help


class OmarchyHelpTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.system = self.root / 'system'
        self.home = self.root / 'home'
        self.config = self.home / '.config'
        (self.system / 'default').mkdir(parents=True)
        self.env = patch.dict(os.environ, {'OMARCHY_PATH': str(self.system),
                                          'XDG_CONFIG_HOME': str(self.config)})
        self.env.start()
        self.addCleanup(self.env.stop)
        self.home_patch = patch.object(omarchy_help.Path, 'home', return_value=self.home)
        self.home_patch.start()
        self.addCleanup(self.home_patch.stop)

    def write(self, root, relative, content='reference'):
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content)
        return path

    def test_curated_topics_and_conversational_variants(self):
        examples = {
            'overview': ['tell me about Omarchy', 'what is Omarchy', 'what’s Omarchy?',
                         'Hey Zephyr, could you please tell me about Omarchy?',
                         'please explain Omarchy', 'give me an overview of Omarchy',
                         'what can you tell me about Omarchy', 'Omarchy',
                         'tell me more about Omarchy', 'what exactly is Omarchy',
                         'give me some information about Omarchy', 'Omarchy overview',
                         'tell me about the Omarchy ecosystem'],
            'start': ['help me learn Omarchy', 'teach me Omarchy', "I'm new to Omarchy",
                      'I’d like to learn Omarchy', 'where do I start with Omarchy',
                      'getting started with Omarchy', 'how do I get started with Omarchy',
                      'Omarchy for beginners', 'show me around Omarchy', 'how does Omarchy work',
                      'get me started with Omarchy', "I'm confused by Omarchy",
                      'help me learn about Omarchy'],
            'docs': ['Omarchy docs', 'where can I find the Omarchy manual',
                     'show me local resources for Omarchy', 'Omarchy offline docs',
                     'find me the documentation for Omarchy', 'Omarchy guide please'],
            'keys': ['what are the keyboard shortcuts for Omarchy', 'Omarchy hotkeys',
                     'tell me about Omarchy keybindings', 'how do I navigate Omarchy',
                     'what does the Super key mean in Omarchy'],
            'themes': ['how do I change themes in Omarchy', 'how can I change my Omarchy theme',
                       'how do I customize the appearance in Omarchy', 'Omarchy themes help'],
            'plugins': ['tell me about Omarchy plugins', 'how do I install a plugin in Omarchy',
                        'how do I create an Omarchy plugin', 'Omarchy shell plugins'],
            'commands': ['Omarchy commands', 'how do I use the Omarchy CLI',
                         'how can I list all the Omarchy commands', 'Omarchy terminal commands'],
            'config': ['where are my Omarchy config files', 'how can I configure Omarchy',
                       'tell me about Omarchy dotfiles', 'Omarchy configuration'],
        }
        for topic, phrases in examples.items():
            for phrase in phrases:
                with self.subTest(phrase=phrase):
                    result = omarchy_help.reply(phrase)
                    self.assertIsNotNone(result)
                    self.assertEqual(result['helpTopic'], 'omarchy.' + topic)
                    self.assertEqual(result['route'], 'local')
                    self.assertEqual(result['action'], '')

    def test_commands_negation_quotations_and_uncovered_questions_fall_through(self):
        for phrase in ['change the theme', 'open Omarchy', 'open the Omarchy menu',
                       'install an Omarchy plugin', 'remove Omarchy', 'do not tell me about Omarchy',
                       "don't show me Omarchy docs", 'tell me about Omarchy and open the browser',
                       'tell me about Omarchy; shut down', 'tell me about Omarchy\nopen files',
                       'tell me about Omarchy: https://example.com', '"tell me about Omarchy"',
                       '“what is Omarchy”', "'what is Omarchy'", '`what is Omarchy`',
                       'my friend said tell me about Omarchy', 'Omarchy docs are useful',
                       'why is Omarchy crashing', 'how do I encrypt my drive in Omarchy',
                       'what is Omarchy doing with my passwords', 'what is Omarchy vs Fedora',
                       'tell me about my life', '', None, 42, 'x' * 301]:
            with self.subTest(phrase=phrase):
                self.assertIsNone(omarchy_help.reply(phrase))

    def test_installed_references_are_local_and_nothing_is_created(self):
        keys = self.write(self.system, 'default/hypr/bindings/utilities.lua')
        shell = self.write(self.system, 'shell/README.md')
        result = omarchy_help.reply('tell me about Omarchy')
        local = [r for r in result['resources'] if r['kind'] == 'local']
        self.assertEqual([r['url'] for r in local], [keys.as_uri(), shell.as_uri()])
        self.assertIn('Super + Space opens the Omarchy menu', result['text'])
        self.assertIn('Default keys:', result['text'])
        self.assertIn('override', result['text'])
        self.assertFalse(self.config.exists())

    def test_missing_local_references_use_official_manual(self):
        result = omarchy_help.reply('Omarchy docs')
        self.assertEqual(result['resources'], [{'label': 'Omarchy manual',
                          'url': 'https://omarchy.org/manual/', 'kind': 'official'}])
        self.assertNotIn('file:', result['text'])

    def test_legacy_installed_bindings_use_legacy_menu_key(self):
        keys = self.write(self.system, 'default/hypr/bindings/utilities.conf')
        result = omarchy_help.reply('Omarchy shortcuts')
        self.assertIn('Super + Alt + Space opens the Omarchy menu', result['text'])
        self.assertEqual(result['resources'][0]['url'], keys.as_uri())

    def test_resource_links_do_not_escape_reviewed_roots(self):
        outside = self.write(self.root, 'secret.txt')
        (self.system / 'shell').mkdir()
        (self.system / 'shell/README.md').symlink_to(outside)
        result = omarchy_help.reply('Omarchy docs')
        self.assertEqual([r['kind'] for r in result['resources']], ['official'])
        self.assertNotIn(str(outside), result['text'])

    def test_user_references_follow_omarchy_config_root(self):
        binding = self.write(self.config, 'hypr/bindings.lua')
        self.write(self.config, 'omarchy/shell.json')
        other_config = self.root / 'other-config'
        self.write(other_config, 'hypr/bindings.lua')
        with patch.dict(os.environ, {'XDG_CONFIG_HOME': str(other_config)}):
            result = omarchy_help.reply('Omarchy config')
        self.assertEqual(result['resources'][0]['url'], binding.as_uri())
        self.assertNotIn(str(other_config), result['text'])

    def test_directories_are_not_offered_as_reference_files(self):
        (self.system / 'shell/README.md').mkdir(parents=True)
        result = omarchy_help.reply('Omarchy docs')
        self.assertEqual([r['kind'] for r in result['resources']], ['official'])

    def test_official_links_are_static_even_with_no_local_install(self):
        for noun in ('docs', 'hotkeys', 'themes', 'plugins', 'commands', 'configuration'):
            result = omarchy_help.reply('Omarchy ' + noun)
            for resource in result['resources']:
                self.assertTrue(resource['url'].startswith('https://omarchy.org/manual/')
                                or resource['url'] == 'https://plugins.omarchy.org/')
                self.assertIn(resource['url'], result['text'])


if __name__ == '__main__':
    unittest.main()
