//@ pragma AppId org.omarchy.screensaver
import QtQuick
import Quickshell
import Quickshell.Io
import Quickshell.Services.UPower
ShellRoot {
    id: root
    property var snapshot: ({profile:{name:"Wisp",seed:0,device:"portable"},growth:{level:0,trait:"Maker"},room:{bond:0,notes:[],activity:"rest"},palette:{accent:"#86efac",foreground:"#dcece6",background:"#101817"},appearance:{family:"Maker"}})
    property bool stateReady:false
    property string restoreError:""
    property int moment:0
    property bool armed:false
    property bool eco:UPower.onBattery || PowerProfiles.profile===PowerProfile.PowerSaver
    Call {id:load;Component.onCompleted:run(["dream_snapshot"]);onReceived:function(d){if(d.error)root.restoreError=d.error;else{root.snapshot=d;root.stateReady=true;root.restoreError=""}}}
    Timer {interval:10000;running:!root.stateReady && !load.busy;repeat:true;onTriggered:load.run(["dream_snapshot"])}
    FileView {path:(Quickshell.env("XDG_STATE_HOME")||Quickshell.env("HOME")+"/.local/state")+"/omarchy/current/theme/colors.toml";watchChanges:true;onFileChanged:load.run(["dream_snapshot"])}
    Timer {interval:1200;running:true;onTriggered:root.armed=true}
    Timer {interval:45000;running:true;repeat:true;onTriggered:root.moment++}
    IpcHandler {target:"wisp-dream";function close():void{Qt.quit()}}
    Variants {model:Quickshell.screens
        FloatingWindow {
            required property var modelData
            screen:modelData;visible:true;fullscreen:true;title:"Wisp dream room"
            color:root.snapshot.palette.background
            Item {anchors.fill:parent;focus:true;Keys.onPressed:function(event){event.accepted=true;Qt.quit()}
                Rectangle {anchors.fill:parent;gradient:Gradient{GradientStop{position:0;color:Qt.darker(root.snapshot.palette.background,1.2)}GradientStop{position:1;color:root.snapshot.palette.background}}}
                Column {anchors.centerIn:parent;spacing:28
                    Text {anchors.horizontalCenter:parent.horizontalCenter;text:root.snapshot.profile.name+" / dream room";color:root.snapshot.palette.foreground;opacity:0.5;font.pixelSize:17;font.letterSpacing:3}
                    RoomScene {visible:root.stateReady;
                        width:Math.min(modelData.width*0.74,1100);height:width*360/640
                        profile:root.snapshot.profile;growth:root.snapshot.growth;family:root.snapshot.appearance.family
                        roomState:Object.assign({},root.snapshot.room,{activity:["rest","read","garden","play"][root.moment%4]})
                        accent:root.snapshot.palette.accent;foreground:root.snapshot.palette.foreground;background:root.snapshot.palette.background;eco:root.eco
                    }
                    Text {anchors.horizontalCenter:parent.horizontalCenter;text:root.stateReady?"a small world, growing with yours":(root.restoreError||"Restoring your saved companion…");color:root.snapshot.palette.accent;opacity:0.35;font.pixelSize:13;font.letterSpacing:2}
                }
                MouseArea {anchors.fill:parent;hoverEnabled:true;cursorShape:Qt.BlankCursor;onPressed:Qt.quit();onPositionChanged:if(root.armed)Qt.quit();onWheel:Qt.quit()}
            }
            onClosed:Qt.quit()
        }
    }
}
