import QtQuick
import QtQuick.Controls as Controls
import Quickshell
import Quickshell.Wayland
import qs.Commons
import qs.Ui as Ui

PanelWindow {
    id: panel
    property var setup: ({})
    property bool awarenessEnabled: false
    property bool titlesEnabled: false
    property bool busy: false
    property string error: ""
    signal finishRequested()
    signal closeRequested()
    signal commandsRequested()
    signal roomRequested()
    signal settingsRequested()
    anchors { top: true; right: true }
    margins { top: 45; right: 24 }
    implicitWidth: Math.max(260, Math.min(480, (screen ? screen.width : 1920) - 32))
    implicitHeight: Math.min(585, screen ? screen.height - 80 : 585)
    color: "transparent"
    exclusionMode: ExclusionMode.Ignore
    WlrLayershell.namespace: "pixel-spirit-setup"
    WlrLayershell.layer: WlrLayer.Overlay
    WlrLayershell.keyboardFocus: WlrKeyboardFocus.OnDemand
    Ui.BorderSurface {
        anchors.fill: parent
        color: Color.popups.background
        radius: Style.cornerRadius
        borderSpec: Border.surfaceSpec("popup", "border", Color.popups.border, 1)
        Column {
            anchors.fill: parent; anchors.margins: 20; spacing: 12
            Row {
                id: setupHeader
                width: parent.width; spacing: 8
                Text { width: parent.width - closeButton.width - parent.spacing; text: "Getting started with Wisp"; wrapMode: Text.Wrap; color: Color.accent; font.family: Style.font.family; font.pixelSize: Style.font.title }
                Action { id: closeButton; text: "Close"; onClicked: panel.closeRequested() }
            }
            Flickable {
                width: parent.width; height: Math.max(0, parent.height - setupHeader.height - footer.height - parent.spacing * 2)
                contentHeight: guide.implicitHeight; clip: true
                boundsBehavior: Flickable.StopAtBounds
                Controls.ScrollBar.vertical: Controls.ScrollBar {}
                Column {
                    id: guide; width: parent.width - 8; spacing: 16
                    Text { width: parent.width; text: panel.setup.text || "Make yourself at home."; textFormat: Text.PlainText; wrapMode: Text.Wrap; color: Color.foreground; font.family: Style.font.family; font.pixelSize: Style.font.body }
                    Ui.BorderSurface {
                        width: parent.width; height: commandPath.implicitHeight + 24
                        radius: Style.cornerRadius; color: Qt.alpha(Color.accent, 0.05)
                        Column {
                            id: commandPath; x: 12; y: 12; width: parent.width - 24; spacing: 6
                            Text { width: parent.width; text: "1 · Get desktop help"; color: Color.accent; font.family: Style.font.family; font.pixelSize: Style.font.body; font.bold: true }
                            Text { width: parent.width; text: typeof panel.setup.availableCount === "number" ? panel.setup.availableCount + " commands ready on this machine. Try “change my theme” or “open files”." : "Find a command, then review it before Run."; wrapMode: Text.Wrap; color: Color.foreground; font.family: Style.font.family; font.pixelSize: Style.font.bodySmall; lineHeight: 1.2 }
                            Action { text: "Browse commands"; onClicked: panel.commandsRequested() }
                        }
                    }
                    Ui.BorderSurface {
                        width: parent.width; height: roomPath.implicitHeight + 24
                        radius: Style.cornerRadius; color: Qt.alpha(Color.accent, 0.05)
                        Column {
                            id: roomPath; x: 12; y: 12; width: parent.width - 24; spacing: 6
                            Text { width: parent.width; text: "2 · Meet Wisp"; color: Color.accent; font.family: Style.font.family; font.pixelSize: Style.font.body; font.bold: true }
                            Text { width: parent.width; text: "Visit the room, choose an activity, or leave a small note."; wrapMode: Text.Wrap; color: Color.foreground; font.family: Style.font.family; font.pixelSize: Style.font.bodySmall; lineHeight: 1.2 }
                            Action { text: "Open Wisp’s room"; onClicked: panel.roomRequested() }
                        }
                    }
                    Ui.BorderSurface {
                        width: parent.width; height: privacyPath.implicitHeight + 24
                        radius: Style.cornerRadius; color: Qt.alpha(Color.accent, 0.05)
                        Column {
                            id: privacyPath; x: 12; y: 12; width: parent.width - 24; spacing: 6
                            Text { width: parent.width; text: "3 · Choose your privacy"; color: Color.accent; font.family: Style.font.family; font.pixelSize: Style.font.body; font.bold: true }
                            Text { width: parent.width; text: "Awareness " + (panel.awarenessEnabled ? "on" : "off") + " · window titles " + (panel.titlesEnabled ? "on" : "off") + ". Review what Wisp can observe."; wrapMode: Text.Wrap; color: Color.foreground; font.family: Style.font.family; font.pixelSize: Style.font.bodySmall; lineHeight: 1.2 }
                            Action { text: "Review settings"; onClicked: panel.settingsRequested() }
                        }
                    }
                    Disclosure {
                        width: parent.width; title: "How Wisp works"
                        Text { width: guide.width - 8; text: "Local commands work without AI. Wisp shows the command or plan before Run; choosing an option only prepares it for review."; wrapMode: Text.Wrap; color: Color.foreground; font.family: Style.font.family; font.pixelSize: Style.font.bodySmall; lineHeight: 1.2 }
                        Text { width: guide.width - 8; text: "Chat and voice need optional local tools. Replies from the local model can be saved for repeat requests; Ask again refreshes one and Forget phrase removes it."; wrapMode: Text.Wrap; color: Color.foreground; font.family: Style.font.family; font.pixelSize: Style.font.bodySmall; lineHeight: 1.2 }
                        Text { width: guide.width - 8; text: "Finishing this introduction does not enable awareness or download a model."; wrapMode: Text.Wrap; color: Color.foreground; font.family: Style.font.family; font.pixelSize: Style.font.bodySmall; lineHeight: 1.2 }
                    }
                    Text { width: parent.width; visible: panel.error.length > 0; text: panel.error; textFormat: Text.PlainText; wrapMode: Text.Wrap; color: Color.accent; font.family: Style.font.family; font.pixelSize: Style.font.bodySmall }
                }
            }
            Flow {
                id: footer; width: parent.width; spacing: 6
                Action { text: panel.busy ? "One moment…" : "Finish setup"; enabled: !panel.busy; onClicked: panel.finishRequested() }
            }
        }
    }
}
