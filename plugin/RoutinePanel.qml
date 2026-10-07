import QtQuick
import QtQuick.Controls as Controls
import Quickshell
import Quickshell.Wayland
import qs.Commons
import qs.Ui as Ui

PanelWindow {
    id: panel
    property var routines: []
    property string detail: ""
    property bool busy: false
    signal prepare(string routineId)
    signal remove(string routineId)
    signal closeRequested()
    function reveal(item) {
        var top = item.mapToItem(list, 0, 0).y
        if (top < listViewport.contentY) listViewport.contentY = top
        else if (top + item.height > listViewport.contentY + listViewport.height)
            listViewport.contentY = Math.min(top + item.height - listViewport.height, Math.max(0, listViewport.contentHeight - listViewport.height))
    }
    anchors {top:true;right:true}
    margins {top:45;right:24}
    implicitWidth:Math.max(260,Math.min(460,(screen?screen.width:1920)-32))
    implicitHeight:Math.min(530,screen?screen.height-90:530,
        Math.max(260,40+header.implicitHeight+intro.implicitHeight+(detailText.visible?detailText.implicitHeight:0)+list.implicitHeight+48))
    color:"transparent";exclusionMode:ExclusionMode.Ignore
    WlrLayershell.namespace:"pixel-spirit-routines"
    WlrLayershell.layer:WlrLayer.Overlay
    WlrLayershell.keyboardFocus:WlrKeyboardFocus.OnDemand
    Ui.BorderSurface {
        anchors.fill:parent;color:Color.popups.background;radius:Style.cornerRadius
        borderSpec:Border.surfaceSpec("popup","border",Color.popups.border,1)
        Column {
            anchors.fill:parent;anchors.margins:20;spacing:12
            Row {
                id:header
                width:parent.width;spacing:8
                Column {width:parent.width-closeButton.width-parent.spacing;spacing:4
                    Text {text:"Reviewed routines";color:Color.accent;font.family:Style.font.family;font.pixelSize:Style.font.title}
                    Text {text:panel.routines.length+" saved · 24 maximum";color:Color.foreground;opacity:0.7;font.family:Style.font.family;font.pixelSize:Style.font.bodySmall}
                }
                Action {id:closeButton;text:"Close";onClicked:panel.closeRequested()}
            }
            Text {
                id:intro
                width:parent.width
                text:"Save a plan from chat. Reviewing a routine creates a fresh plan with a separate Run step. Removed or changed controls cannot run."
                textFormat:Text.PlainText;wrapMode:Text.Wrap;color:Color.foreground
                font.family:Style.font.family;font.pixelSize:Style.font.bodySmall
            }
            Text {
                id:detailText
                visible:!!panel.detail;width:parent.width;text:panel.detail;textFormat:Text.PlainText
                wrapMode:Text.Wrap;color:Color.accent;font.family:Style.font.family;font.pixelSize:Style.font.bodySmall
            }
            Flickable {
                id:listViewport
                width:parent.width;height:parent.height-y-4;clip:true
                contentHeight:list.implicitHeight;boundsBehavior:Flickable.StopAtBounds
                Controls.ScrollBar.vertical:Controls.ScrollBar {}
                Column {
                    id:list;width:parent.width-8;spacing:8
                    Text {
                        visible:panel.routines.length===0;width:parent.width
                        text:"No routines yet. Ask Wisp for a short plan, then name it beside Run plan."
                        textFormat:Text.PlainText;wrapMode:Text.Wrap;color:Color.foreground
                        font.family:Style.font.family;font.pixelSize:Style.font.body
                    }
                    Repeater {
                        model:panel.routines
                        Ui.BorderSurface {
                            required property var modelData
                            width:list.width;height:entry.implicitHeight+20
                            radius:Style.cornerRadius;color:Qt.alpha(Color.accent,0.04)
                            borderSpec:Border.surfaceSpec("popup","border",Color.popups.border,1)
                            Column {
                                id:entry;x:10;y:10;width:parent.width-20;spacing:7
                                Text {width:parent.width;text:modelData.name;textFormat:Text.PlainText;wrapMode:Text.Wrap;color:Color.foreground;font.family:Style.font.family;font.pixelSize:Style.font.body;font.bold:true}
                                Text {width:parent.width;text:modelData.steps+" steps · "+(modelData.ready?"Ready to review":"Needs a fresh plan")+(modelData.reason?" · "+modelData.reason:"");textFormat:Text.PlainText;wrapMode:Text.Wrap;color:modelData.ready?Color.accent:Color.foreground;font.family:Style.font.family;font.pixelSize:Style.font.bodySmall}
                                Flow {width:parent.width;spacing:6
                                    Action {text:"Review";enabled:modelData.ready&&!panel.busy;onClicked:panel.prepare(modelData.id);onActiveFocusChanged:if(activeFocus)panel.reveal(this)}
                                    Action {text:"Remove";enabled:!panel.busy;onClicked:panel.remove(modelData.id);onActiveFocusChanged:if(activeFocus)panel.reveal(this)}
                                }
                            }
                        }
                    }
                }
            }
        }
    }
}
