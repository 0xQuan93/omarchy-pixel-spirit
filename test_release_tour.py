import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).parent / 'plugin'))
import release_tour


class ReleaseTourTests(unittest.TestCase):
    def test_version_matches_manifest(self):
        manifest = json.loads((Path(__file__).parent / 'manifest.json').read_text())
        self.assertEqual(release_tour.VERSION, manifest['version'])

    def test_existing_user_sees_tour_until_explicitly_marked(self):
        with tempfile.TemporaryDirectory() as directory:
            self.assertFalse(release_tour.status(directory, existing=False)['unseen'])
            self.assertTrue(release_tour.status(directory)['unseen'])
            self.assertFalse(release_tour.mark_seen(directory)['unseen'])
            self.assertFalse(release_tour.status(directory)['unseen'])

    def test_damaged_preference_is_preserved_without_forcing_tour(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'release-tour.json'
            path.write_text('{"version":1,"seen":42}')
            result = release_tour.status(directory)
            self.assertFalse(result['unseen'])
            self.assertIn('damaged', result['error'])
            self.assertEqual(path.read_text(), '{"version":1,"seen":42}')


if __name__ == '__main__':
    unittest.main()
