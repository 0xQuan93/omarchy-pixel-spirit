"""Native offscreen review of saved routines and awareness signal controls.

The transport is inert. Captures are optional via WISP_UI_CAPTURE_DIR.
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


class RoutinesSignalsUiTests(unittest.TestCase):
    @unittest.skipUnless(shutil.which('quickshell') and (SHELL / 'Ui').is_dir(), 'requires native Omarchy UI')
    def test_routine_review_and_signal_controls(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp)
            for name in ('Ui', 'Commons'):
                (folder / name).symlink_to(SHELL / name)
            for plugin_dir in (ROOT / 'plugin', Path(os.environ.get('WISP_UI_PLUGIN_DIR', ROOT / 'plugin'))):
                for source in plugin_dir.iterdir():
                    if source.suffix in ('.qml', '.js'):
                        shutil.copy2(source, folder / source.name)
            for source in folder.glob('*.qml'):
                content = source.read_text().replace('PanelWindow {', 'FloatingWindow {')
                content = re.sub(r'^.*WlrLayershell.*\n', '', content, flags=re.M)
                content = re.sub(r'^\s*anchors\s*\{[^}]*:\s*true[^}]*\}\s*$', '', content, flags=re.M)
                content = re.sub(r'^\s*margins(?:\s*\{[^}]*\}|\.[^\n]*).*$', '', content, flags=re.M)
                source.write_text(re.sub(r';?exclusionMode\s*:\s*ExclusionMode.Ignore', '', content))
            (folder / 'Call.qml').write_text(
                'import QtQuick\nItem {property bool busy:false;property var requests:[];'
                'signal received(var data);function run(args){requests=requests.concat([args]);}'
                'function cancel(){busy=false;}}'
            )
            capture = Path(os.environ.get('WISP_UI_CAPTURE_DIR', tmp))
            capture.mkdir(parents=True, exist_ok=True)
            token = 'plan:' + 'a' * 32
            probe = '''
    property string testToken: TOKEN
    property var testRoutines: [
        {id:"1111111111111111",name:"Morning desk",steps:2,ready:true,reason:""},
        {id:"2222222222222222",name:"Old music controls",steps:2,ready:false,reason:"A control changed. Review and save this routine again."}
    ]
    function fail(code, message){console.log("UI_FAIL",code,message);Qt.exit(code)}
    function buttons(item, label, found){
        if(item.text===label && typeof item.clicked==="function")found.push(item)
        var children=item.children||[]
        for(var i=0;i<children.length;i++)buttons(children[i],label,found)
        return found
    }
    function button(item, label){var found=buttons(item,label,[]);return found.length?found[0]:null}
    function textItem(item, label){
        if(item.text===label && typeof item.clicked!=="function")return item
        var children=item.children||[]
        for(var i=0;i<children.length;i++){var found=textItem(children[i],label);if(found)return found}
        return null
    }
    function scrollView(item){
        if(item.visible && item.contentHeight!==undefined && item.contentY!==undefined && item.contentHeight>item.height)return item
        var children=item.children||[]
        for(var i=0;i<children.length;i++){var found=scrollView(children[i]);if(found)return found}
        return null
    }
    function lastRequest(call){return call.requests[call.requests.length-1]||[]}
    function continueToTour(){
        root.showPanel("tour")
        if(!root.tourOpen || lastRequest(tourCall)[0]!=="tour")fail(23,"tour route")
        tourCall.received({version:"2.2",unseen:true,cards:[
            {title:"Review your routines",text:"Saved plans open for a fresh review.",destination:"routines"},
            {title:"Understand signals",text:"See each source and its retention.",destination:"settings"}
        ]})
        tourCheck.start()
    }
    function testStart(){
        root.showPanel("routines")
        if(!root.routinesOpen || lastRequest(routineCall)[0]!=="routines")fail(2,"routine list route")
        routineCall.received({routines:testRoutines})
        readyCapture.start()
    }
    Timer {id:readyCapture;interval:130;onTriggered:{
        var reviews=buttons(testRoutinePanel.contentItem,"Review",[])
        if(reviews.length!==2 || !reviews[0].enabled || reviews[1].enabled)fail(3,"readiness controls")
        if(!reviews[0].focusable)fail(4,"routine keyboard focus")
        testRoutinePanel.contentItem.children[0].grabToImage(function(result){
            if(!result.saveToFile(ROUTINES_IMAGE))fail(5,"routine capture")
            var secondRemove=buttons(testRoutinePanel.contentItem,"Remove",[])[1]
            secondRemove.forceActiveFocus()
            var routineView=scrollView(testRoutinePanel.contentItem)
            var removePos=secondRemove.mapToItem(routineView,0,0)
            if(!secondRemove.activeFocus || removePos.y<-.5 || removePos.y+secondRemove.height>routineView.height+.5)fail(33,"focused routine remove is offscreen")
            reviews[0].forceActiveFocus()
            if(!reviews[0].activeFocus)fail(6,"focused routine review")
            reviews[0].clicked()
            if(JSON.stringify(lastRequest(routineCall))!==JSON.stringify(["routines","prepare",testRoutines[0].id]))fail(6,"prepare route")
            routineCall.received({action:testToken,routineName:"Morning desk",text:"Review both steps before Run.",steps:[
                {action:"browser",label:"Open browser"},{action:"volume_down",label:"Lower volume"}
            ]})
            if(!root.opened || root.routinesOpen || root.pending!==testToken || root.planSteps.length!==2 || actor.requests.length)fail(7,"fresh plan preview")
            root.routineName="Desk start"
            saveCheck.start()
        })
    }}
    Timer {id:saveCheck;interval:100;onTriggered:{
        var save=button(chatContent,"Save routine")
        if(!save || !save.enabled)fail(8,"save control")
        save.clicked()
        if(JSON.stringify(lastRequest(routineCall))!==JSON.stringify(["routines","save",testToken,"Desk start"]) || actor.requests.length)fail(9,"save without run")
        routineCall.received({savedId:"3333333333333333",text:"Saved.",routines:testRoutines})
        if(root.routineName || root.pending!==testToken || actor.requests.length)fail(10,"save keeps review")
        root.showPanel("routines")
        routineCall.received({routines:testRoutines})
        removeCheck.start()
    }}
    Timer {id:removeCheck;interval:80;onTriggered:{
        var removes=buttons(testRoutinePanel.contentItem,"Remove",[])
        if(removes.length!==2 || !removes[1].enabled)fail(11,"remove controls")
        removes[1].clicked()
        if(JSON.stringify(lastRequest(routineCall))!==JSON.stringify(["routines","remove",testRoutines[1].id]))fail(12,"remove route")
        root.showPanel("settings")
        awarenessConfig.received({settings:{enabled:false,titles:false,command_hints:true,mouse_gestures:false,activity_responses:false,quiet_until:0},snapshot:{},minutes:{},events:[],reflections:[],sampled:0,last_delivered:0})
        settingsCapture.start()
    }}
    Timer {id:settingsCapture;interval:130;onTriggered:{
        var top=button(senses.contentItem,"Turn awareness on")
        var titles=button(senses.contentItem,"Turn titles on")
        var tips=button(senses.contentItem,"Turn tips off")
        var gestures=button(senses.contentItem,"Turn gestures on")
        var bottom=button(senses.contentItem,"Turn responses on")
        if(!top || !titles || !tips || !gestures || !bottom)fail(13,"five signal controls")
        if(!top.focusable || !bottom.focusable)fail(14,"signal keyboard access")
        var view=scrollView(senses.contentItem)
        if(!view || view.contentHeight<=view.height)fail(15,"signal viewport")
        senses.contentItem.children[0].grabToImage(function(result){
            if(!result.saveToFile(SIGNALS_TOP_IMAGE))fail(16,"signal top capture")
            top.clicked()
            if(JSON.stringify(lastRequest(awarenessConfig))!==JSON.stringify(["awareness","enabled","on"]))fail(17,"awareness toggle route")
            if(senses.state.settings.enabled)fail(18,"toggle requires backend receipt")
            bottom.forceActiveFocus()
            if(!bottom.activeFocus)fail(19,"bottom signal focus")
            focusCheck.start()
        })
    }}
    Timer {id:focusCheck;interval:100;onTriggered:{
        var bottom=button(senses.contentItem,"Turn responses on")
        var view=scrollView(senses.contentItem)
        var pos=bottom.mapToItem(view,0,0)
        if(pos.y<-.5 || pos.y+bottom.height>view.height+.5)fail(20,"focused signal is offscreen: "+JSON.stringify({y:pos.y,height:bottom.height,viewHeight:view.height,contentY:view.contentY,contentHeight:view.contentHeight}))
        senses.contentItem.children[0].grabToImage(function(result){
            if(!result.saveToFile(SIGNALS_BOTTOM_IMAGE))fail(21,"signal bottom capture")
            bottom.clicked()
            if(JSON.stringify(lastRequest(awarenessConfig))!==JSON.stringify(["awareness","activity_responses","on"]))fail(22,"activity toggle route")
            continueToTour()
        })
    }}
    Timer {id:tourCheck;interval:100;onTriggered:{
        var tries=buttons(testTourPanel.contentItem,"Try this",[])
        var done=button(testTourPanel.contentItem,"Got it")
        if(tries.length!==2 || !done || !done.focusable)fail(24,"tour actions")
        testTourPanel.contentItem.children[0].grabToImage(function(result){
            if(!result.saveToFile(TOUR_IMAGE))fail(25,"tour capture")
            tries[0].clicked()
            if(!root.routinesOpen || root.tourOpen || lastRequest(routineCall)[0]!=="routines")fail(26,"tour destination")
            root.showPanel("tour")
            done.clicked()
            if(JSON.stringify(lastRequest(tourCall))!==JSON.stringify(["tour","seen"]))fail(27,"mark tour seen")
            tourCall.received({version:"2.2",unseen:false,cards:[]})
            if(root.tourOpen || root.tourFinishing)fail(28,"tour closes after receipt")
            root.showPanel("chat")
            brain.received({text:"I could not confirm the current audio output.",route:"local",evidence:{sourceId:"audio_output",sourceLabel:"Audio output",observedAtMs:Date.now(),expiresAtMs:null,status:"unknown",verification:"state",unknownReason:"No active audio output was reported."}})
            evidenceCheck.start()
        })
    }}
    Timer {id:evidenceCheck;interval:100;onTriggered:{
        if(root.evidenceStatus()!=="Could not verify" || root.evidence.unknownReason!=="No active audio output was reported.")fail(34,"unknown machine evidence")
        if(!readingPane.visible || !field.visible || chatSurface.height+chatSurface.y>win.screen.height+.5)fail(35,"bounded chat and composer")
        var evidencePos=evidenceCard.mapToItem(readingPane,0,0)
        if(evidencePos.y<-.5 || evidencePos.y+evidenceCard.height>readingPane.height+.5)fail(37,"evidence card initially clipped: "+JSON.stringify({y:evidencePos.y,cardHeight:evidenceCard.height,paneHeight:readingPane.height,contentY:readingPane.contentY,contentHeight:readingPane.contentHeight}))
        var reason=textItem(evidenceCard,"No active audio output was reported.")
        var reasonPos=reason ? reason.mapToItem(readingPane,0,0) : {y:-100}
        if(!reason || reasonPos.y<-.5 || reasonPos.y+reason.height>readingPane.height+.5)fail(38,"unknown reason clipped: "+JSON.stringify({y:reasonPos.y,reasonHeight:reason&&reason.height,paneHeight:readingPane.height,cardHeight:evidenceCard.height,bodyHeight:evidenceBody.implicitHeight}))
        chatSurface.grabToImage(function(result){
            if(!result.saveToFile(EVIDENCE_IMAGE))fail(36,"evidence capture")
            if(win.screen.width<500){
                root.moreOpen=true
                var roomButtons=buttons(chatContent,"Room",[])
                var roomAction=roomButtons.filter(function(item){return item.visible})[0]
                if(!roomAction)fail(39,"narrow navigation hides Room")
                roomAction.clicked()
                if(!root.roomOpen || root.opened)fail(40,"narrow Room route")
            }
            console.log("ROUTINES_SIGNALS_UI_OK");Qt.quit()
        })
    }}
'''.replace('TOKEN', json.dumps(token)).replace('ROUTINES_IMAGE', json.dumps(str(capture / 'wisp-routines.png'))).replace('SIGNALS_TOP_IMAGE', json.dumps(str(capture / 'wisp-signals-top.png'))).replace('SIGNALS_BOTTOM_IMAGE', json.dumps(str(capture / 'wisp-signals-bottom.png')))
            probe = probe.replace('TOUR_IMAGE', json.dumps(str(capture / 'wisp-tour.png')))
            probe = probe.replace('EVIDENCE_IMAGE', json.dumps(str(capture / 'wisp-evidence.png')))
            desktop = folder / 'Desktop.qml'
            content = desktop.read_text().replace('    id: root', '    id: root\n' + probe, 1)
            content = content.replace('    RoutinePanel {', '    RoutinePanel {\n        id: testRoutinePanel', 1)
            content = content.replace('    TourPanel {', '    TourPanel {\n        id: testTourPanel', 1)
            desktop.write_text(content)
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
            self.assertIn('ROUTINES_SIGNALS_UI_OK', output)
            for failure in ('TypeError', 'ReferenceError', 'Binding loop', 'UI_FAIL'):
                self.assertNotIn(failure, output)
            for name in ('wisp-routines.png', 'wisp-signals-top.png', 'wisp-signals-bottom.png', 'wisp-tour.png', 'wisp-evidence.png'):
                self.assertGreater((capture / name).stat().st_size, 0)


if __name__ == '__main__':
    unittest.main()
