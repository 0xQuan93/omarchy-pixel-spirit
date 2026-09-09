import QtQuick
import QtQuick.Controls as Controls
import Quickshell
import Quickshell.Wayland
import qs.Commons
import qs.Ui as Ui
import "Forms.js" as Forms
PanelWindow {
    id: panel
    property var profile: ({name:"Wisp",seed:0,device:"portable",class:"Auto",interests:[],model:"qwen3.5:4b"})
    property var growth: ({born:Date.now()/1000,level:0,trait:"Maker",stage:"Spark",xp:0,next:24})
    property string family: "Maker"
    property string mood: "idle"
    property string detail: ""
    property bool busy: false
    property double now: Date.now()
    signal change(string setting,string value)
    signal nameSelf()
    signal closeRequested()
    signal screensaver()
    signal growthRequested()
    anchors {top:true;right:true}
    margins {top:45;right:24}
    implicitWidth:460;implicitHeight:Math.min(550,screen?screen.height-90:550)
    color:"transparent";exclusionMode:ExclusionMode.Ignore
    WlrLayershell.namespace:"pixel-spirit-identity";WlrLayershell.layer:WlrLayer.Overlay;WlrLayershell.keyboardFocus:WlrKeyboardFocus.OnDemand
    Timer {interval:60000;running:panel.visible;repeat:true;onTriggered:panel.now=Date.now()}
    Ui.BorderSurface {
        anchors.fill:parent;color:Color.popups.background;radius:Style.cornerRadius
        borderSpec:Border.surfaceSpec("popup","border",Color.popups.border,1)
        Column {
            anchors.fill:parent;anchors.margins:20;spacing:16
            Row {
                width:parent.width;spacing:10
                Spirit {width:90;height:82;active:panel.visible;trait:panel.family;stage:panel.growth.level;seed:panel.profile.seed;device:panel.profile.device;accent:Color.accent;foreground:Color.popups.text;background:Color.popups.background;mood:panel.mood}
                Column {width:parent.width-166;spacing:7
                    Text {width:parent.width;text:panel.profile.name;elide:Text.ElideRight;color:Color.accent;font.family:Style.font.family;font.pixelSize:Style.font.display}
                    Text {text:panel.growth.stage+" · "+panel.family;color:Color.foreground;font.family:Style.font.family;font.pixelSize:Style.font.body}
                    Text {text:Math.max(0,Math.floor((panel.now/1000-(panel.growth.born||panel.profile.created||panel.now/1000))/86400))+" days together";color:Color.foreground;opacity:0.6;font.family:Style.font.family;font.pixelSize:Style.font.bodySmall}
                }
                Action {text:"Close";onClicked:panel.closeRequested()}
            }
            Flickable {
                width:parent.width;height:parent.height-98;clip:true;contentHeight:body.implicitHeight
                boundsBehavior:Flickable.StopAtBounds;Controls.ScrollBar.vertical:Controls.ScrollBar {}
                Column {
                    id:body;width:parent.width-8;spacing:16
                    Row {spacing:8
                        Action {text:panel.growth.xp+(panel.growth.next?" / "+panel.growth.next:"")+" XP";onClicked:panel.growthRequested()}
                        Action {text:"Dream room";onClicked:panel.screensaver()}
                        Action {text:"Portrait";onClicked:panel.change("avatar","")}
                    }
                    Text {visible:panel.busy||!!panel.detail;width:parent.width;text:panel.busy?"Finding a name…":panel.detail;textFormat:Text.PlainText;wrapMode:Text.Wrap;color:Color.accent;font.family:Style.font.family;font.pixelSize:Style.font.bodySmall}
                    Disclosure {
                        width:parent.width;title:"Evolution path"
                        Row {spacing:4
                            Repeater {model:4
                                Column {required property int index;width:98;spacing:5
                                    Ui.BorderSurface {width:94;height:86;radius:Style.cornerRadius;color:Qt.alpha(Color.accent,index===panel.growth.level?0.12:0.035)
                                        Spirit {anchors.centerIn:parent;width:88;height:76;active:panel.visible;eco:true;stage:index;trait:panel.family;seed:panel.profile.seed;device:panel.profile.device;accent:Color.accent;foreground:Color.popups.text;background:Color.popups.background}
                                    }
                                    Text {width:94;text:Forms.names(panel.family)[parent.index];wrapMode:Text.Wrap;horizontalAlignment:Text.AlignHCenter;color:Color.foreground;font.family:Style.font.family;font.pixelSize:Style.font.caption}
                                    Text {text:["0 XP","24 XP","80 XP","180 XP"][parent.index];color:Color.accent;font.family:Style.font.family;font.pixelSize:Style.font.caption;anchors.horizontalCenter:parent.horizontalCenter}
                                }
                            }
                        }
                    }
                    Disclosure {
                        width:parent.width;title:"Name and influences"
                        Row {spacing:6
                            Controls.TextField {id:nameField;width:205;placeholderText:panel.profile.name;color:Color.foreground;selectByMouse:true;maximumLength:24;background:Ui.BorderSurface{color:Qt.alpha(Color.accent,0.05);borderSpec:Border.surfaceSpec("popup","border",Color.popups.border,1)}
                            onAccepted:panel.change("rename",text)}
                            Action {text:"Rename";enabled:!panel.busy;onClicked:panel.change("rename",nameField.text)}
                            Action {text:"Name me";enabled:!panel.busy;onClicked:panel.nameSelf()}
                        }
                        Flow {width:body.width;spacing:4
                            Repeater {model:["Auto","Maker","Artist","Musician","Archivist"];Action {required property string modelData;text:modelData;selected:panel.profile.class===modelData;onClicked:panel.change("class",modelData)}}
                        }
                        Text {width:body.width;text:"Auto follows our shared activity. Choose extra influences below.";wrapMode:Text.Wrap;color:Color.foreground;opacity:0.6;font.family:Style.font.family;font.pixelSize:Style.font.bodySmall}
                        Flow {width:body.width;spacing:4
                            Repeater {model:["Maker","Artist","Musician","Archivist"];Action {required property string modelData;text:modelData;selected:panel.profile.interests.indexOf(modelData)>=0;onClicked:panel.change("interest",modelData)}}
                        }
                    }
                    Disclosure {
                        width:parent.width;title:"Local model"
                        Text {width:body.width;text:panel.profile.model;color:Color.foreground;font.family:Style.font.family;font.pixelSize:Style.font.body}
                        Row {spacing:6
                            Controls.TextField {id:modelField;width:300;placeholderText:"Installed model name";color:Color.foreground;selectByMouse:true;background:Ui.BorderSurface{color:Qt.alpha(Color.accent,0.05);borderSpec:Border.surfaceSpec("popup","border",Color.popups.border,1)}}
                            Action {text:"Set";onClicked:panel.change("model",modelField.text)}
                        }
                    }
                }
            }
        }
    }
}
