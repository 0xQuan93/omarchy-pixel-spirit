import QtQuick
import QtQuick.Controls as Controls
import Quickshell
import Quickshell.Wayland
import qs.Commons
PanelWindow {
    id: room
    property var profile: ({name:"Wisp",seed:0,device:"portable"})
    property string family: "Maker"
    property var roomState: ({bond:0,notes:[],activity:"rest",earned:[],message:"A little room between the pixels."})
    property var growth: ({level:0,trait:"Maker"})
    property bool eco: false
    property bool busy: false
    property string movement: "roam"
    property int caught: 0
    signal interact(string action, string value)
    signal choose()
    signal movementSelected(string mode)
    signal closeRequested()
    anchors {right:true;bottom:true}
    margins {right:24;bottom:24}
    implicitWidth:500;implicitHeight:610
    color:"transparent";exclusionMode:ExclusionMode.Ignore
    WlrLayershell.namespace:"pixel-spirit-room"
    WlrLayershell.layer:WlrLayer.Overlay
    WlrLayershell.keyboardFocus:WlrKeyboardFocus.OnDemand
    Rectangle {
        anchors.fill:parent;radius:18;color:Color.popups.background;border.color:Color.accent
        Column {
            anchors.fill:parent;anchors.margins:20;spacing:12
            Row {
                spacing:8
                Text {text:room.profile.name.toUpperCase()+"’S POCKET ROOM";color:Color.accent;font.family:Style.fontFamily;font.bold:true;width:330;anchors.verticalCenter:parent.verticalCenter}
                Action {text:"Close";onClicked:room.closeRequested()}
            }
            RoomScene {
                width:460;height:259;profile:room.profile;growth:room.growth;roomState:room.roomState;family:room.family
                active:room.visible;eco:room.eco;interactive:true
                accent:Color.accent;foreground:Color.popups.text;background:Color.popups.background
                onCaughtFireflies:room.interact("catch","")
                DropArea {anchors.fill:parent;onDropped:function(drop){if(drop.hasUrls)room.interact("note",drop.urls[0].toString());else if(drop.hasText)room.interact("note",drop.text);drop.acceptProposedAction()}}
            }
            Row {spacing:7
                Repeater {model:["rest","read","play","garden"];Action {required property string modelData;text:modelData;enabled:!room.busy;onClicked:room.interact("activity",modelData)}}
                Action {text:room.busy?"Thinking…":"Choose activity";enabled:!room.busy;onClicked:room.choose()}
            }
            Text {width:460;text:room.roomState.message+"\nBond "+room.roomState.bond+" · "+room.roomState.earned.length+"/7 daily discoveries · sparks "+room.caught+"/3";textFormat:Text.PlainText;wrapMode:Text.Wrap;color:Color.popups.text;font.pixelSize:12;font.family:Style.fontFamily}
            Row {spacing:7
                Text {text:"Outside:";color:Color.accent;anchors.verticalCenter:parent.verticalCenter}
                Repeater {model:["stay","roam","follow"];Action {required property string modelData;text:(room.movement===modelData?"● ":"")+modelData;onClicked:room.movementSelected(modelData)}}
            }
            Row {spacing:7
                Controls.TextField {id:note;width:355;height:32;placeholderText:"Leave a small note, or drop one into the room";color:Color.popups.text;selectByMouse:true;background:Rectangle{radius:6;color:Qt.alpha(Color.accent,0.08);border.color:Color.popups.border} onAccepted:{room.interact("note",text);text=""}}
                Action {text:"Leave note";enabled:!room.busy;onClicked:{room.interact("note",note.text);note.text=""}}
            }
            Row {spacing:8
                Action {text:"Read latest";onClicked:room.interact("activity","read")}
                Action {text:"Empty shelf";enabled:!room.busy;onClicked:room.interact("clear_notes","")}
                Text {text:"Plant 3 · lamp 8 · crown 16 bond";color:Color.accent;font.pixelSize:10;anchors.verticalCenter:parent.verticalCenter}
            }
            Text {width:460;text:room.roomState.notes.length?room.roomState.notes[room.roomState.notes.length-1].text:"Triple-click Wisp’s head for a little affection.";textFormat:Text.PlainText;color:Color.popups.text;opacity:0.7;font.pixelSize:11;wrapMode:Text.Wrap;maximumLineCount:2;elide:Text.ElideRight}
        }
    }
}
