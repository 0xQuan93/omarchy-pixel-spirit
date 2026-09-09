import QtQuick
import QtQuick.Controls as Controls
import Quickshell
import Quickshell.Wayland
import qs.Commons
import qs.Ui as Ui

PanelWindow {
    id: panel
    property var state: ({settings:{enabled:false,titles:false,quiet_until:0},snapshot:{},minutes:{},events:[],reflections:[]})
    property var tools: []
    property bool busy: false
    property bool pluggedIn: false
    property string detail: ""
    property bool showTools: false
    signal change(string setting, string value)
    signal propose(string action, string label)
    signal closeRequested()
    anchors {top:true;right:true}
    margins {top:45;right:24}
    implicitWidth:520;implicitHeight:650
    color:"transparent";exclusionMode:ExclusionMode.Ignore
    WlrLayershell.namespace:"pixel-spirit-awareness"
    WlrLayershell.layer:WlrLayer.Overlay
    WlrLayershell.keyboardFocus:WlrKeyboardFocus.OnDemand
    Ui.BorderSurface {
        anchors.fill:parent;color:Color.popups.background;radius:Style.cornerRadius
        borderSpec:Border.surfaceSpec("popup", "border", Color.popups.border, 1)
        Column {
            anchors.fill:parent;anchors.margins:Style.space(20);spacing:Style.space(12)
            Row {
                spacing:Style.space(8)
                Ui.Button {text:"Awareness";selected:!panel.showTools;focusable:true;onClicked:panel.showTools=false}
                Ui.Button {text:"Tools";selected:panel.showTools;focusable:true;onClicked:panel.showTools=true}
                Ui.Button {text:"Close";focusable:true;onClicked:panel.closeRequested()}
            }
            Text {
                width:parent.width;wrapMode:Text.Wrap;color:Color.foreground
                font.family:Style.font.family;font.pixelSize:Style.font.body
                text:panel.showTools?"These are Wisp’s actual desktop tools. Choose one, then use Run in chat. Availability checks the executable; the tool can still report a runtime error.":"A little awareness of our shared day. App identity and workspace are sampled while you are active and plugged in. Quiet, local-model thoughts appear at most once every 20 minutes."
            }
            Flickable {
                width:parent.width;height:490;clip:true
                contentHeight:content.implicitHeight;boundsBehavior:Flickable.StopAtBounds
                Controls.ScrollBar.vertical:Controls.ScrollBar {}
                Column {
                    id:content;width:parent.width-12;spacing:Style.space(12)
                    Column {
                        visible:!panel.showTools;width:parent.width;spacing:Style.space(12)
                        Flow {
                            width:parent.width;spacing:Style.space(6)
                            Ui.Button {text:panel.state.settings.enabled?"Awareness on":"Awareness off";selected:panel.state.settings.enabled;enabled:!panel.busy;focusable:true;onClicked:panel.change("enabled",panel.state.settings.enabled?"off":"on")}
                            Ui.Button {text:"Pause 1h";enabled:!panel.busy;focusable:true;onClicked:panel.change("pause","")}
                            Ui.Button {text:"Resume";enabled:!panel.busy;focusable:true;onClicked:panel.change("resume","")}
                        }
                        Ui.Button {text:panel.state.settings.titles?"Window titles included":"Window titles excluded";selected:panel.state.settings.titles;enabled:!panel.busy;focusable:true;onClicked:panel.change("titles",panel.state.settings.titles?"off":"on")}
                        Text {width:parent.width;wrapMode:Text.Wrap;color:Color.foreground;font.family:Style.font.family;font.pixelSize:Style.font.bodySmall;opacity:0.7;text:"No screenshots, typed text, clipboard, microphone, or browser history. Titles can contain document names and URLs; include them only if you want that context. Turning titles off clears saved titles and old reflections. Awareness pauses while idle, locked, in fullscreen, in power saver or Do Not Disturb."}
                        Text {width:parent.width;wrapMode:Text.Wrap;color:Color.accent;font.family:Style.font.family;font.pixelSize:Style.font.body;text:panel.detail || panel.state.error || (panel.pluggedIn?"Plugged in · waiting for a settled moment":"Battery care · ambient awareness rests")}
                        Text {width:parent.width;wrapMode:Text.Wrap;color:Color.foreground;font.family:Style.font.family;font.pixelSize:Style.font.body;text:panel.state.snapshot.app?"Last sampled: "+panel.state.snapshot.app+" · workspace "+panel.state.snapshot.workspace+"\n"+new Date(panel.state.sampled*1000).toLocaleString()+(panel.state.snapshot.title?"\n"+panel.state.snapshot.title:""):"No activity sampled yet."}
                        Text {width:parent.width;wrapMode:Text.Wrap;color:Color.accent;font.family:Style.font.family;font.pixelSize:Style.font.body;text:"Shared sampled active minutes\n"+(Object.keys(panel.state.minutes).map(function(k){return k+" "+panel.state.minutes[k]}).join(" · ")||"We are just beginning.")}
                        Text {width:parent.width;wrapMode:Text.Wrap;color:Color.foreground;font.family:Style.font.family;font.pixelSize:Style.font.bodySmall;opacity:0.7;text:"Recognized creative apps gently shape growth: +1 XP per 30 sampled active minutes, up to 4/day within the shared 24 XP daily cap. App categories are approximate; Other earns no activity XP."}
                        Text {text:"RECENT THOUGHTS";color:Color.accent;font.family:Style.font.family;font.pixelSize:Style.font.caption}
                        Repeater {
                            model:panel.state.reflections
                            Text {required property var modelData;width:content.width;wrapMode:Text.Wrap;textFormat:Text.PlainText;color:Color.foreground;font.family:Style.font.family;font.pixelSize:Style.font.body;text:modelData.text+"\n"+modelData.basis+" · "+new Date(modelData.at*1000).toLocaleTimeString();opacity:0.85}
                        }
                        Text {text:"RECENT OBSERVATIONS";color:Color.accent;font.family:Style.font.family;font.pixelSize:Style.font.caption}
                        Repeater {
                            model:panel.state.events
                            Text {required property var modelData;width:content.width;wrapMode:Text.Wrap;textFormat:Text.PlainText;color:Color.foreground;font.family:Style.font.family;font.pixelSize:Style.font.bodySmall;text:modelData.app+" · "+modelData.category+" · "+new Date(modelData.at*1000).toLocaleTimeString()}
                        }
                        Ui.Button {text:"Forget observations and thoughts";enabled:!panel.busy;focusable:true;onClicked:panel.change("clear","")}
                    }
                    Flow {
                        visible:panel.showTools;width:parent.width;spacing:Style.space(7)
                        Repeater {
                            model:panel.tools
                            Ui.Button {required property var modelData;text:modelData.label;enabled:modelData.available;focusable:true;tooltipText:modelData.available?"Propose this tool":"Requires "+modelData.requires;onClicked:panel.propose(modelData.id,modelData.label)}
                        }
                    }
                    Text {visible:panel.showTools;width:parent.width;wrapMode:Text.Wrap;color:Color.foreground;font.family:Style.font.family;font.pixelSize:Style.font.bodySmall;text:panel.tools.filter(function(t){return !t.available}).map(function(t){return t.label+": needs "+t.requires}).join("\n")}
                }
            }
        }
    }
}
