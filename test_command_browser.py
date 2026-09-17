"""Exercise the real native command browser offscreen, without desktop actions."""
import os
import json
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
                source = Path(os.environ.get('WISP_UI_PLUGIN_DIR', str(ROOT / 'plugin'))) / name
                shutil.copy2(source if source.is_file() else ROOT / 'plugin' / name, folder / name)
            capture = Path(os.environ.get('WISP_UI_CAPTURE_DIR', tmp))
            capture.mkdir(parents=True, exist_ok=True)
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
                {id:"theme",label:"Choose a theme",available:true,requires:"omarchy",group:"Appearance",description:"Browse installed themes.",examples:["change my theme"],sourceLabel:"Omarchy",verification:"accepted",planSafe:true},
                {id:"volume",label:"Raise volume",available:true,requires:"wpctl",group:"Sound",description:"Increase speaker volume.",examples:["turn it up"],sourceLabel:"Sound controls",verification:"state",planSafe:true},
                {id:"missing",label:"Open music",available:false,requires:"music-app",group:"Apps",description:"Open your player.",examples:["open music"],sourceLabel:"Music player",availabilityReason:"Your music player is not installed.",verification:"process",planSafe:false}
            ]
            onPropose: function(action,label) { proposals++; if(action!=="theme") Qt.exit(9); }
        }
    }
    Timer {
        interval: 500; running: true
        onTriggered: {
            if(browser.filtered.length!==3) Qt.exit(1);
            if(browser.unavailableReason(browser.tools[2])!=="Your music player is not installed.")Qt.exit(10);
            if(browser.unavailableReason({requires:"player"})!=="Needs player")Qt.exit(11);
            if(browser.controlDetails({})!=="")Qt.exit(12);
            if(browser.controlDetails(browser.tools[0]).indexOf("Confirms the request was accepted.")<0)Qt.exit(13);
            if(browser.controlDetails(browser.tools[1]).indexOf("Checks that the change took effect.")<0)Qt.exit(14);
            if(browser.controlDetails(browser.tools[2]).indexOf("Reports whether the command finished.")<0 || browser.controlDetails(browser.tools[2]).indexOf("Use this command on its own.")<0)Qt.exit(15);
            browser.query="Sound controls";
            if(browser.filtered.length!==1 || browser.filtered[0].id!=="volume")Qt.exit(16);
            browser.query="not installed";
            if(browser.filtered.length!==1 || browser.filtered[0].available)Qt.exit(17);
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
            browser.resetFilters();browser.busy=false;
            captureTimer.start();
        }
    }
    Timer {id:captureTimer;interval:100;onTriggered:browser.grabToImage(function(r){r.saveToFile(CAPTURE_PATH);console.log("COMMAND_BROWSER_OK");Qt.quit();})}
    Timer { interval: 5000; running: true; onTriggered: Qt.exit(8) }
}
'''.replace('CAPTURE_PATH', json.dumps(str(capture / 'wisp-command-metadata.png'))))
            env = dict(os.environ, QT_QPA_PLATFORM='offscreen', QT_QPA_PLATFORMTHEME='', XDG_CACHE_HOME=tmp, XDG_RUNTIME_DIR=tmp)
            result = subprocess.run(['quickshell', '--no-color', '-p', str(folder / 'shell.qml')], capture_output=True, text=True, env=env, timeout=10)
            output = result.stdout + result.stderr
            self.assertEqual(result.returncode, 0, output)
            self.assertIn('COMMAND_BROWSER_OK', output)
            self.assertNotIn('TypeError', output)
            self.assertNotIn('ReferenceError', output)
            self.assertNotIn('Binding loop', output)


if __name__ == '__main__': unittest.main()
