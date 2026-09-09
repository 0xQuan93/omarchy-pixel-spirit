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
    property string page: "thoughts"
    property double now: Date.now()
    property bool paused: state.settings.quiet_until*1000>now
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
                Action {text:"Tools";selected:panel.page==="tools";onClicked:panel.page="tools"}
                Action {text:"Settings";selected:panel.page==="settings";onClicked:panel.page="settings"}
                Action {text:"Close";onClicked:panel.closeRequested()}
            }
            Flickable {
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
                        visible:panel.page==="tools";width:parent.width;spacing:16
                        Text {width:parent.width;text:"Choose a tool, then confirm with Run in chat.";wrapMode:Text.Wrap;color:Color.foreground;opacity:0.7;font.family:Style.font.family;font.pixelSize:Style.font.body}
                        Repeater {
                            model:[{name:"Open",ids:["browser","terminal","files","notes"]},{name:"Sound",ids:["volume_up","volume_down","mute","unmute","toggle_mute","pause_music","play_music","play_pause","next_track"]},{name:"Desktop",ids:["workspace_next","workspace_previous","brightness_up","brightness_down","power_saver","power_balanced","dnd_on","dnd_off"]}]
                            Column {
                                required property var modelData;width:body.width;spacing:6
                                Text {text:modelData.name;color:Color.accent;font.family:Style.font.family;font.pixelSize:Style.font.caption}
                                Grid {width:parent.width;columns:2;columnSpacing:8;rowSpacing:5
                                    Repeater {model:panel.tools.filter(function(t){return modelData.ids.indexOf(t.id)>=0})
                                        Action {required property var modelData;width:(body.width-8)/2;leftAlign:true;text:modelData.label;enabled:modelData.available;tooltipText:modelData.available?"":"Needs "+modelData.requires;onClicked:panel.propose(modelData.id,modelData.label)}
                                    }
                                }
                            }
                        }
                    }
                    Column {
                        visible:panel.page==="settings";width:parent.width;spacing:16
                        Text {text:"Quiet company";color:Color.accent;font.family:Style.font.family;font.pixelSize:Style.font.title}
                        Text {width:parent.width;text:"Brief speech bubbles beside your companion, saved in Thoughts. Hover to keep one open; click to dismiss.";wrapMode:Text.Wrap;color:Color.foreground;font.family:Style.font.family;font.pixelSize:Style.font.body;lineHeight:1.2}
                        Flow {width:parent.width;spacing:6
                            Action {text:panel.state.settings.enabled?"Awareness on":"Awareness off";selected:panel.state.settings.enabled;enabled:!panel.busy;onClicked:panel.change("enabled",panel.state.settings.enabled?"off":"on")}
                            Action {text:panel.paused?"Resume":"Pause 1h";enabled:!panel.busy;onClicked:panel.change(panel.paused?"resume":"pause","")}
                            Action {text:"Preview bubble";onClicked:panel.previewBubble()}
                        }
                        Text {width:parent.width;text:panel.state.error||(!panel.state.settings.enabled?"Awareness is off.":panel.paused?"Paused until "+new Date(panel.state.settings.quiet_until*1000).toLocaleTimeString():!panel.pluggedIn?"Resting on battery.":panel.detail||"Quiet comments while plugged in · at most every 20 minutes");wrapMode:Text.Wrap;color:Color.accent;font.family:Style.font.family;font.pixelSize:Style.font.bodySmall}
                        Disclosure {
                            width:parent.width;title:"Privacy and data"
                            Text {width:body.width;text:"App identity and workspace are used for context. No screenshots or typed text. Window titles can include document names and URLs.";wrapMode:Text.Wrap;color:Color.foreground;font.family:Style.font.family;font.pixelSize:Style.font.body}
                            Action {text:panel.state.settings.titles?"Window titles on":"Window titles off";selected:panel.state.settings.titles;enabled:!panel.busy;onClicked:panel.change("titles",panel.state.settings.titles?"off":"on")}
                            Text {width:body.width;text:"Turning titles off also clears saved titles and old thoughts. Awareness rests when idle, locked, in fullscreen, on battery, in power saver or Do Not Disturb.";wrapMode:Text.Wrap;color:Color.foreground;opacity:0.65;font.family:Style.font.family;font.pixelSize:Style.font.bodySmall}
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
