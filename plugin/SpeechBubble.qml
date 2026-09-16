import QtQuick
import QtQuick.Controls as Controls
import qs.Commons
import qs.Ui as Ui

FocusScope {
    id: bubble
    property string name: "Wisp"
    property string text: ""
    property bool preview: false
    property string actionLabel: ""
    property string sourceLabel: ""
    property bool expanded: false
    readonly property color surfaceColor: Qt.rgba(Color.popups.background.r, Color.popups.background.g, Color.popups.background.b, 1)
    signal dismissed()
    signal hovered(bool active)
    signal actionRequested()
    implicitWidth: 304
    implicitHeight: content.implicitHeight + 28
    onTextChanged: { expanded = false; messageViewport.contentY = 0; }
    Keys.onEscapePressed: bubble.dismissed()
    onActiveFocusChanged: bubble.hovered(activeFocus || hoverTracker.hovered)
    HoverHandler { id: hoverTracker; onHoveredChanged: bubble.hovered(hovered || bubble.activeFocus) }
    Keys.onDownPressed: if (expanded) messageViewport.contentY = Math.min(Math.max(0, messageViewport.contentHeight - messageViewport.height), messageViewport.contentY + 28)
    Keys.onUpPressed: if (expanded) messageViewport.contentY = Math.max(0, messageViewport.contentY - 28)

    Rectangle {
        x: 33; y: -5; width: 10; height: 10; rotation: 45
        color: bubble.surfaceColor
        border.color: Color.popups.border
    }
    Ui.BorderSurface {
        anchors.fill: parent
        color: bubble.surfaceColor
        radius: Style.cornerRadius
        borderSpec: Border.surfaceSpec("popup", "border", Color.popups.border, 1)
        Column {
            id: content
            x: 14; y: 14; width: parent.width - 28
            spacing: 9
            Text {
                width: parent.width
                text: bubble.name + (bubble.preview ? " · Preview" : "")
                textFormat: Text.PlainText
                elide: Text.ElideRight
                color: Color.accent
                font.family: Style.font.family
                font.pixelSize: Style.font.caption
                font.bold: true
            }
            Text {
                width: parent.width
                visible: bubble.sourceLabel.length > 0
                text: bubble.sourceLabel
                textFormat: Text.PlainText
                wrapMode: Text.Wrap
                maximumLineCount: 2
                elide: Text.ElideRight
                color: Color.foreground
                opacity: 0.6
                font.family: Style.font.family
                font.pixelSize: Style.font.caption
            }
            Flickable {
                id: messageViewport
                width: parent.width
                height: Math.min(message.implicitHeight, bubble.expanded ? 240 : 132)
                contentHeight: message.implicitHeight
                clip: true
                interactive: bubble.expanded && contentHeight > height
                boundsBehavior: Flickable.StopAtBounds
                Controls.ScrollBar.vertical: Controls.ScrollBar {
                    policy: messageViewport.interactive ? Controls.ScrollBar.AsNeeded : Controls.ScrollBar.AlwaysOff
                }
                Text {
                    id: message
                    width: parent.width - (bubble.expanded ? 10 : 0)
                    text: bubble.text
                    textFormat: Text.PlainText
                    wrapMode: Text.Wrap
                    maximumLineCount: bubble.expanded ? 10000 : 6
                    elide: Text.ElideRight
                    color: Color.foreground
                    font.family: Style.font.family
                    font.pixelSize: Style.font.body
                    lineHeight: 1.2
                    Accessible.role: Accessible.StaticText
                    Accessible.name: bubble.text
                }
            }
            Controls.Button {
                id: primaryAction
                text: bubble.actionLabel
                visible: bubble.actionLabel.length > 0
                width: parent.width
                padding: 8
                implicitHeight: actionText.implicitHeight + padding * 2
                focusPolicy: Qt.TabFocus
                Accessible.name: bubble.actionLabel
                onClicked: bubble.actionRequested()
                background: Ui.BorderSurface {
                    radius: Style.cornerRadius
                    color: Qt.alpha(Color.accent, primaryAction.hovered || primaryAction.activeFocus ? 0.15 : 0.08)
                    borderSpec: Border.controlSpec(primaryAction.activeFocus ? "focus" : primaryAction.hovered ? "hover-cursor" : "normal", Color.foreground, Color.accent)
                }
                contentItem: Text {
                    id: actionText
                    text: bubble.actionLabel
                    textFormat: Text.PlainText
                    wrapMode: Text.Wrap
                    color: Color.accent
                    font.family: Style.font.family
                    font.pixelSize: Style.font.bodySmall
                    horizontalAlignment: Text.AlignHCenter
                }
            }
            Row {
                width: parent.width
                spacing: 6
                Action {
                    visible: message.truncated || bubble.expanded || message.implicitHeight > messageViewport.height
                    text: bubble.expanded ? "Read less" : "Read more"
                    fontSize: Style.font.caption
                    onClicked: { bubble.expanded = !bubble.expanded; messageViewport.contentY = 0; }
                }
                Action {
                    text: "Dismiss"
                    fontSize: Style.font.caption
                    tooltipText: "Dismiss this message"
                    Accessible.name: "Dismiss message"
                    onClicked: bubble.dismissed()
                }
            }
        }
    }
}
