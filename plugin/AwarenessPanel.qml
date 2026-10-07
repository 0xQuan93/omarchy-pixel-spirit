import QtQuick
import QtQuick.Controls as Controls
import Quickshell
import Quickshell.Wayland
import qs.Commons
import qs.Ui as Ui
PanelWindow {
    id: panel
    property var state: ({settings:{enabled:false,titles:false,quiet_until:0},snapshot:{},minutes:{},events:[],reflections:[],error:""})
    property var tools: []
    property bool busy: false
    property bool pluggedIn: false
    property string detail: ""
    property string inputSummary: ""
    property string page: "thoughts"
    property double now: Date.now()
    property bool paused: state.settings.quiet_until*1000>now
    function sampledTime() {
        return state.sampled > 0 ? new Date(state.sampled * 1000).toLocaleString() : "No sample yet"
    }
    function deliveredTime() {
        return state.last_delivered > 0 ? new Date(state.last_delivered * 1000).toLocaleString() : "No suggestion or thought delivered yet"
    }
    function sourceState(enabled) {
        if (!enabled) return "Off"
        if (!state.settings.enabled) return "Waiting"
        if (paused || !pluggedIn) return "Resting"
        return "Enabled"
    }
    function revealSignal(item) {
        var top = item.mapToItem(body, 0, 0).y
        if (top < settingsViewport.contentY) settingsViewport.contentY = top
        else if (top + item.height > settingsViewport.contentY + settingsViewport.height)
            settingsViewport.contentY = Math.min(top + item.height - settingsViewport.height, Math.max(0, settingsViewport.contentHeight - settingsViewport.height))
    }
    signal change(string setting,string value)
    signal propose(string action,string label)
    signal previewBubble()
    signal closeRequested()
    anchors {top:true;right:true}
    margins {top:45;right:24}
    implicitWidth:480;implicitHeight:Math.min(570,screen?screen.height-90:570)
    color:"transparent";exclusionMode:ExclusionMode.Ignore
    WlrLayershell.namespace:"pixel-spirit-awareness"
    WlrLayershell.layer:WlrLayer.Overlay
    WlrLayershell.keyboardFocus:WlrKeyboardFocus.OnDemand
    Timer {interval:30000;running:panel.visible;repeat:true;onTriggered:panel.now=Date.now()}
    Ui.BorderSurface {
        anchors.fill:parent;color:Color.popups.background;radius:Style.cornerRadius
        borderSpec:Border.surfaceSpec("popup","border",Color.popups.border,1)
        Column {
            anchors.fill:parent;anchors.margins:20;spacing:14
            Row {
                width:parent.width;spacing:6
                Action {text:"Thoughts";selected:panel.page==="thoughts";onClicked:panel.page="thoughts"}
                Action {text:"Commands";selected:panel.page==="tools";onClicked:panel.page="tools"}
                Action {text:"Settings";selected:panel.page==="settings";onClicked:panel.page="settings"}
                Action {text:"Close";onClicked:panel.closeRequested()}
            }
            CommandBrowser {
                id: commandBrowser
                visible: panel.page === "tools"
                width: parent.width
                height: parent.height - 48
                tools: panel.tools
                busy: panel.busy
                onPropose: function(action, label) { panel.propose(action, label); }
                onCloseRequested: panel.closeRequested()
                onVisibleChanged: if (visible) Qt.callLater(focusSearch)
            }
            Flickable {
                id: settingsViewport
                visible: panel.page !== "tools"
                width:parent.width;height:parent.height-48;clip:true;contentHeight:body.implicitHeight
                boundsBehavior:Flickable.StopAtBounds
                Controls.ScrollBar.vertical:Controls.ScrollBar {}
                Column {
                    id:body;width:parent.width-8;spacing:14
                    Column {
                        visible:panel.page==="thoughts";width:parent.width;spacing:14
                        Text {width:parent.width;text:"Little thoughts from our shared day.";wrapMode:Text.Wrap;color:Color.foreground;font.family:Style.font.family;font.pixelSize:Style.font.body;opacity:0.7}
                        Text {visible:panel.state.reflections.length===0;width:parent.width;text:"Quiet company for now.\nNew thoughts will collect here.";wrapMode:Text.Wrap;color:Color.accent;font.family:Style.font.family;font.pixelSize:Style.font.title;lineHeight:1.5}
                        Repeater {
                            model:panel.state.reflections.slice(0,3)
                            Ui.BorderSurface {
                                required property var modelData
                                width:body.width;height:thought.implicitHeight+24;radius:Style.cornerRadius;color:Qt.alpha(Color.accent,0.05)
                                Column {id:thought;x:12;y:12;width:parent.width-24;spacing:8
                                    Text {width:parent.width;text:modelData.text;textFormat:Text.PlainText;wrapMode:Text.Wrap;color:Color.foreground;font.family:Style.font.family;font.pixelSize:Style.font.body;lineHeight:1.2}
                                    Text {width:parent.width;text:modelData.basis+" · "+new Date(modelData.at*1000).toLocaleTimeString();elide:Text.ElideRight;color:Color.foreground;opacity:0.5;font.family:Style.font.family;font.pixelSize:Style.font.caption}
                                }
                            }
                        }
                        Disclosure {
                            visible:panel.state.reflections.length>3;width:parent.width;title:"Earlier thoughts"
                            Repeater {model:panel.state.reflections.slice(3)
                                Text {required property var modelData;width:body.width;text:modelData.text;textFormat:Text.PlainText;wrapMode:Text.Wrap;color:Color.foreground;font.family:Style.font.family;font.pixelSize:Style.font.body}
                            }
                        }
                        Disclosure {
                            width:parent.width;title:"Activity details"
                            Text {width:body.width;text:panel.state.snapshot.app?"Last seen: "+panel.state.snapshot.app+" · workspace "+panel.state.snapshot.workspace+"\n"+new Date(panel.state.sampled*1000).toLocaleTimeString()+(panel.state.snapshot.title?"\n"+panel.state.snapshot.title:""):"No activity sampled yet.";textFormat:Text.PlainText;wrapMode:Text.Wrap;color:Color.foreground;font.family:Style.font.family;font.pixelSize:Style.font.body}
                            Text {width:body.width;text:"Sampled active minutes\n"+(Object.keys(panel.state.minutes).map(function(k){return k+" "+panel.state.minutes[k]}).join(" · ")||"None yet");wrapMode:Text.Wrap;color:Color.accent;font.family:Style.font.family;font.pixelSize:Style.font.bodySmall}
                            Repeater {model:panel.state.events.slice(0,5)
                                Text {required property var modelData;width:body.width;text:modelData.app+" · "+new Date(modelData.at*1000).toLocaleTimeString();elide:Text.ElideRight;color:Color.foreground;opacity:0.65;font.family:Style.font.family;font.pixelSize:Style.font.bodySmall}
                            }
                        }
                    }
                    Column {
                        visible:panel.page==="settings";width:parent.width;spacing:16
                        Text {text:"Quiet company";color:Color.accent;font.family:Style.font.family;font.pixelSize:Style.font.title}
                        Text {width:parent.width;text:"Useful command tips and occasional thoughts beside your companion. Hover to keep one open; use Dismiss when finished. Suggested commands open for review before they run.";wrapMode:Text.Wrap;color:Color.foreground;font.family:Style.font.family;font.pixelSize:Style.font.body;lineHeight:1.2}
                        Flow {width:parent.width;spacing:6
                            Action {text:panel.state.settings.enabled?"Awareness on":"Awareness off";selected:panel.state.settings.enabled;enabled:!panel.busy;onClicked:panel.change("enabled",panel.state.settings.enabled?"off":"on")}
                            Action {text:panel.paused?"Resume":"Pause 1h";enabled:!panel.busy;onClicked:panel.change(panel.paused?"resume":"pause","")}
                            Action {text:"Preview bubble";onClicked:panel.previewBubble()}
                        }
                        Text {width:parent.width;text:panel.state.error||(!panel.state.settings.enabled?"Awareness is off.":panel.paused?"Paused until "+new Date(panel.state.settings.quiet_until*1000).toLocaleTimeString():!panel.pluggedIn?"Resting on battery.":panel.detail||"Ready for a quiet moment · bubbles at least 20 minutes apart");wrapMode:Text.Wrap;color:Color.accent;font.family:Style.font.family;font.pixelSize:Style.font.bodySmall}
                        Disclosure {
                            width:parent.width;title:"Signal sources";expanded:true
                            SignalCard {
                                width:body.width;title:"App and workspace"
                                status:panel.sourceState(!!panel.state.settings.enabled);selected:!!panel.state.settings.enabled;busy:panel.busy
                                detail:"Reads the active app name, broad category, and workspace for context, short thoughts, and sampled creative time. Fullscreen and private windows are skipped."
                                retention:"Last snapshot, up to 32 app changes, sampled minutes, and up to 12 thoughts remain until cleared. No screenshots or typed text."
                                last:"Last sample: "+panel.sampledTime()
                                actionText:panel.state.settings.enabled?"Turn awareness off":"Turn awareness on"
                                onRequested:panel.change("enabled",panel.state.settings.enabled?"off":"on")
                                onFocusRequested:function(item){panel.revealSignal(item)}
                            }
                            SignalCard {
                                width:body.width;title:"Window titles"
                                status:panel.sourceState(!!panel.state.settings.titles);selected:!!panel.state.settings.titles;busy:panel.busy
                                detail:"Adds the active title to app context when awareness samples. Titles may contain document names or URLs."
                                retention:"A title may remain in the last snapshot, app changes, or generated thoughts. Turning this off clears saved titles and thoughts."
                                last:"Last app sample: "+panel.sampledTime()
                                actionText:panel.state.settings.titles?"Turn titles off":"Turn titles on"
                                onRequested:panel.change("titles",panel.state.settings.titles?"off":"on")
                                onFocusRequested:function(item){panel.revealSignal(item)}
                            }
                            SignalCard {
                                width:body.width;title:"Command tips"
                                status:panel.sourceState(panel.state.settings.command_hints!==false);selected:panel.state.settings.command_hints!==false;busy:panel.busy
                                detail:"Uses the sampled app category to choose an authored Omarchy tip. A tip proposes a command for review; it never runs one."
                                retention:"Delivered tips can remain in the bounded thoughts list until activity and thoughts are cleared."
                                last:"Last bubble: "+panel.deliveredTime()
                                actionText:panel.state.settings.command_hints!==false?"Turn tips off":"Turn tips on"
                                onRequested:panel.change("command_hints",panel.state.settings.command_hints!==false?"off":"on")
                                onFocusRequested:function(item){panel.revealSignal(item)}
                            }
                            SignalCard {
                                width:body.width;title:"Pointer gestures"
                                status:panel.sourceState(!!panel.state.settings.mouse_gestures);selected:!!panel.state.settings.mouse_gestures;busy:panel.busy
                                detail:"Recognizes a small pointer wiggle near Wisp to greet you. Awareness and desktop quiet gates still apply."
                                retention:"Movement samples last under two seconds. No pointer trail or trigger time is saved."
                                last:"Last gesture: not separately retained"
                                actionText:panel.state.settings.mouse_gestures?"Turn gestures off":"Turn gestures on"
                                onRequested:panel.change("mouse_gestures",panel.state.settings.mouse_gestures?"off":"on")
                                onFocusRequested:function(item){panel.revealSignal(item)}
                            }
                            SignalCard {
                                width:body.width;title:"Activity rhythm"
                                status:panel.sourceState(!!panel.state.settings.activity_responses);selected:!!panel.state.settings.activity_responses;busy:panel.busy
                                detail:"Uses recent input activity to settle during work and greet your return after a pause. It does not read key contents."
                                retention:"Recent input timing is transient. No keystrokes or trigger time is saved; it does not award activity growth."
                                last:"Last response: not separately retained"
                                actionText:panel.state.settings.activity_responses?"Turn responses off":"Turn responses on"
                                onRequested:panel.change("activity_responses",panel.state.settings.activity_responses?"off":"on")
                                onFocusRequested:function(item){panel.revealSignal(item)}
                            }
                            Text {width:body.width;text:panel.inputSummary;wrapMode:Text.Wrap;color:Color.foreground;opacity:0.7;font.family:Style.font.family;font.pixelSize:Style.font.bodySmall}
                        }
                        Disclosure {
                            width:parent.width;title:"Privacy and data"
                            Text {width:body.width;text:"Awareness rests when idle, locked, in fullscreen, on battery, in power saver or Do Not Disturb. Signals stay local. The source cards above show each control and its retention.";wrapMode:Text.Wrap;color:Color.foreground;font.family:Style.font.family;font.pixelSize:Style.font.body}
                            Action {text:"Forget activity and thoughts";enabled:!panel.busy;onClicked:panel.change("clear","")}
                            Text {text:"Keeps identity and earned growth.";color:Color.foreground;opacity:0.55;font.family:Style.font.family;font.pixelSize:Style.font.caption}
                        }
                        Disclosure {
                            width:parent.width;title:"How activity shapes growth"
                            Text {width:body.width;text:"Recognized creative apps contribute 1 XP per 30 sampled active minutes, up to 4/day within the shared 24 XP daily cap. App categories are approximate; Other earns no activity XP. File and project changes contribute too.";wrapMode:Text.Wrap;color:Color.foreground;font.family:Style.font.family;font.pixelSize:Style.font.body}
                        }
                    }
                }
            }
        }
    }
}
