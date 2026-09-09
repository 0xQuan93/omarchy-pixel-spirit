import QtQuick
import "Forms.js" as Forms
Item {
    id: root
    property string mood: "idle"
    property int stage: 0
    property string trait: "Maker"
    property int seed: 0
    property string device: "portable"
    property color accent: "#86efac"
    property color foreground: "#dcece6"
    property color background: "#101817"
    property bool eco: false
    property bool active: true
    property int tick: 0
    onMoodChanged:art.requestPaint()
    onStageChanged:art.requestPaint()
    onTraitChanged:art.requestPaint()
    onAccentChanged:art.requestPaint()
    Timer {interval:root.eco?250:80;running:root.active;repeat:true;onTriggered:{root.tick++;art.requestPaint()}}
    Canvas {
        id:art;anchors.fill:parent
        onPaint: {
            var c=getContext("2d");c.reset();c.scale(width/128,height/110)
            var t=root.tick,level=Math.max(0,Math.min(3,root.stage)),a=root.accent.toString(),f=root.foreground.toString(),b=root.background.toString()
            var sleeping=root.mood==="sleeping",busy=root.mood==="thinking"||root.mood==="working"
            var pulse=0.5+Math.sin(t/(busy?2:9))*0.16
            c.strokeStyle=a;c.lineWidth=root.mood==="working"?2:1;c.globalAlpha=sleeping?0.22:pulse
            c.beginPath();c.ellipse(12,85,104,18);c.stroke()
            var count=root.mood==="reading"?4:root.mood==="playing"?16:12
            for(var i=0;i<count;i++) {
                var angle=(i/count)*Math.PI*2+(sleeping?0:t*(busy?0.15:0.035))
                var x=63+Math.cos(angle)*50,y=94+Math.sin(angle)*8
                c.globalAlpha=sleeping?0.18:root.mood==="reading"?(i%2?0.25:0.95):0.3+(Math.sin(angle)+1)*0.3
                c.fillStyle=root.mood==="happy"?f:a
                var size=root.mood==="playing"?3+Math.sin(t/3+i)*1.4:3
                c.fillRect(x,y,size,root.mood==="working"?5:size)
            }
            if(root.mood==="thinking"){c.globalAlpha=0.6;c.beginPath();c.ellipse(19,80,90,26);c.stroke()}
            var rows=Forms.rows(root.trait,level),px=4,ox=64-rows[0].length*px/2,oy=14+(root.eco?0:Math.round(Math.sin(t/8)*2))
            c.fillStyle=a
            for(var yy=0;yy<rows.length;yy++)for(var xx=0;xx<rows[yy].length;xx++)if(rows[yy][xx]!=='0'){
                c.globalAlpha=rows[yy][xx]==='2'?0.38:0.88
                c.fillRect(ox+xx*px,oy+yy*px,3.8,3.8)
            }
            // Stable per-install constellation: individual markings, never a hardware ID.
            c.fillStyle=f;c.globalAlpha=0.55
            for(var mark=0;mark<3;mark++)c.fillRect(49+((root.seed>>(mark*3))%7)*4,oy+8+(mark%2)*4,3,2)
            c.fillStyle=b;c.globalAlpha=1
            var eyeY=oy+28, eyeH=sleeping||t%71>68?2:6
            c.fillRect(49,eyeY,7,eyeH);c.fillRect(72,eyeY,7,eyeH)
            if(root.mood==="happy") {c.fillRect(59,eyeY+12,10,3);c.fillRect(57,eyeY+9,3,3);c.fillRect(69,eyeY+9,3,3)}
            else c.fillRect(61,eyeY+12,6,2)
            // Portable devices grow folding fins; stationary machines get stabilizers.
            if(level>0){c.fillStyle=f;c.globalAlpha=0.6;if(root.device==="portable"){c.fillRect(26,oy+40,8,3);c.fillRect(94,oy+40,8,3)}else{c.fillRect(42,oy+61,12,4);c.fillRect(74,oy+61,12,4)}}
            if(root.mood==="happy"){c.fillStyle=f;c.font="12px sans-serif";c.globalAlpha=0.8;for(var h=0;h<3;h++)c.fillText("♥",22+h*38,16-(t+h*4)%12)}
        }
    }
}
