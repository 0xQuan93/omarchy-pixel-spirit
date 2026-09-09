import QtQuick
import qs.Commons
import qs.Ui as Ui
Ui.Button {
    focusable: true
    fontSize: Style.font.body
    horizontalPadding: 10
    verticalPadding: 6
    opacity: enabled ? 1 : 0.4
}
