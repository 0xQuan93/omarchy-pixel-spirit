import QtQuick
import QtQuick.Controls as Controls
import Quickshell
import Quickshell.Wayland
import qs.Commons
import qs.Ui as Ui

PanelWindow {
    id: panel
    property var cards: []
    property string version: ""
    property bool busy: false
    property string detail: ""
    signal destinationRequested(string destination)
    signal finishRequested()
    signal closeRequested()
    anchors {top:true;right:true}
    margins {top:45;right:24}
    implicitWidth:Math.max(280,Math.min(480,(screen?screen.width:1920)-32))
    implicitHeight:Math.min(570,screen?screen.height-90:570)
    color:"transparent";exclusionMode:ExclusionMode.Ignore
    WlrLayershell.namespace:"pixel-spirit-tour"
    WlrLayershell.layer:WlrLayer.Overlay
    WlrLayershell.keyboardFocus:WlrKeyboardFocus.OnDemand
    Ui.BorderSurface {
        anchors.fill:parent;color:Color.popups.background;radius:Style.cornerRadius
        borderSpec:Border.surfaceSpec("popup","border",Color.popups.border,1)
        Column {
            anchors.fill:parent;anchors.margins:20;spacing:12
            Row {width:parent.width;spacing:8
                Column {width:parent.width-closeButton.width-parent.spacing;spacing:4
                    Text {text:"What changed in Wisp";color:Color.accent;font.family:Style.font.family;font.pixelSize:Style.font.title}
                    Text {text:panel.version?"Version "+panel.version:"Recent changes";color:Color.foreground;opacity:0.7;font.family:Style.font.family;font.pixelSize:Style.font.bodySmall}
                }
                Action {id:closeButton;text:"Close";onClicked:panel.closeRequested()}
            }
            Flickable {
                width:parent.width;height:Math.max(0,parent.height-y-footer.implicitHeight-16)
                contentHeight:guide.implicitHeight;clip:true
                boundsBehavior:Flickable.StopAtBounds
                Controls.ScrollBar.vertical:Controls.ScrollBar {}
                Column {id:guide;width:parent.width-8;spacing:10
                    Text {width:parent.width;text:"Pick a change to try, or come back later from More.";textFormat:Text.PlainText;wrapMode:Text.Wrap;color:Color.foreground;font.family:Style.font.family;font.pixelSize:Style.font.body}
                    Repeater {model:panel.cards
                        Ui.BorderSurface {
                            required property var modelData
                            width:guide.width;height:cardBody.implicitHeight+20
                            radius:Style.cornerRadius;color:Qt.alpha(Color.accent,0.04)
                            borderSpec:Border.surfaceSpec("popup","border",Color.popups.border,1)
                            Column {id:cardBody;x:10;y:10;width:parent.width-20;spacing:7
                                Text {width:parent.width;text:modelData.title;textFormat:Text.PlainText;wrapMode:Text.Wrap;color:Color.accent;font.family:Style.font.family;font.pixelSize:Style.font.body;font.bold:true}
                                Text {width:parent.width;text:modelData.text;textFormat:Text.PlainText;wrapMode:Text.Wrap;color:Color.foreground;font.family:Style.font.family;font.pixelSize:Style.font.bodySmall}
                                Action {text:"Try this";onClicked:panel.destinationRequested(modelData.destination)}
                            }
                        }
                    }
                    Text {visible:!!panel.detail;width:parent.width;text:panel.detail;textFormat:Text.PlainText;wrapMode:Text.Wrap;color:Color.accent;font.family:Style.font.family;font.pixelSize:Style.font.bodySmall}
                }
            }
            Flow {id:footer;width:parent.width;spacing:6
                Action {text:panel.busy?"Saving…":"Got it";enabled:!panel.busy;onClicked:panel.finishRequested()}
            }
        }
    }
}
