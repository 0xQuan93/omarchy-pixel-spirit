import QtQuick
import qs.Ui
BarWidget {
    id: root
    moduleName: "oxquan.pixel-spirit"
    implicitWidth: button.implicitWidth
    implicitHeight: button.implicitHeight
    WidgetButton {
        id: button; anchors.fill:parent; bar:root.bar; text:"󰚩"
        tooltipText:"Wisp · show / chat with your local pixel companion"
        onPressed: if(root.bar) root.bar.run("omarchy shell pixel-spirit toggle")
    }
}
