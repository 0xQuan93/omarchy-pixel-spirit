import importlib.util
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location('onboarding', Path(__file__).parent/'plugin/onboarding.py')
onboarding = importlib.util.module_from_spec(spec); spec.loader.exec_module(onboarding)


class OnboardingTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory(); self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        self.base = self.root/'state/wisp'
        self.entries = [
            {'id':'theme_picker','sourceLabel':'Appearance','available':True},
            {'id':'terminal','sourceLabel':'Apps','available':False},
            {'id':'files','sourceLabel':'Apps','available':True},
        ]

    def test_clean_install_without_omarchy_or_model_has_no_effects(self):
        env = {'HOME':str(self.root), 'XDG_STATE_HOME':str(self.root/'state'),
               'XDG_CONFIG_HOME':str(self.root/'config'), 'PATH':''}
        with patch.dict(os.environ, env), patch('subprocess.run', side_effect=AssertionError('No probing')), patch('subprocess.Popen', side_effect=AssertionError('No launch')):
            result = onboarding.status(self.base, [{'id':'browser','available':False}], scan=lambda: self.fail('No scanning'))
        self.assertTrue(result['showSetup']); self.assertTrue(result['modelOptional'])
        self.assertFalse(result['localCommandsUsable']); self.assertEqual(result['unavailableCount'],1)
        self.assertEqual(list(self.root.iterdir()), [])

    def test_counts_are_deduplicated_and_only_use_supplied_catalogue(self):
        entries=self.entries + [self.entries[0], {'id':'unknown','available':'true'}, None]
        result=onboarding.status(self.base, entries, {'plugins':[{},{}], 'themes':['one']})
        self.assertEqual(result['availableCount'],2); self.assertEqual(result['unavailableCount'],2)
        self.assertEqual(result['sources'], [{'name':'Appearance','count':1},{'name':'Apps','count':2},{'name':'Local controls','count':1}])
        self.assertEqual(result['pluginCount'],2); self.assertEqual(result['themeCount'],1)
        self.assertTrue(result['localCommandsUsable'])

    def test_existing_identity_or_backup_never_auto_opens_setup(self):
        self.base.mkdir(parents=True)
        for name in ('identity.json','identity.json.bak'):
            file=self.base/name; file.write_text('not even valid JSON')
            self.assertFalse(onboarding.status(self.base,self.entries)['showSetup'])
            file.unlink()
        (self.base/'identity.json').symlink_to(self.base/'missing')
        self.assertFalse(onboarding.status(self.base,self.entries)['showSetup'])

    def test_only_finish_writes_and_survives_restart(self):
        self.assertFalse(onboarding.status(self.base,self.entries)['completed'])
        result=onboarding.finish(self.base)
        self.assertEqual(result, {'version':2,'completed':True})
        self.assertEqual(json.loads((self.base/'onboarding.json').read_text()),result)
        self.assertEqual({p.name for p in self.base.iterdir()},{'onboarding.json'})
        restored=onboarding.status(self.base,self.entries)
        self.assertTrue(restored['completed']); self.assertFalse(restored['showSetup'])
        self.assertEqual(restored['availableCount'],2)

    def test_malformed_or_special_preferences_are_nonblocking_and_unchanged(self):
        self.base.mkdir(parents=True)
        path=self.base/'onboarding.json'; path.write_text('invalid')
        self.assertFalse(onboarding.status(self.base,[])['completed'])
        self.assertEqual(path.read_text(),'invalid'); path.unlink()
        os.mkfifo(path)
        self.assertFalse(onboarding.status(self.base,[])['completed'])
        self.assertTrue(path.exists())

    def test_failed_completion_does_not_claim_success_or_leave_temporary_files(self):
        with patch.object(onboarding.os,'replace',side_effect=PermissionError('readonly')):
            with self.assertRaises(PermissionError):onboarding.finish(self.base)
        self.assertEqual(list(self.base.iterdir()),[])
        self.assertFalse(onboarding.status(self.base,[])['completed'])

    def test_summary_never_exposes_requirements_or_private_paths(self):
        result=onboarding.status(self.base,[{'id':'tool','available':False,
            'requires':'/private/personal-helper.py','sourceLabel':'/private/provider'}])
        self.assertNotIn('/private',json.dumps(result))
        source=Path(onboarding.__file__).read_text()
        for private in ('/home/oxquan','zephyr-local','quan-workbench','identity import','growth import','inference import'):
            self.assertNotIn(private,source)

    def test_input_work_is_bounded_and_unknown_values_do_not_look_available(self):
        entries=[{'id':str(i),'available':1} for i in range(onboarding.MAX_ENTRIES+10)]
        result=onboarding.status(self.base,entries)
        self.assertEqual(result['availableCount'],0)
        self.assertEqual(result['unavailableCount'],onboarding.MAX_ENTRIES)


if __name__=='__main__':unittest.main()
