import QtQuick
import Quickshell
import Quickshell.Io
Item {
    id: root
    property bool busy: proc.running
    signal received(var data)
    function run(args) {
        if (proc.running) return
        proc.command = ["python3", "-B", Qt.resolvedUrl("brain.py").toString().replace("file://", "")].concat(args)
        proc.running = true
    }
    Process {
        id: proc
        stdout: StdioCollector {
            onStreamFinished: {
                try { root.received(JSON.parse(text)) }
                catch(e) { root.received({error:"Wisp could not complete that. Try again."}) }
            }
        }
    }
}
