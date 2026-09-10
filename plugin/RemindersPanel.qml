import QtQuick
import QtQuick.Controls as Controls
import Quickshell
import Quickshell.Wayland
import qs.Commons
import qs.Ui as Ui

PanelWindow {
    id: panel
    property var reminders: []
    property var draft: ({minutes:"25",message:""})
    property string detail: ""
    property bool busy: false
    property double now: Date.now()/1000
    signal create(string minutes,string message)
    signal cancel(string unit)
    signal closeRequested()
    onDraftChanged:{duration.text=draft.minutes;message.text=draft.message;}
    anchors {top:true;right:true}
    margins {top:45;right:24}
    implicitWidth:440;implicitHeight:Math.min(560,screen?screen.height-90:560)
    color:"transparent";exclusionMode:ExclusionMode.Ignore
    WlrLayershell.namespace:"pixel-spirit-reminders"
    WlrLayershell.layer:WlrLayer.Overlay
    WlrLayershell.keyboardFocus:WlrKeyboardFocus.OnDemand
    Timer {interval:1000;running:panel.visible;repeat:true;onTriggered:panel.now=Date.now()/1000}
    function remaining(at) {
        var seconds=Math.max(0,Math.ceil(at-panel.now));
        return seconds ? Math.floor(seconds/60)+":"+("0"+seconds%60).slice(-2) : "Due now";
    }
    Ui.BorderSurface {
        anchors.fill:parent;color:Color.popups.background;radius:Style.cornerRadius
        borderSpec:Border.surfaceSpec("popup","border",Color.popups.border,1)
        Column {
            anchors.fill:parent;anchors.margins:20;spacing:14
            Row {width:parent.width;spacing:8
                Text {width:parent.width-76;text:"Timers & reminders";color:Color.accent;font.family:Style.font.family;font.pixelSize:Style.font.title;anchors.verticalCenter:parent.verticalCenter}
                Action {text:"Close";onClicked:panel.closeRequested()}
            }
            Flickable {
                width:parent.width;height:parent.height-48;clip:true;contentHeight:body.implicitHeight
                boundsBehavior:Flickable.StopAtBounds;Controls.ScrollBar.vertical:Controls.ScrollBar {}
                Column {
                    id:body;width:parent.width-8;spacing:12
                    Text {text:"Remind me in…";color:Color.foreground;font.family:Style.font.family;font.pixelSize:Style.font.body}
                    Row {spacing:8
                        Controls.TextField {
                            id:duration;width:90;height:36;text:"25";maximumLength:4;validator:IntValidator {bottom:1;top:1440}
                            color:Color.foreground;font.family:Style.font.family;selectByMouse:true
                            background:Ui.BorderSurface {radius:Style.cornerRadius;color:Qt.alpha(Color.accent,0.05);borderSpec:Border.surfaceSpec("popup","border",Color.popups.border,1)}
                        }
                        Text {text:"minutes";anchors.verticalCenter:parent.verticalCenter;color:Color.foreground;font.family:Style.font.family;font.pixelSize:Style.font.body}
                    }
                    Flow {width:parent.width;spacing:6
                        Repeater {model:[5,15,25,60];Action {required property int modelData;text:modelData+" min";onClicked:duration.text=String(modelData)}}
                    }
                    Controls.TextField {
                        id:message;width:parent.width;height:36;placeholderText:"Reminder message (optional)";maximumLength:240
                        color:Color.foreground;placeholderTextColor:Qt.alpha(Color.foreground,0.5);font.family:Style.font.family;selectByMouse:true
                        background:Ui.BorderSurface {radius:Style.cornerRadius;color:Qt.alpha(Color.accent,0.05);borderSpec:Border.surfaceSpec("popup","border",Color.popups.border,1)}
                    }
                    Action {text:panel.busy?"Setting…":"Set reminder";enabled:!panel.busy && duration.acceptableInput;onClicked:panel.create(duration.text,message.text)}
                    Text {visible:!!panel.detail;width:parent.width;text:panel.detail;textFormat:Text.PlainText;wrapMode:Text.Wrap;color:Color.accent;font.family:Style.font.family;font.pixelSize:Style.font.body}
                    Text {width:parent.width;text:"Omarchy delivers the notification, even if Wisp is hidden or reloaded. Timers last for this login session; Do Not Disturb can silence popups.";wrapMode:Text.Wrap;color:Color.foreground;opacity:0.6;font.family:Style.font.family;font.pixelSize:Style.font.bodySmall}
                    Text {text:"Upcoming on this desktop";color:Color.accent;font.family:Style.font.family;font.pixelSize:Style.font.subtitle}
                    Text {visible:panel.reminders.length===0;text:"No active reminders.";color:Color.foreground;font.family:Style.font.family;font.pixelSize:Style.font.body}
                    Repeater {
                        model:panel.reminders
                        Ui.BorderSurface {
                            required property var modelData
                            width:body.width;height:entry.implicitHeight+20;radius:Style.cornerRadius;color:Qt.alpha(Color.accent,0.05)
                            Column {id:entry;x:10;y:10;width:parent.width-20;spacing:6
                                Text {width:parent.width;text:modelData.label;textFormat:Text.PlainText;wrapMode:Text.Wrap;color:Color.foreground;font.family:Style.font.family;font.pixelSize:Style.font.body}
                                Row {spacing:10
                                    Text {text:panel.remaining(modelData.at);color:Color.accent;font.family:Style.font.family;font.pixelSize:Style.font.body;anchors.verticalCenter:parent.verticalCenter}
                                    Action {text:"Cancel";enabled:!panel.busy;onClicked:panel.cancel(modelData.unit)}
                                }
                            }
                        }
                    }
                }
            }
        }
    }
}
