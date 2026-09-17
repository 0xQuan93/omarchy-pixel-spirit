import QtQuick
import QtQuick.Controls as Controls
import Quickshell
import Quickshell.Wayland
import qs.Commons
import qs.Ui as Ui

PanelWindow {
    id: panel
    property var setup: ({})
    property bool busy: false
    property string error: ""
    signal finishRequested()
    signal closeRequested()
    signal commandsRequested()
    signal settingsRequested()
    anchors { top: true; right: true }
    margins { top: 45; right: 24 }
    implicitWidth: 480
    implicitHeight: Math.min(610, screen ? screen.height - 90 : 610)
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
                    Text { width: parent.width; text: panel.setup.text || "Everyday desktop help, right here."; textFormat: Text.PlainText; wrapMode: Text.Wrap; color: Color.foreground; font.family: Style.font.family; font.pixelSize: Style.font.body }
                    Text { width: parent.width; text: "Local commands work without AI. Try “change my theme”, “open files” or “turn the volume down”."; wrapMode: Text.Wrap; color: Color.foreground; font.family: Style.font.family; font.pixelSize: Style.font.bodySmall; lineHeight: 1.2 }
                    Ui.BorderSurface {
                        width: parent.width; height: discovery.implicitHeight + 24
                        radius: Style.cornerRadius; color: Qt.alpha(Color.accent, 0.05)
                        Column {
                            id: discovery; x: 12; y: 12; width: parent.width - 24; spacing: 8
                            Text { width: parent.width; text: typeof panel.setup.availableCount === "number" ? panel.setup.availableCount + " commands ready on this machine" : "Checking your command bank…"; wrapMode: Text.Wrap; color: Color.accent; font.family: Style.font.family; font.pixelSize: Style.font.body }
                            Text { width: parent.width; visible: typeof panel.setup.unavailableCount === "number" && panel.setup.unavailableCount > 0; text: panel.setup.unavailableCount + " more need an app or service. Commands explains what is missing."; wrapMode: Text.Wrap; color: Color.foreground; opacity: 0.7; font.family: Style.font.family; font.pixelSize: Style.font.bodySmall }
                            Text { width: parent.width; text: "Wisp discovers installed themes and supported plugin controls from local metadata."; wrapMode: Text.Wrap; color: Color.foreground; font.family: Style.font.family; font.pixelSize: Style.font.bodySmall }
                            Repeater {
                                model: Array.isArray(panel.setup.sources) ? panel.setup.sources.slice(0, 12) : []
                                Text { required property var modelData; width: discovery.width; text: modelData.name + " · " + modelData.count; textFormat: Text.PlainText; wrapMode: Text.Wrap; color: Color.foreground; opacity: 0.65; font.family: Style.font.family; font.pixelSize: Style.font.caption }
                            }
                        }
                    }
                    Text { width: parent.width; text: "Review before Run"; color: Color.accent; font.family: Style.font.family; font.pixelSize: Style.font.body }
                    Text { width: parent.width; text: "Command choices and multi-step plans show what will happen before you run them. A plan lists each step in order. During a plan, you can ask it to stop after the current step."; wrapMode: Text.Wrap; color: Color.foreground; font.family: Style.font.family; font.pixelSize: Style.font.bodySmall; lineHeight: 1.2 }
                    Text { width: parent.width; text: "Choose what Wisp can observe"; color: Color.accent; font.family: Style.font.family; font.pixelSize: Style.font.body }
                    Text { width: parent.width; text: "Activity awareness and window titles are controlled in Settings. Finishing this introduction does not enable them or download a model. Chat and voice need their own local tools."; wrapMode: Text.Wrap; color: Color.foreground; font.family: Style.font.family; font.pixelSize: Style.font.bodySmall; lineHeight: 1.2 }
                    Text { width: parent.width; visible: panel.error.length > 0; text: panel.error; textFormat: Text.PlainText; wrapMode: Text.Wrap; color: Color.accent; font.family: Style.font.family; font.pixelSize: Style.font.bodySmall }
                }
            }
            Flow {
                id: footer; width: parent.width; spacing: 6
                Action { text: panel.busy ? "One moment…" : "Finish setup"; enabled: !panel.busy; onClicked: panel.finishRequested() }
                Action { text: "Explore commands"; onClicked: panel.commandsRequested() }
                Action { text: "Settings"; onClicked: panel.settingsRequested() }
            }
        }
    }
}
