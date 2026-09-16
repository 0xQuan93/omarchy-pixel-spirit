import QtQuick
import QtQuick.Controls as Controls
import qs.Commons
import qs.Ui as Ui

FocusScope {
    id: root
    property var tools: []
    property bool busy: false
    property alias query: search.text
    property string category: "All commands"
    property bool availableOnly: false
    signal propose(string action, string label)
    signal closeRequested()

    readonly property var categories: {
        var names = {};
        for (var i = 0; i < tools.length; i++) names[tools[i].group || "Other"] = true;
        return ["All commands"].concat(Object.keys(names).sort());
    }
    readonly property var filtered: {
        var words = search.text.toLowerCase().trim().split(/\s+/).filter(function(s) { return s.length > 0; });
        return tools.filter(function(t) {
            if (root.availableOnly && !t.available) return false;
            if (root.category !== "All commands" && (t.group || "Other") !== root.category) return false;
            var haystack = [t.label || "", t.description || "", t.group || "", (t.examples || []).join(" ")].join(" ").toLowerCase();
            return words.every(function(word) { return haystack.indexOf(word) !== -1; });
        });
    }
    function focusSearch() { search.forceActiveFocus(); }
    function prepare(tool) {
        if (tool && tool.available && !root.busy) root.propose(tool.id, tool.label);
    }
    function resetFilters() {
        search.text = "";
        category = "All commands";
        availableOnly = false;
        focusSearch();
    }
    onFilteredChanged: commands.currentIndex = filtered.length ? 0 : -1
    Keys.onEscapePressed: {
        if (search.text.length) search.text = "";
        else root.closeRequested();
    }
    Keys.onPressed: function(event) {
        if ((event.modifiers & Qt.ControlModifier) && event.key === Qt.Key_F) {
            focusSearch();
            event.accepted = true;
        }
    }

    Column {
        id: heading
        width: parent.width
        spacing: 10
        Text {
            text: "A little help, right here."
            width: parent.width
            color: Color.foreground
            font.family: Style.font.family
            font.pixelSize: Style.font.title
            wrapMode: Text.Wrap
        }
        Text {
            width: parent.width
            text: "Find a command or try its example in chat. Choose one, then confirm with Run."
            color: Color.foreground
            opacity: 0.7
            font.family: Style.font.family
            font.pixelSize: Style.font.bodySmall
            wrapMode: Text.Wrap
        }
        Row {
            width: parent.width
            spacing: 6
            Ui.TextField {
                id: search
                width: parent.width - clearSearch.width - parent.spacing
                placeholderText: "Search themes, sound, screenshots…"
                Accessible.name: "Search commands and example phrases"
                selectByMouse: true
                onAccepted: root.prepare(root.filtered[commands.currentIndex])
                Keys.onDownPressed: {
                    if (commands.count) {
                        commands.currentIndex = 0;
                        commands.forceActiveFocus();
                    }
                }
            }
            Action {
                id: clearSearch
                text: "Clear"
                enabled: search.text.length > 0
                tooltipText: "Clear search"
                onClicked: { search.text = ""; root.focusSearch(); }
            }
        }
        Row {
            width: parent.width
            spacing: 8
            Ui.Dropdown {
                width: parent.width - availability.width - parent.spacing
                options: root.categories
                value: root.category
                showLabel: false
                label: "Command category"
                onChanged: function(value) { root.category = value; }
            }
            Action {
                id: availability
                text: root.availableOnly ? "Ready only" : "All availability"
                selected: root.availableOnly
                tooltipText: "Filter to commands with their required tools installed"
                onClicked: root.availableOnly = !root.availableOnly
            }
        }
        Text {
            width: parent.width
            text: root.filtered.length + (root.filtered.length === 1 ? " command" : " commands") + " · " + root.tools.length + " in your bank"
            color: Color.foreground
            opacity: 0.55
            font.family: Style.font.family
            font.pixelSize: Style.font.caption
        }
    }

    ListView {
        id: commands
        anchors { top: heading.bottom; topMargin: 12; bottom: footer.top; bottomMargin: 8; left: parent.left; right: parent.right }
        clip: true
        spacing: 8
        model: root.filtered
        boundsBehavior: Flickable.StopAtBounds
        keyNavigationEnabled: true
        highlightMoveDuration: 0
        activeFocusOnTab: true
        cacheBuffer: 160
        Controls.ScrollBar.vertical: Controls.ScrollBar {}
        Keys.onReturnPressed: root.prepare(root.filtered[currentIndex])
        Keys.onEnterPressed: root.prepare(root.filtered[currentIndex])
        Keys.onSpacePressed: root.prepare(root.filtered[currentIndex])
        delegate: Controls.AbstractButton {
            id: card
            required property var modelData
            required property int index
            width: commands.width - 10
            implicitHeight: content.implicitHeight + 24
            padding: 12
            hoverEnabled: true
            activeFocusOnTab: true
            Accessible.name: modelData.label + (modelData.available ? ", prepare command" : ", unavailable")
            Accessible.description: modelData.description || ""
            onClicked: { commands.currentIndex = index; root.prepare(modelData); }
            background: Ui.BorderSurface {
                radius: Style.cornerRadius
                color: Qt.alpha(Color.accent, card.hovered || card.activeFocus || (commands.activeFocus && commands.currentIndex === card.index) ? 0.12 : 0.035)
                borderSpec: Border.controlSpec(card.activeFocus || (commands.activeFocus && commands.currentIndex === card.index) ? "focus" : card.hovered ? "hover-cursor" : "normal", Color.foreground, Color.accent)
            }
            contentItem: Column {
                id: content
                spacing: 6
                Row {
                    width: parent.width
                    spacing: 8
                    Text {
                        width: parent.width - status.width - parent.spacing
                        text: card.modelData.label
                        textFormat: Text.PlainText
                        wrapMode: Text.Wrap
                        color: Color.foreground
                        font.family: Style.font.family
                        font.pixelSize: Style.font.body
                        font.bold: true
                    }
                    Text {
                        id: status
                        text: card.modelData.available ? "Prepare ›" : "Unavailable"
                        color: card.modelData.available ? Color.accent : Color.foreground
                        opacity: card.modelData.available ? 1 : 0.55
                        font.family: Style.font.family
                        font.pixelSize: Style.font.caption
                    }
                }
                Text {
                    width: parent.width
                    text: card.modelData.description || card.modelData.group || "Desktop command"
                    textFormat: Text.PlainText
                    wrapMode: Text.Wrap
                    color: Color.foreground
                    opacity: 0.65
                    font.family: Style.font.family
                    font.pixelSize: Style.font.bodySmall
                }
                Text {
                    width: parent.width
                    visible: !!(card.modelData.examples && card.modelData.examples.length)
                    text: visible ? "Try: “" + card.modelData.examples[0] + "”" : ""
                    textFormat: Text.PlainText
                    wrapMode: Text.Wrap
                    color: Color.accent
                    font.family: Style.font.family
                    font.pixelSize: Style.font.bodySmall
                }
                Text {
                    width: parent.width
                    visible: !card.modelData.available
                    text: "Needs " + (card.modelData.requires || "an available desktop service")
                    textFormat: Text.PlainText
                    wrapMode: Text.Wrap
                    color: Color.foreground
                    opacity: 0.65
                    font.family: Style.font.family
                    font.pixelSize: Style.font.caption
                }
            }
        }
        Column {
            anchors { left: parent.left; right: parent.right; top: parent.top; topMargin: 24 }
            visible: commands.count === 0
            spacing: 12
            Text {
                width: parent.width
                text: root.tools.length ? "No commands match these filters." : "Your command bank is getting ready."
                wrapMode: Text.Wrap
                color: Color.foreground
                font.family: Style.font.family
                font.pixelSize: Style.font.body
            }
            Text {
                width: parent.width
                text: root.tools.length ? "Try a shorter search such as theme, volume or window." : "Open Commands again in a moment to see what is available."
                wrapMode: Text.Wrap
                color: Color.foreground
                opacity: 0.65
                font.family: Style.font.family
                font.pixelSize: Style.font.bodySmall
            }
            Action { visible: root.tools.length > 0; text: "Reset filters"; onClicked: root.resetFilters() }
        }
    }
    Text {
        id: footer
        anchors { left: parent.left; right: parent.right; bottom: parent.bottom }
        text: root.busy ? "Finishing the current request…" : "Ctrl+F to search · ↑↓ to browse · Enter to prepare"
        wrapMode: Text.Wrap
        color: Color.foreground
        opacity: 0.5
        font.family: Style.font.family
        font.pixelSize: Style.font.caption
    }
}
