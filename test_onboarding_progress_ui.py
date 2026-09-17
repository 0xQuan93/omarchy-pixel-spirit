"""Native onboarding and plan lifecycle tests, using inert backend transports.

The offscreen floating wrapper starts at the real chat width because its
platform cannot resize an existing window when the implicit width changes.
"""
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).parent
SHELL = Path('/usr/share/omarchy/shell')


class OnboardingProgressUiTests(unittest.TestCase):
    @unittest.skipUnless(shutil.which('quickshell') and (SHELL / 'Ui').is_dir(), 'requires native Omarchy UI')
    def test_consent_progress_stop_and_interrupted_recovery(self):
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
            (folder / 'Call.qml').write_text('import QtQuick\nItem {property bool busy:false;property var requests:[];signal received(var data);function run(args){requests=requests.concat([args]);} function cancel(){busy=false;}}')
            capture = Path(os.environ.get('WISP_UI_CAPTURE_DIR', tmp))
            capture.mkdir(parents=True, exist_ok=True)
            probe = '''
    property string testToken:"plan:"+"a".repeat(32)
    property int finalReadCount:0
    property int settledPollCount:0
    function testRestore(onboarding,progress){return {profile:root.profile,room:root.roomData,growth:root.growth,awareness:root.awareness,position:{x:24,y:70,hidden:false,voice:false,movement:"stay"},recovered:[],reply:"Welcome back.",onboarding:onboarding,planStatus:progress}}
    function testButton(item,label){
        if(item.text===label && typeof item.clicked==="function")return item;
        var children=item.children||[];
        for(var i=0;i<children.length;i++){var button=testButton(children[i],label);if(button)return button;}return null;
    }
    function testStart(){
        brain.received({text:"Which player?",choices:[{action:"browser",label:"Browser"},{action:"volume_down",label:"Volume"}],route:"local"});
        testButton(chatContent,"Mic").clicked();
        if(root.commandChoices.length!==2)Qt.exit(27);
        root.voiceReply("Transcribing your recording locally…");
        listener.received({text:"Second one.",transcript:"Second one."});root.send();
        if(brain.requests.length || actor.requests.length || root.pending!=="volume_down")Qt.exit(28);
        root.pending="";root.pendingLabel="";listener.requests=[];

        if(root.actionReceiptMood({status:"failed",emote:"happy"},false)!=="idle" || root.actionReceiptMood({status:"cancelled"},true)!=="idle")Qt.exit(20);
        if(root.actionReceiptMood({status:"accepted"},false)!=="working" || root.actionReceiptMood({status:"completed"},false)!=="working" || root.actionReceiptMood({status:"verified"},false)!=="happy")Qt.exit(21);
        if(root.actionReceiptMood({status:"completed",receipts:[{status:"verified"},{status:"accepted"}]},true)!=="working" || root.actionReceiptMood({status:"completed",receipts:[]},true)!=="working" || root.actionReceiptMood({status:"completed",receipts:[{status:"verified"}]},true)!=="happy")Qt.exit(22);
        if(root.stepStatusText("completed")!=="Finished")Qt.exit(23);
        loader.received(testRestore({showSetup:true,completed:false,availableCount:42,unavailableCount:3,sources:[{name:"Desktop",count:40},{name:"Installed themes",count:5}],text:"Make yourself at home."},null));
        if(!root.setupOpen || root.setupData.availableCount!==42 || setupCall.requests.length || root.awareness.settings.enabled || brain.requests.length || actor.requests.length)Qt.exit(1);
        captureSetup.start();
    }
    Timer {id:captureSetup;interval:100;onTriggered:introduction.contentItem.children[0].grabToImage(function(r){r.saveToFile(SETUP_IMAGE);afterSetup.start();})}
    Timer {id:afterSetup;interval:50;onTriggered:{
        var finish=testButton(introduction.contentItem,"Finish setup");
        if(!finish || !finish.focusable)Qt.exit(24);
        finish.forceActiveFocus();
        finish.Keys.returnPressed({accepted:false});
        if(setupCall.requests.length!==1 || setupCall.requests[0][0]!=="setup" || setupCall.requests[0][1]!=="finish")Qt.exit(2);
        root.showPanel("tools");
        setupCall.received({showSetup:false,completed:true,availableCount:42,unavailableCount:3,sources:[]});
        if(!root.awarenessOpen)Qt.exit(29);
        if(root.setupOpen || root.awareness.settings.enabled || brain.requests.length || actor.requests.length)Qt.exit(3);
        root.showPanel("setup");
        if(setupCall.requests[1][1]!=="status")Qt.exit(4);
        setupCall.received({showSetup:false,completed:true,availableCount:42,unavailableCount:3,sources:[]});
        introduction.closeRequested();
        var recovery={status:"interrupted",text:"The previous plan stopped.",current:0,total:2,steps:[{label:"Open browser",status:"unknown"},{label:"Lower volume",status:"skipped"}]};
        loader.received(testRestore({showSetup:false,completed:true},recovery));
        if(!root.opened || root.setupOpen || root.pending || root.displayedPlanSteps.length!==2 || actor.requests.length || planStatusCall.requests.length)Qt.exit(5);
        root.clearPlanProgress();
        brain.received({text:"Review two steps.",action:root.testToken,actionLabel:"Run 2 steps",steps:[{action:"browser",label:"Open browser"},{action:"volume_down",label:"Lower volume"}],route:"local"});
        root.handleCommandChoiceReply("cancel");
        if(root.pending || idlePlanCancelCall.requests.length!==1 || idlePlanCancelCall.requests[0][1]!==root.testToken || actor.requests.length)Qt.exit(25);
        root.reply="A newer reply";idlePlanCancelCall.received({text:"Cancelled old plan"});
        if(root.reply!=="A newer reply")Qt.exit(26);
        brain.received({text:"Review two steps.",action:root.testToken,actionLabel:"Run 2 steps",steps:[{action:"browser",label:"Open browser"},{action:"volume_down",label:"Lower volume"}],route:"local"});
        // Genuine plan edits receive the pending token before local UI clears it.
        field.text="remove the second step";root.send();
        if(brain.requests.length!==1 || brain.requests[0].length!==4 || brain.requests[0][3]!==root.testToken || root.pending)Qt.exit(6);
        brain.received({text:"Review two steps.",action:root.testToken,actionLabel:"Run 2 steps",steps:[{action:"browser",label:"Open browser"},{action:"volume_down",label:"Lower volume"}],route:"local"});
        root.runPendingCommand();actor.busy=true;testRunning.start();
    }}
    Timer {id:testRunning;interval:600;onTriggered:{
        if(win.width!==360 || chatContent.width!==328)Qt.exit(18);
        if(actor.requests.length!==1 || !planStatusCall.requests.length || planStatusCall.requests[0][0]!=="plan_status" || planStatusCall.requests[0][1]!==root.testToken)Qt.exit(7);
        planStatusCall.received({status:"running",current:1,total:2,steps:[{label:"Open browser",status:"accepted"},{label:"Lower volume",status:"running"}],text:"Lowering volume"});
        if(root.displayedPlanSteps[0].status!=="accepted" || root.displayedPlanSteps[1].status!=="running")Qt.exit(8);
        captureProgress.start();
    }}
    Timer {id:captureProgress;interval:100;onTriggered:chatSurface.grabToImage(function(r){r.saveToFile(PROGRESS_IMAGE);testStop.start();})}
    Timer {id:testStop;interval:50;onTriggered:{
        var stop=testButton(chatContent,"Stop after this step");if(!stop || !stop.enabled)Qt.exit(9);stop.clicked();
        if(planCancelCall.requests.length!==1 || planCancelCall.requests[0][0]!=="plan_cancel" || planCancelCall.requests[0][1]!==root.testToken || actor.requests.length!==1)Qt.exit(10);
        planCancelCall.received({text:"Will stop after this step."});if(!root.planStopRequested)Qt.exit(11);
        planStatusCall.busy=true;root.finalReadCount=planStatusCall.requests.length;
        actor.received({ok:false,status:"cancelled",text:"Stopped before the next step.",action:"",route:"local"});actor.busy=false;
        if(!root.planFinalReadNeeded || root.pending || root.mood!=="idle")Qt.exit(12);
        planStatusCall.received({status:"running",steps:[{label:"Old snapshot",status:"running"}]});
        if(root.planProgress.status==="running")Qt.exit(13);
        planStatusCall.busy=false;testFinal.start();
    }}
    Timer {id:testFinal;interval:100;onTriggered:{
        if(planStatusCall.requests.length!==root.finalReadCount+1)Qt.exit(14);
        planStatusCall.received({status:"cancelled",current:1,total:2,steps:[{label:"Open browser",status:"accepted"},{label:"Lower volume",status:"skipped"}],text:"Stopped."});
        if(root.planProgress.status!=="cancelled" || root.displayedPlanSteps[0].status!=="accepted" || root.displayedPlanSteps[1].status!=="skipped")Qt.exit(15);
        root.settledPollCount=planStatusCall.requests.length;testNoIdlePoll.start();
    }}
    Timer {id:testNoIdlePoll;interval:650;onTriggered:{
        if(planStatusCall.requests.length!==root.settledPollCount || actor.requests.length!==1)Qt.exit(16);
        var oldProgress=root.planProgress;
        senses.propose("browser","Open browser");
        if(root.pending!=="browser" || root.activePlanToken || root.planFinished || root.displayedPlanSteps.length)Qt.exit(30);
        root.planProgress=oldProgress;root.activePlanToken=root.testToken;root.planFinished=true;
        root.asideAction="theme_picker";root.asideActionLabel="Choose a theme";root.reviewBubbleAction();
        if(root.pending!=="theme_picker" || root.activePlanToken || root.planFinished || root.displayedPlanSteps.length)Qt.exit(31);
        actor.busy=true;senses.propose("browser","Open browser");
        if(root.pending!=="theme_picker")Qt.exit(32);actor.busy=false;
        root.clearPlanProgress();
        planStatusCall.received({status:"completed",steps:[{label:"Stale result",status:"completed"}]});
        if(root.displayedPlanSteps.length)Qt.exit(17);
        root.activePlanToken=root.testToken;root.pending=root.testToken;
        root.planSteps=[{action:"browser",label:"Open browser"}];
        actor.received({error:"A required control is unavailable. Nothing ran; prepare a new plan."});
        if(root.pending || root.pendingLabel || root.mood!=="idle" || !root.planFinished)Qt.exit(33);
        console.log("ONBOARDING_PROGRESS_OK");Qt.quit();
    }}
'''.replace('SETUP_IMAGE', json.dumps(str(capture / 'wisp-onboarding.png'))).replace('PROGRESS_IMAGE', json.dumps(str(capture / 'wisp-plan-progress.png')))
            desktop = folder / 'Desktop.qml'
            desktop.write_text(desktop.read_text().replace('    id: root', '    id: root\n' + probe, 1))
            (folder / 'shell.qml').write_text('''
import QtQuick
import Quickshell
Scope {
    Desktop {id:desktop;stateReady:true;opened:true;movement:"stay"}
    Timer {interval:300;running:true;onTriggered:desktop.testStart()}
    Timer {interval:7000;running:true;onTriggered:Qt.exit(99)}
}
''')
            env = dict(os.environ, QT_QPA_PLATFORM='offscreen', QT_QPA_PLATFORMTHEME='', XDG_CACHE_HOME=tmp, XDG_RUNTIME_DIR=tmp)
            result = subprocess.run(['quickshell', '--no-color', '-p', str(folder / 'shell.qml')], capture_output=True, text=True, env=env, timeout=10)
            output = result.stdout + result.stderr
            self.assertEqual(result.returncode, 0, output)
            self.assertIn('ONBOARDING_PROGRESS_OK', output)
            for failure in ('TypeError', 'ReferenceError', 'Binding loop'):
                self.assertNotIn(failure, output)


if __name__ == '__main__': unittest.main()
