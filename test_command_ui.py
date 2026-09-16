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
            sources = [ROOT / 'plugin']
            if os.environ.get('WISP_UI_PLUGIN_DIR'):
                sources.append(Path(os.environ['WISP_UI_PLUGIN_DIR']))
            for source_dir in sources:
                for source in source_dir.iterdir():
                    if source.suffix in ('.qml', '.js'):
                        shutil.copy2(source, folder / source.name)
            for source in folder.glob('*.qml'):
                text = source.read_text().replace('PanelWindow {', 'FloatingWindow {')
                text = re.sub(r'^.*WlrLayershell.*\n', '', text, flags=re.M)
                text = re.sub(r'^\s*anchors\s*\{[^}]*:\s*true[^}]*\}\s*$', '', text, flags=re.M)
                text = re.sub(r'^\s*margins(?:\s*\{[^}]*\}|\.[^\n]*).*$', '', text, flags=re.M)
                text = re.sub(r';?exclusionMode\s*:\s*ExclusionMode.Ignore', '', text)
                source.write_text(text)
            (folder / 'Call.qml').write_text('import QtQuick\nItem {property bool busy:false;property var requests:[];signal received(var data);function run(args){requests=requests.concat([args]);} function cancel(){}}')
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
        // Stored model failures are status metadata, not failed transport.
        var historyStatus=Object.assign({},root.awareness,{settings:Object.assign({},root.awareness.settings,{enabled:false}),error:"Historical model failure",due:true});
        observer.received(historyStatus);
        if(root.awareness.error!=="Historical model failure" || !root.reflectionDue)Qt.exit(24);
        var previousAwareness=root.awareness;
        observer.received({error:"Transport unavailable"});
        if(root.awareness!==previousAwareness || !root.reflectionDue)Qt.exit(25);
        var settingsStatus=Object.assign({},historyStatus,{error:"Previous model attempt failed"});
        awarenessConfig.received(settingsStatus);
        if(root.awareness.error!=="Previous model attempt failed")Qt.exit(26);
        previousAwareness=root.awareness;
        awarenessConfig.received({error:"Transport unavailable"});
        if(root.awareness!==previousAwareness)Qt.exit(27);
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
            testBubble.start();
        });
    }}
    Timer {id:testBubble;interval:100;onTriggered:{
        root.pending="";root.pendingLabel="";
        root.previewBubble();
        if(!root.asideVisible || root.pending || !asideCard.preview || !asideCard.actionLabel)Qt.exit(11);
        if(actor.requests.length || brain.requests.length)Qt.exit(12);
        if(!asideDismiss.running)Qt.exit(13);
        asideCard.hovered(true);
        if(asideDismiss.running)Qt.exit(14);
        asideCard.hovered(false);
        if(!asideDismiss.running)Qt.exit(15);
        checkBounds(asideCard);
        asideCard.dismissed();
        if(root.asideVisible)Qt.exit(16);
        root.previewBubble();
        var proposed=root.asideAction;
        asideCard.actionRequested();
        if(!root.opened || root.pending!==proposed || !root.pendingLabel || root.asideVisible)Qt.exit(17);
        if(actor.requests.length || brain.requests.length)Qt.exit(18);
        root.showPanel("");root.pending="";root.pendingLabel="";
        root.presentBubble({id:"sample-hint",text:"You can change a theme locally. 雲",basis:"Installed command",kind:"command-hint",action:"theme_picker",actionLabel:"Choose a theme"});
        if(!root.asideVisible || root.asideId!=="sample-hint" || root.asideSource!=="Command tip · works locally" || asideCard.actionLabel!=="Review: Choose a theme")Qt.exit(19);
        if(bubbleGate.requests.length!==1 || bubbleGate.requests[0][0]!=="bubble_gate")Qt.exit(20);
        if(actor.requests.length || brain.requests.length || root.pending)Qt.exit(21);
        asideCard.actionRequested();
        if(root.pending!=="theme_picker" || !root.opened || actor.requests.length)Qt.exit(22);
        root.showPanel("");root.pending="";root.pendingLabel="";
        root.presentBubble({text:"A quiet local thought.",kind:"local-script"});
        if(asideCard.actionLabel || root.asideAction || root.asideSource!=="Local routine")Qt.exit(23);
        asideCard.dismissed();
        root.previewBubble();testBubbleCapture.start();
    }}
    Timer {id:testBubbleCapture;interval:100;onTriggered:{
        checkBounds(asideCard);
        asideCard.grabToImage(function(r){r.saveToFile(BUBBLE_PATH);testChoices.start();});
    }}
    Timer {id:testChoices;interval:100;onTriggered:{
        root.showPanel("chat");
        brain.received({text:"Which playback control did you mean?",emote:"idle",route:"local",matchType:"clarify",action:"",choices:[
            {action:"pause_music",label:"Pause music"},
            {action:"cartoons_close",label:"Stop the cartoon player and close its controls"},
            {action:"cartoons_hide",label:"Hide cartoon controls and keep playing"},
            {action:"cartoons_off",label:"Stop cartoon playback"},
            {action:"extra",label:"Fifth choice is omitted"}, {action:22,label:"Malformed"}
        ]});
        if(root.commandChoices.length!==4 || root.pending || actor.requests.length || brain.requests.length)Qt.exit(28);
        testChoose.start();
    }}
    Timer {id:testChoose;interval:100;onTriggered:{
        checkBounds(chatContent);
        chatSurface.grabToImage(function(r){
            r.saveToFile(CHOICES_PATH);
            var choice=findButton(chatContent,"2. Stop the cartoon player and close its controls");if(!choice)Qt.exit(29);
            choice.clicked();
            if(root.pending!=="cartoons_close" || root.pendingLabel!=="Stop the cartoon player and close its controls" || root.commandChoices.length || actor.requests.length || brain.requests.length)Qt.exit(30);
            findButton(chatContent,"Cancel").clicked();
            if(root.pending || root.commandChoices.length)Qt.exit(31);
            var response={text:"Choose a source",route:"local",action:"",choices:[{action:"pause_music",label:"Pause music"}]};
            brain.received(response);root.reply="A newer message";
            if(root.commandChoices.length)Qt.exit(32);
            brain.received(response);root.showPanel("tools");
            if(root.commandChoices.length)Qt.exit(33);
            root.showPanel("chat");brain.received(response);senses.propose("theme_menu","Choose a theme");
            if(root.commandChoices.length)Qt.exit(34);
            var followup={text:"Which source?",route:"local",action:"",choices:[{action:"pause_music",label:"Pause music"},{action:"cartoons_close",label:"Close cartoons"}]};
            var requests=brain.requests.length;
            var ordinalForms=["second one","choose the second option","2","please choose the second option","second one please","CLOSE CARTOONS","Second one.","2!","Please, choose the second option."];
            for(var i=0;i<ordinalForms.length;i++){
                brain.received(followup);field.text=ordinalForms[i];root.send();
                if(root.pending!=="cartoons_close" || root.pendingLabel!=="Close cartoons" || root.commandChoices.length || field.text || brain.requests.length!==requests || actor.requests.length)Qt.exit(37);
            }
            brain.received(followup);field.text="Yes, please.";root.send();
            if(root.pending || root.commandChoices.length!==2 || field.text || brain.requests.length!==requests || actor.requests.length)Qt.exit(38);
            field.text="fourth option";root.send();
            if(root.pending || root.commandChoices.length!==2 || brain.requests.length!==requests)Qt.exit(39);
            for(var j=0;j<["not the second one","second one tomorrow","choose the second option and reboot","second one, then reboot","second one, then close the browser."].length;j++){
                if(root.handleCommandChoiceReply(["not the second one","second one tomorrow","choose the second option and reboot","second one, then reboot","second one, then close the browser."][j]))Qt.exit(40);
            }
            field.text="never mind";root.send();
            if(root.pending || root.commandChoices.length || field.text || root.reply!=="Cancelled. Nothing was run." || brain.requests.length!==requests || actor.requests.length)Qt.exit(41);
            if(root.handleCommandChoiceReply("second one"))Qt.exit(42);
            brain.received(response);field.text="Yes, please.";root.send();
            if(root.pending!=="pause_music" || root.commandChoices.length || brain.requests.length!==requests || actor.requests.length)Qt.exit(44);
            brain.received(followup);testIpc.ask("Second one.");
            var ipcStatus=JSON.parse(testIpc.status());
            if(root.pending!=="cartoons_close" || root.commandChoices.length || brain.requests.length!==requests || actor.requests.length)Qt.exit(45);
            if(ipcStatus.pending!=="cartoons_close" || ipcStatus.pendingLabel!=="Close cartoons" || ipcStatus.responseSource!=="local" || ipcStatus.choiceCount!==0)Qt.exit(46);
            testIpc.ask("Yes, please.");
            if(root.pending!=="cartoons_close" || brain.requests.length!==requests || actor.requests.length)Qt.exit(47);
            testIpc.ask("Never mind.");
            if(root.pending || root.pendingLabel || root.commandChoices.length || brain.requests.length!==requests || actor.requests.length)Qt.exit(48);
            if(root.handleCommandChoiceReply("second one"))Qt.exit(49);
            brain.received(response);testIpc.ask("new request");
            if(root.commandChoices.length || brain.requests.length!==1 || actor.requests.length)Qt.exit(35);
            brain.received({error:"Unavailable",choices:response.choices});
            if(root.commandChoices.length)Qt.exit(36);
            field.text="second one";root.send();
            if(brain.requests.length!==2 || root.pending || actor.requests.length)Qt.exit(43);
            console.log("COMMAND_UI_OK");Qt.quit();
        });
    }}
'''.replace('CHAT_PATH', json.dumps(str(capture / 'wisp-chat.png'))).replace('COMMANDS_PATH', json.dumps(str(capture / 'wisp-commands.png'))).replace('BUBBLE_PATH', json.dumps(str(capture / 'wisp-preview-bubble.png'))).replace('CHOICES_PATH', json.dumps(str(capture / 'wisp-clarification.png')))
            desktop.write_text(desktop.read_text().replace('    id: root', '    id: root\n' + probe, 1).replace('    IpcHandler {', '    IpcHandler {\n        id: testIpc', 1))
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
            self.assertTrue((capture / 'wisp-preview-bubble.png').is_file())


if __name__ == '__main__': unittest.main()
