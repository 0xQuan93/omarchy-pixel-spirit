"""Theme colors use Omarchy's configuration root and remain safe SVG colors."""
import importlib.util
import os
import subprocess
import sys
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

SPEC = importlib.util.spec_from_file_location('artwork_palette_test', Path(__file__).parent / 'plugin/artwork.py')
artwork = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(artwork)


class ThemePaletteTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.home = Path(self.temp.name)
        self.path = self.home / '.config/omarchy/current/theme/colors.toml'
        self.path.parent.mkdir(parents=True)
        self.home_patch = patch.object(artwork.Path, 'home', return_value=self.home)
        self.home_patch.start()
        self.addCleanup(self.home_patch.stop)

    def test_actual_config_root_and_supported_colors(self):
        self.path.write_text('accent = "#AAbb33"\nforeground = "#112233FF"\nbackground = "#010203"\ncolor0 = "#556677"\n')
        with patch.dict(os.environ, {'XDG_CONFIG_HOME': str(self.home / 'elsewhere')}):
            self.assertEqual(artwork.theme_palette(), {'accent': '#AAbb33', 'foreground': '#112233FF', 'background': '#010203'})

    def test_missing_malformed_and_oversized_use_defaults(self):
        self.assertEqual(artwork.theme_palette(), artwork.DEFAULT_PALETTE)
        for content in (b'accent = [', b'\xff', b'#' * 65537):
            with self.subTest(content=content[:20]):
                self.path.write_bytes(content)
                self.assertEqual(artwork.theme_palette(), artwork.DEFAULT_PALETTE)

    def test_fifo_is_rejected_without_waiting_for_a_writer(self):
        os.mkfifo(self.path)
        script = 'import runpy,sys; m=runpy.run_path(sys.argv[1]); assert m["theme_palette"]()==m["DEFAULT_PALETTE"]'
        result = subprocess.run([sys.executable, '-c', script, str(Path(artwork.__file__).resolve())],
                                env=dict(os.environ, HOME=str(self.home)), capture_output=True, text=True, timeout=2)
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_regular_theme_symlink_is_supported(self):
        target = self.home / 'installed-theme.toml'
        target.write_text('accent = "#123456"')
        self.path.symlink_to(target)
        self.assertEqual(artwork.theme_palette()['accent'], '#123456')

    def test_invalid_colors_fall_back_individually(self):
        for invalid in ('red', '#123', '#1234567', '#123456789', '#GG0000', '<svg>', 'url(file:///tmp/a)', '#112233\n', 123, None, {}):
            with self.subTest(value=invalid), patch.object(artwork.tomllib, 'loads', return_value={'accent': invalid, 'foreground': '#fedcba'}):
                self.path.write_text('')
                self.assertEqual(artwork.theme_palette(), dict(artwork.DEFAULT_PALETTE, foreground='#fedcba'))
        colors = artwork.theme_palette()
        colors['accent'] = 'mutated'
        self.assertEqual(artwork.DEFAULT_PALETTE['accent'], '#86efac')


if __name__ == '__main__':
    unittest.main()
