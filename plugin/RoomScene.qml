import QtQuick
Item {
    id: scene
    property color accent: "#86efac"
    property color foreground: "#ddeee5"
    property color background: "#101817"
    property var profile: ({name:"Wisp",seed:0,device:"portable"})
    property var growth: ({level:0,trait:"Maker"})
    property var roomState: ({bond:0,activity:"rest",notes:[]})
    property string family: "Maker"
    property bool active: true
    property bool eco: false
    property bool interactive: false
    onAccentChanged:waveform.requestPaint()
    property int caught: 0
    signal caughtFireflies()
    Item {
        width:640;height:360;scale:Math.min(scene.width/640,scene.height/360);transformOrigin:Item.TopLeft
        Rectangle {anchors.fill:parent;radius:12;color:scene.background;border.color:Qt.alpha(scene.accent,0.28)}
        Rectangle {x:1;y:1;width:638;height:240;radius:12;gradient:Gradient{GradientStop{position:0;color:Qt.alpha(scene.accent,0.14)}GradientStop{position:1;color:Qt.alpha(scene.accent,0.015)}}}
        Repeater {model:9;Rectangle {required property int index;x:index*80;y:239;width:1;height:120;color:Qt.alpha(scene.accent,0.10)}}
        Repeater {model:5;Rectangle {required property int index;x:0;y:240+index*28;width:640;height:1;color:Qt.alpha(scene.accent,0.13)}}
        Rectangle {x:40;y:28;width:188;height:168;radius:60;color:Qt.alpha(scene.accent,0.06);border.width:2;border.color:Qt.alpha(scene.accent,0.6)
            Rectangle {x:92;y:0;width:2;height:168;color:Qt.alpha(scene.accent,0.5)}
            Rectangle {x:0;y:82;width:188;height:2;color:Qt.alpha(scene.accent,0.5)}
            Rectangle {x:120;y:25;width:29;height:29;radius:15;color:scene.foreground;opacity:0.6}
            Repeater {model:14;Rectangle{required property int index;x:12+(index*41)%160;y:12+(index*31)%140;width:2;height:2;color:scene.accent;opacity:0.3+(index%4)/6}}
        }
        Rectangle {x:330;y:52;width:239;height:113;radius:7;color:Qt.alpha(scene.accent,0.035);border.color:Qt.alpha(scene.accent,0.16)
            Canvas {id:waveform;anchors.fill:parent;onPaint:{var c=getContext('2d');c.clearRect(0,0,width,height);c.strokeStyle=scene.accent.toString();c.globalAlpha=0.4;c.beginPath();for(var x=12;x<width-12;x++){var y=height/2+Math.sin(x/18)*Math.sin(x/61)*28;if(x===12)c.moveTo(x,y);else c.lineTo(x,y)}c.stroke()}}
        }
        Rectangle {x:384;y:199;width:198;height:9;color:Qt.alpha(scene.accent,0.55)}
        Repeater {model:Math.min(9,scene.roomState.notes.length+2);Rectangle {required property int index;x:401+index*17;y:164-index%3*7;width:11;height:35+index%3*7;color:Qt.alpha(scene.accent,0.35+index%4*0.12)}}
        Rectangle {x:51;y:272;width:155;height:35;radius:18;color:Qt.alpha(scene.accent,0.16);border.color:Qt.alpha(scene.accent,0.4)}
        Rectangle {x:66;y:268;width:125;height:22;radius:11;color:Qt.alpha(scene.accent,0.10)}
        Item {visible:scene.roomState.bond>=3;x:512;y:246
            Rectangle{x:0;y:33;width:36;height:30;radius:4;color:Qt.alpha(scene.accent,0.4)}
            Rectangle{x:16;y:0;width:4;height:39;color:scene.accent}
            Repeater {model:4;Rectangle{required property int index;x:index%2?19:0;y:3+index*7;width:19;height:8;radius:4;rotation:index%2?-25:25;color:Qt.alpha(scene.accent,0.8)}}
        }
        Item {visible:scene.roomState.bond>=8;x:279;y:220
            Rectangle {x:14;y:18;width:3;height:52;color:scene.accent}
            Rectangle {x:0;y:0;width:32;height:23;radius:8;color:Qt.alpha(scene.accent,0.5)}
            Rectangle {x:4;y:69;width:25;height:3;color:scene.accent}
        }
        Text {visible:scene.roomState.bond>=16;x:445;y:18;text:"♛";font.pixelSize:24;color:scene.accent}
        Spirit {
            x:scene.roomState.activity==="rest"?62:scene.roomState.activity==="read"?395:scene.roomState.activity==="garden"?414:259
            y:scene.roomState.activity==="rest"?168:scene.roomState.activity==="read"?98:180
            width:132;height:114;active:scene.active;eco:scene.eco;stage:scene.growth.level;trait:scene.family;seed:scene.profile.seed;device:scene.profile.device
            accent:scene.accent;foreground:scene.foreground;background:scene.background
            mood:({rest:"sleeping",read:"reading",play:"playing",garden:"happy"})[scene.roomState.activity]||"idle"
            Behavior on x {NumberAnimation{duration:1200;easing.type:Easing.InOutCubic}}
            Behavior on y {NumberAnimation{duration:1200;easing.type:Easing.InOutCubic}}
        }
        Repeater {model:3
            Rectangle {required property int index;property int hop:0;x:260+(index*71+hop*37)%95;y:35+(index*31+hop*17)%112;width:18;height:18;radius:9;color:Qt.alpha(scene.accent,0.12);border.color:Qt.alpha(scene.accent,0.7)
                Rectangle{anchors.centerIn:parent;width:4;height:4;rotation:45;color:scene.accent}
                MouseArea{anchors.fill:parent;enabled:scene.interactive;cursorShape:Qt.PointingHandCursor;onClicked:{parent.hop++;scene.caught++;if(scene.caught>=3){scene.caught=0;scene.caughtFireflies()}}}
            }
        }
    }
}
