import QtQuick
import QtQuick.Controls as Controls
import Quickshell
import Quickshell.Wayland
import qs.Commons
import qs.Ui as Ui
PanelWindow {
    id: room
    property var profile: ({name:"Wisp",seed:0,device:"portable"})
    property string family: "Maker"
    property var roomState: ({bond:0,notes:[],activity:"rest",earned:[],message:"Welcome home."})
    property var growth: ({level:0,trait:"Maker"})
    property bool eco: false
    property bool busy: false
    property string movement: "roam"
    signal interact(string action,string value)
    signal choose()
    signal movementSelected(string mode)
    signal closeRequested()
    anchors {right:true;bottom:true}
    margins {right:24;bottom:24}
    implicitWidth:Math.max(260,Math.min(500,(screen?screen.width:1920)-32));implicitHeight:Math.min(575,screen?screen.height-80:575)
    color:"transparent";exclusionMode:ExclusionMode.Ignore
    WlrLayershell.namespace:"pixel-spirit-room";WlrLayershell.layer:WlrLayer.Overlay;WlrLayershell.keyboardFocus:WlrKeyboardFocus.OnDemand
    Ui.BorderSurface {
        anchors.fill:parent;color:Color.popups.background;radius:Style.cornerRadius
        borderSpec:Border.surfaceSpec("popup","border",Color.popups.border,1)
        Column {
            anchors.fill:parent;anchors.margins:20;spacing:12
            Row {width:parent.width;spacing:8
                Text {width:parent.width-72;text:room.profile.name+"’s room";elide:Text.ElideRight;color:Color.accent;font.family:Style.font.family;font.pixelSize:Style.font.title;anchors.verticalCenter:parent.verticalCenter}
                Action {text:"Close";onClicked:room.closeRequested()}
            }
            Flickable {
                width:parent.width;height:parent.height-44;clip:true;contentHeight:body.implicitHeight
                boundsBehavior:Flickable.StopAtBounds;Controls.ScrollBar.vertical:Controls.ScrollBar {}
                Column {
                    id:body;width:parent.width-8;spacing:12
                    RoomScene {
                        id:roomScene
                        width:parent.width;height:width*360/640;profile:room.profile;growth:room.growth;roomState:room.roomState;family:room.family
                        active:room.visible;eco:room.eco;interactive:!room.busy
                        accent:Color.accent;foreground:Color.popups.text;background:Color.popups.background
                        onCaughtFireflies:room.interact("catch","")
                        DropArea {anchors.fill:parent;onDropped:function(drop){if(drop.hasUrls)room.interact("note",drop.urls[0].toString());else if(drop.hasText)room.interact("note",drop.text);drop.acceptProposedAction()}}
                    }
                    Text {width:parent.width;text:"Choose an activity";color:Color.accent;font.family:Style.font.family;font.pixelSize:Style.font.bodySmall}
                    Flow {width:parent.width;spacing:5
                        Repeater {model:["rest","read","play","garden"];Action {required property string modelData;text:modelData.charAt(0).toUpperCase()+modelData.slice(1);selected:room.roomState.activity===modelData;enabled:!room.busy;onClicked:room.interact("activity",modelData)}}
                    }
                    Flow {width:parent.width;spacing:5
                        Action {text:room.busy?"Thinking…":"Let Wisp choose";enabled:!room.busy;onClicked:room.choose()}
                        Action {text:"Catch fireflies · "+roomScene.caught+" of 3";tooltipText:"Collect three fireflies for a room discovery";enabled:!room.busy;onClicked:roomScene.catchFirefly()}
                    }
                    Text {width:parent.width;text:room.roomState.message;textFormat:Text.PlainText;wrapMode:Text.Wrap;color:Color.foreground;font.family:Style.font.family;font.pixelSize:Style.font.body;lineHeight:1.2}
                    Disclosure {
                        width:parent.width;title:"Notes · "+room.roomState.notes.length
                        Row {width:parent.width;spacing:6
                            Controls.TextField {id:note;width:Math.max(120,parent.width-saveNote.implicitWidth-parent.spacing);placeholderText:"Leave a small note…";color:Color.foreground;selectByMouse:true;background:Ui.BorderSurface{color:Qt.alpha(Color.accent,0.05);borderSpec:Border.surfaceSpec("popup","border",Color.popups.border,1)}
                            onAccepted:if(!room.busy && text.trim()){room.interact("note",text);text=""}}
                            Action {id:saveNote;text:"Save";enabled:!room.busy && !!note.text.trim();onClicked:{room.interact("note",note.text);note.text=""}}
                        }
                        Repeater {model:room.roomState.notes.slice().reverse()
                            Text {required property var modelData;width:body.width;text:modelData.text;textFormat:Text.PlainText;wrapMode:Text.Wrap;color:Color.foreground;font.family:Style.font.family;font.pixelSize:Style.font.bodySmall}
                        }
                        Action {visible:room.roomState.notes.length>0;text:"Empty shelf";enabled:!room.busy;onClicked:room.interact("clear_notes","")}
                    }
                    Disclosure {
                        width:parent.width;title:"Room details · bond "+room.roomState.bond
                        Text {width:body.width;text:"Plant at 3 · lamp at 8 · crown at 16 bond\n"+room.roomState.earned.length+" of 7 daily discoveries";wrapMode:Text.Wrap;color:Color.foreground;font.family:Style.font.family;font.pixelSize:Style.font.bodySmall}
                        Text {text:"When outside";color:Color.accent;font.family:Style.font.family;font.pixelSize:Style.font.caption}
                        Flow {width:body.width;spacing:5
                            Repeater {model:["stay","roam","follow"];Action {required property string modelData;text:modelData;selected:room.movement===modelData;onClicked:room.movementSelected(modelData)}}
                        }
                    }
                }
            }
        }
    }
}
