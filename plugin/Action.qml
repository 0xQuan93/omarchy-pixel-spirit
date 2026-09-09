import QtQuick
import qs.Commons
Rectangle {
    id: root
    property string text: ""
    signal clicked()
    implicitWidth: label.implicitWidth + 20
    implicitHeight: 30
    radius: 7
    color: Qt.alpha(Color.accent, mouse.containsMouse ? 0.25 : 0.10)
    opacity: enabled ? 1 : 0.4
    Text { id: label; anchors.centerIn: parent; text: root.text; color: Color.popups.text; font.family: Style.fontFamily; font.pixelSize: 12 }
    MouseArea { id: mouse; anchors.fill: parent; hoverEnabled: true; cursorShape: Qt.PointingHandCursor; onClicked: root.clicked() }
}
