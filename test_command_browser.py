"""Exercise the real native command browser offscreen, without desktop actions."""
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).parent
SHELL = Path('/usr/share/omarchy/shell')


class CommandBrowserTests(unittest.TestCase):
    @unittest.skipUnless(shutil.which('quickshell') and (SHELL / 'Ui').is_dir(), 'requires native Omarchy UI')
    def test_filter_and_proposal_with_native_components(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp)
            for name in ('Ui', 'Commons'):
                (folder / name).symlink_to(SHELL / name)
            for name in ('CommandBrowser.qml', 'Action.qml'):
                shutil.copy2(ROOT / 'plugin' / name, folder / name)
            (folder / 'shell.qml').write_text('''
import QtQuick
import Quickshell
Scope {
    property int proposals: 0
    FloatingWindow {
        visible: true
        width: 440; height: 490
        CommandBrowser {
            id: browser
            anchors.fill: parent
            tools: [
                {id:"theme",label:"Choose a theme",available:true,requires:"omarchy",group:"Appearance",description:"Browse installed themes.",examples:["change my theme"]},
                {id:"volume",label:"Raise volume",available:true,requires:"wpctl",group:"Sound",description:"Increase speaker volume.",examples:["turn it up"]},
                {id:"missing",label:"Open music",available:false,requires:"music-app",group:"Apps",description:"Open your player.",examples:["open music"]}
            ]
            onPropose: function(action,label) { proposals++; if(action!=="theme") Qt.exit(9); }
        }
    }
    Timer {
        interval: 500; running: true
        onTriggered: {
            if(browser.filtered.length!==3) Qt.exit(1);
            browser.query="turn up";
            if(browser.filtered.length!==1 || browser.filtered[0].id!=="volume") Qt.exit(2);
            browser.query=""; browser.availableOnly=true;
            if(browser.filtered.length!==2) Qt.exit(3);
            browser.category="Appearance";
            if(browser.filtered.length!==1) Qt.exit(4);
            browser.prepare(browser.tools[0]);
            browser.prepare(browser.tools[2]);
            browser.busy=true; browser.prepare(browser.tools[0]);
            if(proposals!==1) Qt.exit(5);
            browser.resetFilters();
            if(browser.filtered.length!==3) Qt.exit(6);
            browser.query="not a real command";
            if(browser.filtered.length!==0) Qt.exit(7);
            console.log("COMMAND_BROWSER_OK"); Qt.quit();
        }
    }
    Timer { interval: 5000; running: true; onTriggered: Qt.exit(8) }
}
''')
            env = dict(os.environ, QT_QPA_PLATFORM='offscreen', QT_QPA_PLATFORMTHEME='', XDG_CACHE_HOME=tmp, XDG_RUNTIME_DIR=tmp)
            result = subprocess.run(['quickshell', '--no-color', '-p', str(folder / 'shell.qml')], capture_output=True, text=True, env=env, timeout=10)
            output = result.stdout + result.stderr
            self.assertEqual(result.returncode, 0, output)
            self.assertIn('COMMAND_BROWSER_OK', output)
            self.assertNotIn('TypeError', output)
            self.assertNotIn('ReferenceError', output)
            self.assertNotIn('Binding loop', output)


if __name__ == '__main__': unittest.main()
