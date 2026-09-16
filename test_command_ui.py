"""Render full Desktop content with native UI and inert transport, offscreen.

Only window wrappers are adapted from Wayland PanelWindow to FloatingWindow.
The public chat, navigation, proposal handlers, and command browser are intact.
Set WISP_UI_CAPTURE_DIR to retain PNGs for review; no actions or user state run.
"""
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).parent
SHELL = Path('/usr/share/omarchy/shell')


class CommandUiTests(unittest.TestCase):
    @unittest.skipUnless(shutil.which('quickshell') and (SHELL / 'Ui').is_dir(), 'requires native Omarchy UI')
    def test_full_chat_and_commands_layout_and_proposals(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp)
            for name in ('Ui', 'Commons'):
                (folder / name).symlink_to(SHELL / name)
            for source in (ROOT / 'plugin').iterdir():
                if source.suffix in ('.qml', '.js'):
                    shutil.copy2(source, folder / source.name)
            for source in folder.glob('*.qml'):
                text = source.read_text().replace('PanelWindow {', 'FloatingWindow {')
                text = re.sub(r'^.*WlrLayershell.*\n', '', text, flags=re.M)
                text = re.sub(r'^\s*anchors\s*\{[^}]*:\s*true[^}]*\}\s*$', '', text, flags=re.M)
                text = re.sub(r'^\s*margins(?:\s*\{[^}]*\}|\.[^\n]*).*$', '', text, flags=re.M)
                text = re.sub(r';?exclusionMode\s*:\s*ExclusionMode.Ignore', '', text)
                source.write_text(text)
            (folder / 'Call.qml').write_text('import QtQuick\nItem {property bool busy:false;signal received(var data);function run(args){} function cancel(){}}')
            capture = Path(os.environ.get('WISP_UI_CAPTURE_DIR', tmp))
            capture.mkdir(parents=True, exist_ok=True)
            import json
            desktop = folder / 'Desktop.qml'
            probe = '''
    function findButton(item, label) {
        if(item.text === label && typeof item.clicked === "function") return item;
        var children = item.children || [];
        for(var i=0;i<children.length;i++) {var found=findButton(children[i],label);if(found)return found;}
        return null;
    }
    function checkBounds(item) {
        var children=item.children||[];
        for(var i=0;i<children.length;i++) {
            var child=children[i];
            if(!child.visible)continue;
            if(typeof child.clicked === "function" && (child.x < -1 || child.x+child.width > item.width+1)) {
                console.log("BUTTON_OVERFLOW",child.text,child.x,child.width,item.width);Qt.exit(3);
            }
            checkBounds(child);
        }
    }
    function snapshotTest() {
        if(win.width!==360 || chatContent.width!==328)Qt.exit(2);
        checkBounds(chatContent);
        chatSurface.grabToImage(function(r) {
            r.saveToFile(CHAT_PATH);
            var cancel=findButton(chatContent,"Cancel");if(!cancel)Qt.exit(4);
            cancel.clicked();
            if(root.pending || root.reply!=="Cancelled. Nothing was run.")Qt.exit(5);
            root.showPanel("tools");testCapture.start();
        });
    }
    Timer {id:testCapture;interval:300;onTriggered:{
        checkBounds(senses.contentItem);
        senses.contentItem.children[0].grabToImage(function(r){
            r.saveToFile(COMMANDS_PATH);
            senses.propose("theme_menu","Choose a theme");
            if(!root.opened || root.pending!=="theme_menu" || root.pendingLabel!=="Choose a theme" || root.responseSource!=="local")Qt.exit(6);
            console.log("COMMAND_UI_OK");Qt.quit();
        });
    }}
'''.replace('CHAT_PATH', json.dumps(str(capture / 'wisp-chat.png'))).replace('COMMANDS_PATH', json.dumps(str(capture / 'wisp-commands.png')))
            desktop.write_text(desktop.read_text().replace('    id: root', '    id: root\n' + probe, 1))
            (folder / 'shell.qml').write_text('''
import QtQuick
import Quickshell
Scope {
    Desktop {
        id: desktop; stateReady: true; opened: true; movement: "stay"
        pending: "theme_menu"; pendingLabel: "Choose a theme for your desktop"; responseSource: "local"
        reply: "Ready: Choose a theme for your desktop. Tap Run below."
        tools: [{id:"theme_menu",label:"Choose a theme",group:"Appearance",description:"Browse installed desktop themes.",examples:["change my theme"],available:true,requires:"omarchy"}]
    }
    Timer {interval:700;running:true;onTriggered:desktop.snapshotTest()}
    Timer {interval:5000;running:true;onTriggered:Qt.exit(8)}
}
''')
            env = dict(os.environ, QT_QPA_PLATFORM='offscreen', QT_QPA_PLATFORMTHEME='', XDG_CACHE_HOME=tmp, XDG_RUNTIME_DIR=tmp)
            result = subprocess.run(['quickshell', '--no-color', '-p', str(folder / 'shell.qml')], capture_output=True, text=True, env=env, timeout=10)
            output = result.stdout + result.stderr
            self.assertEqual(result.returncode, 0, output)
            self.assertIn('COMMAND_UI_OK', output)
            for failure in ('TypeError', 'ReferenceError', 'Binding loop', 'BUTTON_OVERFLOW'):
                self.assertNotIn(failure, output)
            self.assertTrue((capture / 'wisp-chat.png').is_file())
            self.assertTrue((capture / 'wisp-commands.png').is_file())


if __name__ == '__main__': unittest.main()
