import QtQuick
import qs.Commons
import qs.Ui as Ui

Ui.BorderSurface {
    id: card
    property string title: ""
    property string status: ""
    property string detail: ""
    property string retention: ""
    property string last: ""
    property string actionText: ""
    property bool selected: false
    property bool busy: false
    signal requested()
    signal focusRequested(var item)
    height: content.implicitHeight + 20
    radius: Style.cornerRadius
    color: Qt.alpha(Color.accent, 0.035)
    borderSpec: Border.surfaceSpec("popup", "border", Color.popups.border, 1)
    Column {
        id: content
        x: 10; y: 10; width: parent.width - 20; spacing: 6
        Row {
            width: parent.width; spacing: 8
            Text {
                width: parent.width - state.width - parent.spacing
                text: card.title; textFormat: Text.PlainText; wrapMode: Text.Wrap
                color: Color.foreground; font.family: Style.font.family
                font.pixelSize: Style.font.body; font.bold: true
            }
            Text {
                id: state; text: card.status; textFormat: Text.PlainText
                color: card.selected ? Color.accent : Color.foreground
                font.family: Style.font.family; font.pixelSize: Style.font.bodySmall
                opacity: card.selected ? 1 : 0.7
            }
        }
        Text {
            width: parent.width; text: card.detail; textFormat: Text.PlainText
            wrapMode: Text.Wrap; color: Color.foreground
            font.family: Style.font.family; font.pixelSize: Style.font.bodySmall
        }
        Text {
            width: parent.width; text: card.retention; textFormat: Text.PlainText
            wrapMode: Text.Wrap; color: Color.foreground; opacity: 0.75
            font.family: Style.font.family; font.pixelSize: Style.font.caption
        }
        Text {
            visible: card.last.length > 0; width: parent.width
            text: card.last; textFormat: Text.PlainText; wrapMode: Text.Wrap
            color: Color.foreground; opacity: 0.75
            font.family: Style.font.family; font.pixelSize: Style.font.caption
        }
        Action {
            visible: card.actionText.length > 0; text: card.actionText
            selected: card.selected; enabled: !card.busy
            onClicked: card.requested()
            onActiveFocusChanged: if (activeFocus) card.focusRequested(this)
        }
    }
}
