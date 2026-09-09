import QtQuick
import qs.Commons
import qs.Ui as Ui
Item {
    id: bubble
    property string name: "Wisp"
    property string text: ""
    property bool preview: false
    signal dismissed()
    signal hovered(bool active)
    implicitWidth: 304
    implicitHeight: content.implicitHeight + 28
    Rectangle {x:33;y:-5;width:10;height:10;rotation:45;color:Color.popups.background;border.color:Color.popups.border}
    Ui.BorderSurface {
        anchors.fill:parent;color:Color.popups.background;radius:Style.cornerRadius
        borderSpec:Border.surfaceSpec("popup","border",Color.popups.border,1)
        Column {
            id:content;x:14;y:14;width:parent.width-28;spacing:8
            Row {
                width:parent.width
                Text {width:parent.width-18;text:bubble.name+(bubble.preview?" · Preview":"");elide:Text.ElideRight;color:Color.accent;font.family:Style.font.family;font.pixelSize:Style.font.caption}
                Text {text:"×";color:Color.foreground;opacity:0.5;font.pixelSize:Style.font.caption}
            }
            Text {width:parent.width;text:bubble.text;textFormat:Text.PlainText;wrapMode:Text.Wrap;color:Color.foreground;font.family:Style.font.family;font.pixelSize:Style.font.body;maximumLineCount:6;elide:Text.ElideRight}
        }
        MouseArea {anchors.fill:parent;hoverEnabled:true;onClicked:bubble.dismissed();onEntered:bubble.hovered(true);onExited:bubble.hovered(false)}
    }
}
