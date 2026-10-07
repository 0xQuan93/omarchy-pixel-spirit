"""Native help can describe reviewed controls without discovering executable actions."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / 'plugin'))

import native_guide


class NativeGuideTests(unittest.TestCase):
    def test_installed_catalogue_confirms_only_safe_display_routes(self):
        rows = {'ok': True, 'commands': [
            {'route': 'omarchy launch browser', 'summary': 'Open browser', 'hidden': False},
            {'route': 'omarchy launch browser; touch /tmp/no', 'summary': 'Injected'},
            {'route': 'omarchy system shutdown', 'summary': 'Shutdown', 'requires_sudo': True},
        ]}
        routes = native_guide._routes(rows)
        self.assertEqual(routes, {'omarchy launch browser': 'Open browser'})
        info = native_guide.details('browser', routes)
        self.assertEqual(info['nativeRoute'], 'omarchy launch browser')
        self.assertNotIn('nativeRoute', native_guide.details('terminal', routes))
        self.assertEqual(native_guide.details('unregistered-from-manifest', routes), {})

    def test_informational_question_is_local_and_nonexecuting(self):
        response = native_guide.reply('How do I open the browser in Omarchy?',
                                      {'omarchy launch browser': 'Open browser'})
        self.assertEqual(response['route'], 'local')
        self.assertEqual(response['action'], '')
        self.assertIn('Super + Shift + Return', response['text'])
        self.assertIn('omarchy launch browser', response['text'])
        self.assertEqual(response['helpTopic'], 'omarchy.native.browser')

    def test_action_request_and_unknown_target_fall_through(self):
        routes = {'omarchy launch browser': 'Open browser'}
        self.assertIsNone(native_guide.reply('open the browser in Omarchy', routes))
        self.assertIsNone(native_guide.reply('How do I open my secret app in Omarchy?', routes))
        self.assertIsNone(native_guide.reply('How do I open browser; run code in Omarchy?', routes))

    def test_bad_catalogue_does_not_hide_default_shortcut(self):
        self.assertEqual(native_guide._routes({'ok': True, 'commands': 'bad'}), {})
        info = native_guide.details('browser', {})
        self.assertEqual(info['nativeShortcut'], 'Super + Shift + Return')
        self.assertNotIn('nativeRoute', info)


if __name__ == '__main__':
    unittest.main()
