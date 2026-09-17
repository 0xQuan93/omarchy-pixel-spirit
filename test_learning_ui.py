"""Native resource and saved-reply controls with inert calls and URL opening."""
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import unittest
from unittest.mock import patch

from plugin import omarchy_help

ROOT = Path(__file__).parent
SHELL = Path('/usr/share/omarchy/shell')


class LearningUiTests(unittest.TestCase):
    @unittest.skipUnless(shutil.which('quickshell') and (SHELL / 'Ui').is_dir(), 'requires native Omarchy UI')
    def test_reviewed_resources_and_saved_phrase_lifecycle(self):
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
                source.write_text(re.sub(r';?exclusionMode\s*:\s*ExclusionMode.Ignore', '', text))
            (folder / 'Call.qml').write_text('import QtQuick\nItem {property bool busy:false;property var requests:[];signal received(var data);function run(args){requests=requests.concat([args]);} function cancel(){busy=false;}}')
            capture = Path(os.environ['WISP_UI_CAPTURE_DIR']) if os.environ.get('WISP_UI_CAPTURE_DIR') else None
            if capture:
                capture.mkdir(parents=True, exist_ok=True)
            system, config = folder / 'fixture-omarchy', folder / 'fixture-config'
            for relative in ('shell/README.md', 'default/hypr/bindings/utilities.lua'):
                reference = system / relative
                reference.parent.mkdir(parents=True, exist_ok=True)
                reference.write_text('Native UI fixture; never opened.\n')
            with patch.object(omarchy_help, '_roots', return_value=(system, config)):
                help_reply = omarchy_help.reply('Tell me about Omarchy')
            probe = r'''
    property string captureDirectory:CAPTURE_DIRECTORY
    property var helpExample:HELP_EXAMPLE
    property string testKey:"b".repeat(64)
    property var openedUrls:[]
    property var testResources:[
        {label:"Read the manual",url:"https://omarchy.org/manual/",kind:"official"},
        {label:"Installed guide",url:"file:///usr/share/omarchy/shell/README.md",kind:"local"},
        {label:"Wrong host",url:"https://omarchy.org.evil.example/manual/",kind:"official"},
        {label:"Code",url:"javascript:alert(1)",kind:"official"},
        {label:"Wrong file type",url:"file:///usr/share/omarchy/run.desktop",kind:"local"},
        {label:"Traversal",url:"file:///usr/share/omarchy/../shell/README.md",kind:"local"}
    ]
    function testAssert(condition,code){if(!condition){console.error("Check failed",code);Qt.exit(code);throw new Error("Check "+code)}}
    function testButton(item,label){
        if(item.text===label && typeof item.clicked==="function")return item;
        var children=item.children||[];
        for(var i=0;i<children.length;i++){var found=testButton(children[i],label);if(found)return found;}return null;
    }
    function testLearned(route,kind){return {text:"A saved reply",route:route,learnedKey:testKey,learnedKind:kind,savedAt:1720000000}}
    function testStart(){
        brain.received({text:"About Omarchy",route:"local",helpTopic:"overview",resources:testResources});
        testAssert(!(root.chatResources.length!==2 || root.learnedKey || openedUrls.length),1);
        testAssert(!(!root.reviewedResource({label:"Spaces",url:"file:///home/test%20user/.local/share/omarchy/shell/README.md",kind:"local"})),2);
        testAssert(root.replyText({text:"About\n\n"+testResources[0].label+": "+testResources[0].url,route:"local",helpTopic:"overview",resources:[testResources[0]]})==="About",20);
        resourceCheck.start();
    }
    Timer {id:resourceCheck;interval:80;onTriggered:{
        var manual=testButton(chatContent,"Read the manual · Official manual");
        var local=testButton(chatContent,"Installed guide · On this computer");
        testAssert(!(!manual || !local || manual.focusPolicy!==Qt.TabFocus || !manual.enabled || resourceList.parent.height>104),3);
        manual.clicked();testAssert(!(openedUrls.length!==1 || openedUrls[0]!==testResources[0].url),4);
        root.openChatResource(testResources[3]);testAssert(!(openedUrls.length!==1),5);
        brain.busy=true;root.openChatResource(root.chatResources[0]);brain.busy=false;testAssert(!(openedUrls.length!==1),6);
        brain.received({text:"Model supplied",route:"model",helpTopic:"overview",resources:testResources});testAssert(!(root.chatResources.length),7);
        brain.received({text:"Ordinary local reply",route:"local",resources:testResources});testAssert(!(root.chatResources.length),8);
        brain.received(testLearned("model","answer"));savedCheck.start();
    }}
    Timer {id:savedCheck;interval:60;onTriggered:{
        var refresh=testButton(chatContent,"Ask again"),forget=testButton(chatContent,"Forget phrase");
        testAssert(!(!refresh || !forget || !refresh.focusable || !forget.focusable || !refresh.enabled || root.learnedKey!==testKey || root.learnedKind!=="answer" || root.learnedSavedAt!==1720000000),9);
        root.pending="plan:"+"a".repeat(32);root.planSteps=[{action:"browser",label:"Browser"}];root.activePlanToken=root.pending;root.planFinished=true;
        root.commandChoices=[{action:"browser",label:"Browser"}];root.chatResources=[testResources[0]];
        brain.busy=true;root.learningRequest("refresh");brain.busy=false;testAssert(!(brain.requests.length),10);
        refresh.clicked();
        testAssert(!(brain.requests.length!==1 || JSON.stringify(brain.requests[0])!==JSON.stringify(["learning","refresh",testKey,root.eco?"eco":""])),11);
        testAssert(!(root.pending || root.pendingLabel || root.commandChoices.length || root.displayedPlanSteps.length || root.activePlanToken || root.learnedKey || root.chatResources.length || idlePlanCancelCall.requests.length!==1 || actor.requests.length),12);
        brain.received(testLearned("learned","action"));
        testAssert(!(root.responseSource!=="learned" || root.learnedKind!=="action"),13);
        forget.clicked();
        testAssert(!(brain.requests.length!==2 || JSON.stringify(brain.requests[1])!==JSON.stringify(["learning","forget",testKey]) || root.learnedKey || actor.requests.length),14);
        brain.received(Object.assign(testLearned("local","unresolved"),{error:"Could not answer this request."}));
        testAssert(!(root.learnedKind!=="unresolved" || !root.learnedKey),15);
        brain.received({text:root.reply,route:"local"});testAssert(!(root.learnedKey || root.chatResources.length),16);
        brain.received(Object.assign(testLearned("learned","answer"),{learnedKey:"bad"}));testAssert(!(root.learnedKey),17);
        brain.received(testLearned("learned","answer"));root.prepareCommandChoice({action:"browser",label:"Browser"});
        testAssert(!(root.learnedKey || root.chatResources.length || root.pending!=="browser"),18);
        root.pending="";root.pendingLabel="";
        brain.received({text:"Which player?",route:"local",choices:[{action:"browser",label:"Browser"},{action:"volume_down",label:"Volume"}]});
        root.voiceReply("Listening now…");listener.received({text:"Second one.",transcript:"Second one."});root.send();
        testAssert(!(root.pending!=="volume_down" || brain.requests.length!==2 || actor.requests.length),19);
        if(captureDirectory){root.pending="";root.pendingLabel="";brain.received(helpExample);captureHelp.start()}
        else {console.log("LEARNING_UI_OK");Qt.quit()}
    }}
    Timer {id:captureHelp;interval:200;onTriggered:chatSurface.grabToImage(function(result){
        testAssert(result.saveToFile(captureDirectory+"/wisp-omarchy-help.png"),21);
        brain.received(Object.assign(testLearned("learned","answer"),{text:"Saved local AI reply · Sep 16, 2026 at 20:30\nA tiling window manager arranges your windows automatically, making it easier to keep a few apps visible. You can still move between them using keyboard shortcuts."}));
        captureSaved.start();
    })}
    Timer {id:captureSaved;interval:200;onTriggered:chatSurface.grabToImage(function(result){
        testAssert(result.saveToFile(captureDirectory+"/wisp-saved-reply.png"),22);
        console.log("LEARNING_UI_OK");Qt.quit();
    })}
'''.replace('CAPTURE_DIRECTORY', json.dumps(str(capture) if capture else '')).replace('HELP_EXAMPLE', json.dumps(help_reply))
            desktop = folder / 'Desktop.qml'
            text = desktop.read_text().replace('Qt.openUrlExternally(resource.url)', 'root.openedUrls=root.openedUrls.concat([resource.url])')
            desktop.write_text(text.replace('    id: root', '    id: root\n' + probe, 1))
            (folder / 'shell.qml').write_text('''
import QtQuick
import Quickshell
Scope {
    Desktop {id:desktop;stateReady:true;opened:true;movement:"stay"}
    Timer {interval:300;running:true;onTriggered:desktop.testStart()}
    Timer {interval:5000;running:true;onTriggered:Qt.exit(99)}
}
''')
            env = dict(os.environ, QT_QPA_PLATFORM='offscreen', QT_QPA_PLATFORMTHEME='', XDG_CACHE_HOME=tmp, XDG_RUNTIME_DIR=tmp)
            result = subprocess.run(['quickshell', '--no-color', '-p', str(folder / 'shell.qml')], capture_output=True, text=True, env=env, timeout=8)
            output = result.stdout + result.stderr
            self.assertEqual(result.returncode, 0, output)
            self.assertIn('LEARNING_UI_OK', output)
            if capture:
                for name in ('wisp-omarchy-help.png', 'wisp-saved-reply.png'):
                    self.assertGreater((capture / name).stat().st_size, 0)
            for failure in ('TypeError', 'ReferenceError', 'Binding loop'):
                self.assertNotIn(failure, output)


if __name__ == '__main__': unittest.main()
