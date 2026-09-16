"""Pure phrase-routing regression checks; never execute desktop actions."""
import unittest
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent / 'plugin'))

from smart_commands import LOOKUP, PHRASES, match, normalize


class SmartCommandTests(unittest.TestCase):
    def test_every_phrase_and_collision(self):
        seen = {}
        for action, phrases in PHRASES.items():
            for phrase in phrases:
                with self.subTest(action=action, phrase=phrase):
                    key = normalize(phrase)
                    self.assertTrue(key)
                    self.assertEqual(seen.setdefault(key, action), action)
                    self.assertEqual(match(phrase), action)
                    self.assertEqual(LOOKUP[key], action)

    def test_every_phrase_stays_bounded(self):
        for action, phrases in PHRASES.items():
            for phrase in phrases:
                for message in ("don't " + phrase, 'how do i ' + phrase,
                                'explain ' + phrase, phrase + ' tomorrow',
                                '"' + phrase + '"', phrase + ' and open terminal'):
                    with self.subTest(message=message):
                        self.assertEqual(match(message), '')

    def test_politeness(self):
        for message in (
            'Change the theme', 'Hey Wisp, could you please change the theme for me?',
            'Wisp, change the theme!', 'please, change the theme please',
            'I would like you to change the theme now.',
            'Would you mind changing the theme?', 'Do you mind changing the theme?',
            'ＣＨＡＮＧＥ　ＴＨＥ　ＴＨＥＭＥ',
        ):
            with self.subTest(message=message):
                self.assertEqual(match(message), 'theme_picker')

    def test_representative_actions(self):
        cases = {
            'turn off my microphone': 'mic_mute', 'turn on my microphone': 'mic_unmute',
            'open a terminal': 'terminal', 'show my files': 'files',
            'open my browser': 'browser', 'open obsidian': 'notes',
            'pause this song': 'pause_music', 'resume playback': 'play_music',
            'skip this track': 'next_track', 'go back one track': 'previous_track',
            'make it louder': 'volume_up', 'turn the volume down': 'volume_down',
            'mute': 'mute', 'unmute the sound': 'unmute',
            'dim my screen': 'brightness_down', 'brighten the display': 'brightness_up',
            'next workspace': 'workspace_next', 'previous desktop': 'workspace_previous',
            'pause notifications': 'dnd_on', 'resume notifications': 'dnd_off',
            'save battery': 'power_saver', 'disable battery saver': 'power_balanced',
            'show my reminders': 'reminders', 'open bluetooth settings': 'settings_bluetooth',
            'show keyboard shortcuts': 'keybindings',
            'change my wallpaper': 'background_picker', 'next wallpaper': 'background_next',
            'open clipboard history': 'clipboard', 'toggle night light': 'nightlight_toggle',
        }
        for message, action in cases.items():
            with self.subTest(message=message):
                self.assertEqual(match(message), action)

    def test_unsupported_meaning_does_not_disappear(self):
        messages = (
            'do not change the theme', 'never change the theme',
            'can you explain how to change the theme', 'why did you change the theme',
            'i just tried to change the theme', 'i might change the theme',
            'if i change the theme', 'change the theme if possible',
            'change the theme to catppuccin', 'change the theme tomorrow',
            'change the theme and open files', 'open files then change the theme',
            'please say change the theme', 'what does change the theme mean',
            '“change the theme”', '‘change the theme’', '`change the theme`',
            "'change the theme'", 'change the theme; open terminal',
            'change the theme\nopen terminal', 'change\rthe theme',
            'enable fullscreen', 'disable floating', 'turn off window gaps',
            'go to workspace 11', 'send this window to workspace 0',
            'go to workspace -1', 'move this window to workspace 100',
            'set brightness to 50%', 'turn up the volume by 20%',
            'open browser https://example.com', 'open terminal && echo hello',
            'next theme', 'delete my files', '', None, 42, ['open files'],
            'please ' * 40 + 'open files',
        )
        for message in messages:
            with self.subTest(message=message):
                self.assertEqual(match(message), '')

    def test_meaningful_scale_and_implemented_actions(self):
        from capabilities import ACTIONS
        self.assertGreaterEqual(len(LOOKUP), 10000)
        core = {normalize(phrase) for phrases in PHRASES.values() for phrase in phrases
                if not phrase.startswith(('would you mind ', 'do you mind '))}
        self.assertGreaterEqual(len(core), 10000)
        self.assertEqual(set(PHRASES) - set(ACTIONS), set())

    def test_realistic_natural_requests(self):
        cases = {
            'let me see my clipboard history': 'clipboard',
            'bring me to the audio controls': 'settings_audio',
            'take me to the theme chooser': 'theme_picker',
            'i want to change my desktop theme': 'theme_picker',
            'help me choose a theme': 'theme_picker',
            'let me pick a new wallpaper': 'background_picker',
            'show me the available fonts': 'font_picker',
            'view the keyboard shortcuts': 'keybindings',
            'open my default browser': 'browser',
            'get me to the command line': 'terminal',
            'bring up the file browser': 'files',
            'show me my scheduled reminders': 'reminders',
            'show me the network connections': 'settings_network',
            'connect to wifi': 'settings_network',
            'pair my headphones': 'settings_bluetooth',
            'choose my microphone': 'settings_audio',
            'configure my monitors': 'settings_display',
            'review the appearance settings': 'appearance',
            'manage my plugins': 'plugins',
            'change my default apps': 'default_apps',
            'open the software installation menu': 'install_menu',
            'take me to software update options': 'update_menu',
            'show me omarchy guides': 'learn_menu',
            'open shutdown options': 'power_menu',
            'show me the recording options': 'recording_menu',
            'get me to screenshot options': 'capture_menu',
            'bring up my system information': 'about',
            'pause the media playback': 'pause_music',
            'continue the track': 'play_music',
            'put on the next audio track': 'next_track',
            'skip back a song': 'previous_track',
            'make my speakers quieter': 'volume_down',
            'increase the audio volume': 'volume_up',
            'silence desktop audio': 'mute',
            'unmute my audio output': 'unmute',
            'make my monitor dimmer': 'brightness_down',
            'raise the brightness of my screen': 'brightness_up',
            'go to the next virtual desktop': 'workspace_next',
            'switch to the previous virtual desktop': 'workspace_previous',
            'mute my notifications': 'dnd_on',
            'allow notification alerts': 'dnd_off',
            'put the computer in battery saver mode': 'power_saver',
            'return to the balanced power profile': 'power_balanced',
            'display the next desktop background': 'background_next',
            'unhide my top bar': 'bar_show',
            'hide my status bar': 'bar_hide',
            'keep my computer awake': 'idle_inhibit',
            'let my screen sleep when idle': 'idle_allow',
            'turn on night light': 'nightlight_on',
            'turn off night light': 'nightlight_off',
            'switch on bluetooth': 'bluetooth_on',
            'disable the bluetooth radio': 'bluetooth_off',
            'mute myself': 'mic_mute',
            'unmute my microphone': 'mic_unmute',
            'brighten the keyboard': 'keyboard_brightness_up',
            'dim the keyboard': 'keyboard_brightness_down',
            'switch off my keyboard backlight': 'keyboard_brightness_off',
            'restore my keyboard backlight': 'keyboard_brightness_restore',
            'cycle audio outputs': 'audio_output_next',
            'take a screenshot': 'screenshot',
            'copy the text on my screen': 'capture_text',
            'scan the onscreen qr code': 'capture_qr',
            'finish my screen recording': 'recording_stop',
            'change my default browser': 'default_browser',
            'choose a default terminal': 'default_terminal',
            'open default editor settings': 'default_editor',
            'focus the window on the left': 'window_focus_left',
            'switch to the window above': 'window_focus_up',
            'swap this window with the window below': 'window_swap_down',
            'exchange the active window with the window on the right': 'window_swap_right',
            'cycle to the next window': 'window_next',
            'activate the previous window': 'window_previous',
            'close the focused app window': 'window_close',
            'toggle fullscreen for this window': 'window_fullscreen_toggle',
            'toggle maximization on the current window': 'window_maximize_toggle',
            'toggle floating for the focused window': 'window_float_toggle',
            'go to workspace 3': 'workspace_3',
            'switch to the tenth desktop': 'workspace_10',
            'move this window to workspace five': 'window_workspace_5',
            'put the active window on the first virtual desktop': 'window_workspace_1',
            'return to the workspace i was on': 'workspace_former',
            'move focus to the next monitor': 'monitor_next',
            'switch to the previous display': 'monitor_previous',
            'toggle my scratchpad': 'scratchpad_toggle',
            'send this window to the scratchpad': 'window_to_scratchpad',
            'toggle gaps between windows': 'window_gaps_toggle',
            'toggle window transparency': 'window_transparency_toggle',
            'toggle my workspace layout': 'workspace_layout_toggle',
        }
        for message, action in cases.items():
            with self.subTest(message=message):
                self.assertEqual(match(message), action)

    def test_action_filter(self):
        self.assertEqual(match('change the theme', {'theme_picker'}), 'theme_picker')
        self.assertEqual(match('change the theme', {'browser'}), '')
        self.assertEqual(match('open browser', {}), '')
        self.assertEqual(match('open browser', {'browser': ['fixed', 'argv']}), 'browser')


if __name__ == '__main__':
    unittest.main()
