import QtQuick
import Quickshell
import Quickshell.Io
Item {
    id: root
    property bool busy: proc.running
    property string pendingFrame: ""
    signal received(var data)
    function run(args) {
        if (proc.running) return
        // ASCII JSON gives an exact byte count, including escaped Unicode.
        var frame = JSON.stringify(args).replace(/[\u007f-\uffff]/g, function(c) {
            return "\\u" + ("0000" + c.charCodeAt(0).toString(16)).slice(-4)
        }) + "\n"
        if (frame.length > 65536) {
            root.received({error: "Wisp request is too large. Please shorten it."})
            return
        }
        pendingFrame = frame
        proc.command = ["python3", "-B", Qt.resolvedUrl("brain.py").toString().replace("file://", "")]
        proc.stdinEnabled = true
        proc.running = true
    }
    Process {
        id: proc
        onStarted: {
            write(root.pendingFrame)
            root.pendingFrame = ""
            stdinEnabled = false
        }
        onExited: root.pendingFrame = ""
        stdout: StdioCollector {
            onStreamFinished: {
                try { root.received(JSON.parse(text)) }
                catch(e) { root.received({error:"Wisp could not complete that. Try again."}) }
            }
        }
    }
}
