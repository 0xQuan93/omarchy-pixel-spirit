import QtQuick
import QtQuick.Controls as Controls
import Quickshell
import Quickshell.Wayland
import qs.Commons
import "Forms.js" as Forms
PanelWindow {
    id: panel
    property var profile: ({name:"Wisp",seed:0,device:"portable",class:"Auto",interests:[],model:"qwen3.5:4b"})
    property var growth: ({born:Date.now()/1000,level:0,trait:"Maker",stage:"Spark"})
    property string family: "Maker"
    property string mood: "idle"
    property string detail: ""
    property bool busy: false
    property double now: Date.now()
    signal change(string setting,string value)
    signal nameSelf()
    signal closeRequested()
    signal screensaver()
    anchors {top:true;right:true}
    margins {top:45;right:24}
    implicitWidth:430;implicitHeight:620;color:"transparent";exclusionMode:ExclusionMode.Ignore
    WlrLayershell.namespace:"pixel-spirit-identity";WlrLayershell.layer:WlrLayer.Overlay;WlrLayershell.keyboardFocus:WlrKeyboardFocus.OnDemand
    Timer {interval:60000;running:panel.visible;repeat:true;onTriggered:panel.now=Date.now()}
    Rectangle {anchors.fill:parent;radius:18;color:Color.popups.background;border.color:Color.accent
        Column {anchors.fill:parent;anchors.margins:20;spacing:12
            Row {spacing:12
                Spirit {width:90;height:78;active:panel.visible;trait:panel.family;stage:panel.growth.level;seed:panel.profile.seed;device:panel.profile.device;accent:Color.accent;foreground:Color.popups.text;background:Color.popups.background;mood:panel.mood}
                Column {spacing:7;width:210
                    Text {text:panel.profile.name;color:Color.accent;font.bold:true;font.pixelSize:23}
                    Text {text:panel.growth.stage+" · "+({Maker:"Forgewright",Artist:"Prismweaver",Musician:"Resonant",Archivist:"Lorekeeper"})[panel.family];color:Color.popups.text;font.pixelSize:12}
                    Text {text:"Age "+Math.max(0,Math.floor((panel.now/1000-(panel.growth.born||panel.profile.created||panel.now/1000))/86400))+"d "+Math.max(0,Math.floor((panel.now/1000-(panel.growth.born||panel.profile.created||panel.now/1000))/3600)%24)+"h "+Math.max(0,Math.floor((panel.now/1000-(panel.growth.born||panel.profile.created||panel.now/1000))/60)%60)+"m · "+panel.mood;color:Color.popups.text;font.pixelSize:12}
                }
                Action {text:"×";onClicked:panel.closeRequested()}
            }
            Row {spacing:7
                Controls.TextField {background:Rectangle{radius:6;color:Qt.alpha(Color.accent,0.06);border.color:Color.popups.border} placeholderTextColor:Qt.alpha(Color.popups.text,0.45);id:nameField;width:210;placeholderText:panel.profile.name;color:Color.popups.text;selectByMouse:true;maximumLength:24;onAccepted:panel.change("rename",text)}
                Action {text:"Rename";enabled:!panel.busy;onClicked:panel.change("rename",nameField.text)}
                Action {text:"Name me";enabled:!panel.busy;onClicked:panel.nameSelf()}
            }
            Text {text:"EVOLUTION LINEAGE";color:Color.accent;font.pixelSize:10;font.letterSpacing:2}
            Flow {width:390;spacing:6
                Repeater {model:["Auto","Maker","Artist","Musician","Archivist"];Action {required property string modelData;text:(panel.profile.class===modelData?"● ":"")+modelData;onClicked:panel.change("class",modelData)}}
            }
            Text {width:390;text:"Auto blends observed work with the influences you choose below. Your unique markings stay with you.";wrapMode:Text.Wrap;color:Color.popups.text;font.pixelSize:11;opacity:0.7}
            Flow {width:390;spacing:6
                Repeater {model:["Maker","Artist","Musician","Archivist"];Action {required property string modelData;text:(panel.profile.interests.indexOf(modelData)>=0?"♥ ":"+ ")+modelData;onClicked:panel.change("interest",modelData)}}
            }
            Row {spacing:5
                Repeater {model:4
                    Column {required property int index;spacing:4
                        Rectangle {width:92;height:91;radius:8;color:Qt.alpha(Color.accent,index===panel.growth.level?0.17:0.04);border.color:Qt.alpha(Color.accent,0.2)
                            Spirit {anchors.centerIn:parent;width:88;height:76;active:panel.visible;eco:true;stage:index;trait:panel.family;seed:panel.profile.seed;device:panel.profile.device;accent:Color.accent;foreground:Color.popups.text;background:Color.popups.background}
                        }
                        Text {text:Forms.names(panel.family)[parent.index];color:Color.accent;font.pixelSize:10;anchors.horizontalCenter:parent.horizontalCenter}
                        Text {text:["0 XP","24 XP","80 XP","180 XP"][parent.index];color:Color.popups.text;font.pixelSize:10;anchors.horizontalCenter:parent.horizontalCenter}
                    }
                }
            }
            Text {text:"LOCAL MODEL";color:Color.accent;font.pixelSize:10;font.letterSpacing:2}
            Row {spacing:8
                Controls.TextField {background:Rectangle{radius:6;color:Qt.alpha(Color.accent,0.06);border.color:Color.popups.border} placeholderTextColor:Qt.alpha(Color.popups.text,0.45);id:modelField;width:285;placeholderText:panel.profile.model;color:Color.popups.text;selectByMouse:true}
                Action {text:"Set model";onClicked:panel.change("model",modelField.text)}
            }
            Row {spacing:8
                Action {text:"Preview dream room";onClicked:panel.screensaver()}
                Action {text:"Export portrait";onClicked:panel.change("avatar","")}
            }
            Text {width:390;text:panel.busy?"Listening for a name…":panel.detail;textFormat:Text.PlainText;wrapMode:Text.Wrap;maximumLineCount:3;elide:Text.ElideRight;color:Color.accent;font.pixelSize:11}
        }
    }
}
