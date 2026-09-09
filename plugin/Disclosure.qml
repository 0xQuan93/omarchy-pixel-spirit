import QtQuick
import qs.Commons
Item {
    id: root
    property string title: "Details"
    property bool expanded: false
    default property alias contents: body.data
    implicitHeight: heading.implicitHeight + (expanded ? body.implicitHeight + 10 : 0)
    Action {
        id: heading
        text: (root.expanded ? "−  " : "+  ") + root.title
        onClicked: root.expanded = !root.expanded
    }
    Column {
        id: body
        y: heading.implicitHeight + 10
        width: parent.width
        spacing: 10
        visible: root.expanded
    }
}
