"""Native offscreen bubble layout and action regression; no desktop actions."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).parent
SHELL = Path('/usr/share/omarchy/shell')


class SpeechBubbleTests(unittest.TestCase):
    @unittest.skipUnless(shutil.which('quickshell') and (SHELL / 'Ui').is_dir(), 'requires native Omarchy UI')
    def test_long_unicode_source_and_explicit_actions(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp)
            for name in ('Ui', 'Commons'):
                (folder / name).symlink_to(SHELL / name)
            for name in ('SpeechBubble.qml', 'Action.qml'):
                shutil.copy2(ROOT / 'plugin' / name, folder / name)
            capture = Path(os.environ.get('WISP_UI_CAPTURE_DIR', tmp))
            capture.mkdir(parents=True, exist_ok=True)
            (folder / 'shell.qml').write_text('''
import QtQuick
import Quickshell
Scope {
    id: test
    property int actions: 0
    property int dismissals: 0
    function button(item,label) {
        if(item.text===label && typeof item.clicked==="function")return item;
        var children=item.children||[];
        for(var i=0;i<children.length;i++){var found=button(children[i],label);if(found)return found;}
        return null;
    }
    FloatingWindow {
        visible:true;implicitWidth:324;implicitHeight:bubble.implicitHeight+30;color:"#141818"
        SpeechBubble {
            id:bubble;x:10;y:15;width:304;height:implicitHeight
            name:"Wisp";sourceLabel:"Desktop help · On this machine"
            text:"Try ‘change my theme’ or ‘show keyboard shortcuts’. I can prepare those right here, without a model call. 🌿"
            actionLabel:"Explore commands"
            onActionRequested:test.actions++
            onDismissed:test.dismissals++
        }
    }
    Timer {
        interval:350;running:true
        onTriggered:{
            if(bubble.activeFocus)Qt.exit(1);
            if(bubble.width!==304 || bubble.implicitHeight>400)Qt.exit(2);
            button(bubble,"Explore commands").clicked();
            if(test.actions!==1 || test.dismissals!==0)Qt.exit(3);
            bubble.grabToImage(function(r){r.saveToFile(CAPTURE);longTest.start();});
        }
    }
    Timer {
        id:longTest;interval:100
        onTriggered:{
            bubble.text="A longer thought about your desktop — 雲 and 🌿. ".repeat(100);
            bubble.sourceLabel="A longer source label with Unicode · 源 and native theme details that should wrap without pushing the message out of the card";
            bubble.actionLabel="Open the command browser and explore installed themes";
            expandedTest.start();
        }
    }
    Timer {
        id:expandedTest;interval:100
        onTriggered:{
            var more=button(bubble,"Read more");if(!more || !more.visible)Qt.exit(4);
            if(bubble.implicitHeight>440)Qt.exit(5);
            more.clicked();
            if(!bubble.expanded)Qt.exit(6);
            finish.start();
        }
    }
    Timer {
        id:finish;interval:100
        onTriggered:{
            if(bubble.implicitHeight>500)Qt.exit(7);
            button(bubble,"Dismiss").clicked();
            if(test.dismissals!==1 || test.actions!==1)Qt.exit(8);
            bubble.text="New message";
            if(bubble.expanded)Qt.exit(9);
            console.log("SPEECH_BUBBLE_OK");Qt.quit();
        }
    }
    Timer {interval:5000;running:true;onTriggered:Qt.exit(10)}
}
'''.replace('CAPTURE', json.dumps(str(capture / 'wisp-speech-bubble.png'))))
            env = dict(os.environ, QT_QPA_PLATFORM='offscreen', QT_QPA_PLATFORMTHEME='', XDG_CACHE_HOME=tmp, XDG_RUNTIME_DIR=tmp)
            result = subprocess.run(['quickshell', '--no-color', '-p', str(folder / 'shell.qml')], capture_output=True, text=True, env=env, timeout=10)
            output = result.stdout + result.stderr
            self.assertEqual(result.returncode, 0, output)
            self.assertIn('SPEECH_BUBBLE_OK', output)
            for failure in ('TypeError', 'ReferenceError', 'Binding loop'):
                self.assertNotIn(failure, output)
            self.assertTrue((capture / 'wisp-speech-bubble.png').is_file())


if __name__ == '__main__': unittest.main()
