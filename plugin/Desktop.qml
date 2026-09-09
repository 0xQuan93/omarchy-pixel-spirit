import QtQuick
import QtQuick.Controls as Controls
import Quickshell
import Quickshell.Io
import Quickshell.Wayland
import Quickshell.Hyprland
import Quickshell.Services.UPower
import qs.Commons
import qs.Ui as Ui
Item {
    id: root
    property bool stateReady: false
    property string restoreError: ""
    property bool hidden: false
    property string movement: "roam"
    property bool roomOpen: false
    property bool identityOpen: false
    property bool awarenessOpen: false
    property var awareness: ({settings:{enabled:false,titles:false,quiet_until:0},snapshot:{},minutes:{},events:[],reflections:[],error:""})
    property var tools: []
    property string awarenessDetail: ""
    property string asideText: ""
    property string asideBasis: ""
    property bool asideVisible: false
    property bool senseAllowed: stateReady && awareness.settings.enabled && !eco && !hidden && !dreaming && !presenceIdle.isIdle && motionClock>=awareness.settings.quiet_until*1000 && !busy && !choice.busy && !selfName.busy
    property bool commentAllowed: senseAllowed && !opened && !roomOpen && !identityOpen && !awarenessOpen && !speaker.busy && !pending
    onCommentAllowedChanged: if(!commentAllowed){reflection.cancel();asideVisible=false}
    IdleMonitor {id:presenceIdle;timeout:180;respectInhibitors:false}

    property var dreamWindows: ({})
    property bool dreaming: Object.keys(dreamWindows).length>0
    Connections {target:Hyprland;function onRawEvent(event){
        if(event.name==="activewindow" || event.name==="workspace") {reflection.cancel();root.asideVisible=false}
        if(event.name!=="openwindow" && event.name!=="closewindow")return
        var parts=event.parse?event.parse(event.name==="openwindow"?4:1):String(event.data).split(",")
        var next=Object.assign({},root.dreamWindows)
        if(event.name==="openwindow" && parts[2]==="org.omarchy.screensaver")next[parts[0]]=true
        if(event.name==="closewindow")delete next[parts[0]]
        root.dreamWindows=next
    }}
    property var profile: ({name:"Wisp",seed:0,device:"portable",class:"Auto",interests:[],model:"qwen3.5:4b"})
    property string profileDetail: "Your imprint is local, editable, and yours."
    property string family: {
        if(profile.class!=="Auto")return profile.class
        var scores=Object.assign({},growth.traits)
        for(var i=0;i<profile.interests.length;i++){var k=profile.interests[i];scores[k]=(scores[k]||0)+4}
        return Object.keys(scores).sort(function(a,b){return scores[b]-scores[a]})[0]||"Maker"
    }
    property var roomData: ({bond:0,notes:[],activity:"rest",earned:[],message:"Welcome home."})
    property real targetX: 24
    property real targetY: 70
    property int pats: 0
    property double pauseUntil: 0
    property double motionClock: Date.now()
    property bool wandering: stateReady && !hidden && !dreaming && !opened && !roomOpen && !identityOpen && !awarenessOpen && !busy && !dragArea.pressed && !dragArea.containsMouse && motionClock>pauseUntil && movement!=="stay"
    function roomEvent(action,value) {if(!stateReady)return;roomCall.run(["room",action,value])}
    function headPat() {pats++;patTimer.restart();if(pats>=3){pats=0;patTimer.stop();mood="happy";pauseUntil=Date.now()+5000;roomEvent("pat","");celebrate.restart()}}
    property bool opened: false
    property bool voice: false
    property int micSeconds: 0
    property real posX: 24
    property real posY: 70
    property string mood: "idle"
    property string displayMood:listener.busy?"reading":actor.busy?"working":brain.busy||choice.busy||selfName.busy?"thinking":speaker.busy?"playing":mood!=="idle"?mood:senseAllowed && motionClock-(awareness.sampled||0)*1000<90000?({Maker:"working",Artist:"playing",Musician:"playing",Archivist:"reading"})[awareness.snapshot.category]||"idle":"idle"
    property string reply: "Hey, I’m Wisp. A little signal in your machine.\n\nAsk me something, or try ‘turn the volume down’."
    property string pending: ""
    property var growth: ({stage:"Spark",level:0,trait:"Maker",xp:0,next:24,traits:{},journal:[]})
    property bool journalOpen: false
    property string growthError: ""
    property bool eco: UPower.onBattery || PowerProfiles.profile === PowerProfile.PowerSaver
    property bool busy: !stateReady || brain.busy || listener.busy || actor.busy
    function persist() { if(!stateReady)return; saver.run(["save", JSON.stringify({x:posX,y:posY,hidden:hidden,voice:voice,movement:movement})]) }
    function toggle() { hidden=false; opened=!opened; persist() }
    function send() {
        if (busy || !field.text.trim()) return
        journalOpen=false; pending=""; mood="thinking"; reply="Following that thought…"
        brain.run(["chat",field.text,eco?"eco":"normal"]); field.text=""
    }
    IpcHandler {
        target: "pixel-spirit"
        function toggle(): void { root.toggle() }
        function open(): void { root.hidden=false; root.opened=true; root.persist() }
        function ask(message: string): void { root.hidden=false; root.opened=true; field.text=message; root.send() }
        function show(): void { root.hidden=false; root.persist() }
        function hide(): void { root.hidden=true; root.opened=false; root.persist() }
        function reset(): void { root.posX=24; root.posY=70; root.hidden=false; root.persist() }
        function identity(): void {root.identityOpen=!root.identityOpen}
        function screensaver(): void {dream.running=true}
        function tools(): void {root.awarenessOpen=true;senses.showTools=true;toolCall.run(["tools"])}
        function awareness(): void {root.awarenessOpen=!root.awarenessOpen;senses.showTools=false;awarenessConfig.run(["awareness"])}
        function room(): void {root.roomOpen=!root.roomOpen}
        function roam(mode: string): void {if(["stay","roam","follow"].indexOf(mode)>=0){root.movement=mode;root.persist()}}
        function journal(): void {root.hidden=false;root.opened=true;root.journalOpen=true;growthCall.run(["growth"])}
        function status(): string { return JSON.stringify({hidden:root.hidden,mood:root.mood,eco:root.eco,busy:root.busy,movement:root.movement,room:root.roomOpen,ready:root.stateReady,error:root.restoreError,stage:root.stateReady?root.growth.stage:null,trait:root.stateReady?root.growth.trait:null,xp:root.stateReady?root.growth.xp:null,bond:root.stateReady?root.roomData.bond:null,awareness:root.awareness.settings.enabled,ambientBusy:reflection.busy,sampled:root.awareness.sampled||0}) }
    }
    Timer {interval:500;running:!root.hidden;repeat:true;onTriggered:root.motionClock=Date.now()}
    Timer {id:patTimer;interval:400;onTriggered:{root.pats=0;root.opened=!root.opened;root.persist()}}
    Timer {id:celebrate;interval:4000;onTriggered:if(!root.busy)root.mood="idle"}
    Call {id:profileCall;onReceived:function(d){if(d.error)root.profileDetail=d.error;else{root.profile=d;root.profileDetail=d.avatarPath?"Portrait saved: "+d.avatarPath:"Identity saved."}}}
    Call {id:selfName;onReceived:function(d){if(d.error)root.profileDetail=d.error;else{root.profile=d;root.profileDetail="I chose "+d.name+". You can rename me any time."}}}
    Process {id:dream;command:["quickshell","-n","-p",Qt.resolvedUrl("Screensaver.qml").toString().replace("file://","")]}
    IdentityPanel {visible:root.stateReady && root.identityOpen && !root.dreaming;profile:root.profile;growth:root.growth;family:root.family;mood:root.displayMood;busy:selfName.busy||profileCall.busy;detail:root.profileDetail
        onCloseRequested:root.identityOpen=false
        onChange:function(setting,value){profileCall.run(["identity",setting,value])}
        onNameSelf:selfName.run(["name_self",root.eco?"eco":"normal"])
        onScreensaver:{root.identityOpen=false;root.roomOpen=false;root.opened=false;dream.running=true}
    }
    Call {id:roomCall;onReceived:function(d){if(d.error){root.reply=d.error;root.roomData=Object.assign({},root.roomData,{message:d.error})}else root.roomData=d}}
    Call {id:choice;onReceived:function(d){if(d.error)root.roomData=Object.assign({},root.roomData,{message:d.error});else {root.roomData=d;root.mood=({rest:"sleeping",read:"reading",play:"playing",garden:"happy"})[d.activity]||"idle"}}}
    Timer {interval:root.eco?600000:180000;running:root.roomOpen && !root.busy && !choice.busy && !roomCall.busy;repeat:true;onTriggered:choice.run(["room_choose",root.eco?"eco":"normal","ambient"])}
    Room {visible:root.stateReady && root.roomOpen && !root.dreaming;profile:root.profile;family:root.family;roomState:root.roomData;growth:root.growth;eco:root.eco;busy:choice.busy||roomCall.busy;movement:root.movement
        onCloseRequested:root.roomOpen=false
        onInteract:function(action,value){root.roomEvent(action,value)}
        onChoose:choice.run(["room_choose",root.eco?"eco":"normal"])
        onMovementSelected:function(mode){root.movement=mode;root.pauseUntil=Date.now()+1000;root.persist()}
    }
    Timer {interval:root.eco?18000:9000;running:root.wandering && root.movement==="roam";repeat:true;triggeredOnStart:true;onTriggered:{root.targetX=24+Math.random()*Math.max(0,win.screen.width-176);root.targetY=40+Math.random()*Math.max(0,win.screen.height-200)}}
    Timer {interval:root.eco?100:33;running:root.wandering;repeat:true;onTriggered:{var dx=root.targetX-root.posX,dy=root.targetY-root.posY,dist=Math.sqrt(dx*dx+dy*dy);if(dist>3){var step=Math.min(dist,root.eco?5:4);root.posX+=dx/dist*step;root.posY+=dy/dist*step}}}
    Timer {interval:root.eco?1000:300;running:root.wandering && root.movement==="follow";repeat:true;triggeredOnStart:true;onTriggered:if(!cursorPoll.running)cursorPoll.running=true}
    Call { id: growthCall; onReceived: function(d) {if(d.error)root.growthError=d.error;else {root.growth=d;root.growthError=""}} }
    Timer { interval:root.eco?1800000:600000; running:!root.busy; repeat:true; onTriggered:growthCall.run(["growth"]) }
    Call { id: saver }
    Call {id:toolCall;onReceived:function(d){if(!d.error)root.tools=d.tools}}
    Call {id:awarenessConfig;onReceived:function(d){if(d.error)root.awarenessDetail=d.error;else{root.awareness=d;root.awarenessDetail=""}}}
    Call {id:observer;onReceived:function(d){
        if(d.error){root.awarenessDetail=d.error;return}
        root.awareness=d;if(d.growth)root.growth=d.growth;root.awarenessDetail=d.quiet||""
        if(d.due && root.commentAllowed && !reflection.busy)reflection.run(["reflect"])
    }}
    Call {id:reflection;onReceived:function(d){
        if(d.reflection && root.commentAllowed){root.asideText=d.reflection.text;root.asideBasis=d.reflection.basis;root.asideVisible=true;asideDismiss.restart();root.awareness=d.awareness}
        else if(d.quiet)root.awarenessDetail=d.quiet
    }}
    Timer {interval:60000;running:root.senseAllowed;repeat:true;triggeredOnStart:true;onTriggered:if(!observer.busy)observer.run(["observe"])}
    Timer {id:asideDismiss;interval:14000;onTriggered:root.asideVisible=false}
    AwarenessPanel {
        id:senses
        visible:root.awarenessOpen && root.stateReady && !root.dreaming
        state:root.awareness;tools:root.tools;busy:awarenessConfig.busy;pluggedIn:!root.eco;detail:root.awarenessDetail
        onCloseRequested:root.awarenessOpen=false
        onChange:function(setting,value){reflection.cancel();root.asideVisible=false;awarenessConfig.run(["awareness",setting,value])}
        onPropose:function(action,label){root.awarenessOpen=false;root.opened=true;root.pending=action;root.reply="Ready: "+label+". Tap Run below."}
    }

    Call {
        id: loader
        Component.onCompleted: run(["restore"])
        onReceived: function(d) {
            if (d.error) {root.restoreError=d.error;root.opened=true;return}
            root.profile=d.profile;root.roomData=d.room;root.growth=d.growth;root.awareness=d.awareness
            var p=d.position
            root.posX=Number.isFinite(p.x)?p.x:24;root.posY=Number.isFinite(p.y)?p.y:70
            root.hidden=!!p.hidden;root.voice=!!p.voice;root.movement=p.movement||"roam"
            root.targetX=root.posX;root.targetY=root.posY
            root.reply=d.recovered.length ? "Recovered saved progress from a backup ("+d.recovered.join(", ")+").\n\n"+d.reply : d.reply
            root.restoreError="";root.stateReady=true
            growthCall.run(["growth"]);toolCall.run(["tools"])
        }
    }
    Timer {interval:10000;running:!root.stateReady && !loader.busy;repeat:true;onTriggered:loader.run(["restore"])}
    Timer {id:reaction;interval:15000;onTriggered:if(!root.busy)root.mood="idle"}
    Call { id: brain; onReceived: function(d) { root.reply=d.error||d.text; root.mood=d.emote||"idle"; root.pending=d.action||"";reaction.restart(); if(root.voice && !d.error) speaker.run(["speak",d.text]) } }
    Call { id: actor; onReceived: function(d) { root.reply=d.error||d.text; root.mood=d.emote||"idle"; root.pending="";reaction.restart() } }
    Timer { interval:1000; running:listener.busy; repeat:true; onTriggered: { if(root.micSeconds>0)root.micSeconds--; if(root.micSeconds===0)root.reply="Transcribing your recording locally…" } }
    Call { id: listener; onReceived: function(d) { root.reply=d.error||d.text; root.mood=d.emote||"idle"; if(d.transcript) {field.text=d.transcript; field.forceActiveFocus()} } }
    Call { id: speaker; onReceived: function(d) { if(d.error) root.reply="Voice: "+d.error } }
    PanelWindow {
        id: win
        screen: Quickshell.screens[0]
        visible: !root.hidden && !root.dreaming
        anchors { top: true; left: true }
        margins.left: Math.max(0,Math.min(root.posX,(screen?screen.width:1920)-implicitWidth))
        margins.top: Math.max(0,Math.min(root.posY,(screen?screen.height:1080)-implicitHeight))
        implicitWidth: root.opened ? 360 : root.asideVisible ? 320 : 128
        implicitHeight: root.opened ? 520 : root.asideVisible ? 280 : 128
        color: "transparent"
        exclusionMode: ExclusionMode.Ignore
        WlrLayershell.namespace: "pixel-spirit"
        WlrLayershell.layer: WlrLayer.Overlay
        WlrLayershell.keyboardFocus: root.opened ? WlrKeyboardFocus.OnDemand : WlrKeyboardFocus.None
        Item {
            width:128; height:128
            Spirit { visible:root.stateReady; anchors.top: parent.top; width:128; height:102; mood:root.displayMood; eco:root.eco; active:win.visible; stage:root.growth.level; trait:root.family;seed:root.profile.seed;device:root.profile.device;accent:Color.accent;foreground:Color.popups.text;background:Color.popups.background }
            Rectangle {visible:!root.stateReady;anchors.centerIn:parent;width:44;height:44;radius:22;color:"transparent";border.width:2;border.color:Color.accent;opacity:0.6}
            MouseArea {
                id: dragArea
                anchors.fill:parent; hoverEnabled:true; acceptedButtons:Qt.LeftButton|Qt.RightButton; cursorShape:pressed?Qt.ClosedHandCursor:Qt.OpenHandCursor
                property real originX: 0
                property real originY: 0
                property real cursorX: 0
                property real cursorY: 0
                property bool located: false
                property real travel: 0
                onPressed: { root.pauseUntil=Date.now()+10000;originX=root.posX; originY=root.posY; located=false; travel=0; cursorPoll.running=true }
                onReleased: function(m) {
                    if(travel<8) {
                        if(m.button===Qt.RightButton) {root.hidden=true;root.opened=false}
                        else root.headPat()
                    }
                    root.persist()
                }
                onCanceled: root.persist()
            }
            DropArea {anchors.fill:parent;onDropped:function(drop){if(drop.hasUrls){root.roomEvent("note",drop.urls[0].toString());root.roomOpen=true}else if(drop.hasText){root.roomEvent("note",drop.text);root.roomOpen=true}drop.acceptProposedAction()}}
            Timer { interval:40; running:dragArea.pressed; repeat:true; onTriggered:if(!cursorPoll.running)cursorPoll.running=true }
            Process {
                id:cursorPoll; command:["hyprctl","cursorpos","-j"]
                stdout:StdioCollector {
                    onStreamFinished: {
                        try {
                            var p=JSON.parse(text)
                            if(!dragArea.pressed) {
                                if(root.movement==="follow" && root.wandering) {
                                    root.targetX=Math.max(0,Math.min(p.x-win.screen.x+90,win.screen.width-128))
                                    root.targetY=Math.max(30,Math.min(p.y-win.screen.y+55,win.screen.height-128))
                                }
                                return
                            }
                            if(!dragArea.located) {dragArea.cursorX=p.x;dragArea.cursorY=p.y;dragArea.located=true}
                            var dx=p.x-dragArea.cursorX,dy=p.y-dragArea.cursorY
                            dragArea.travel=Math.max(dragArea.travel,Math.abs(dx)+Math.abs(dy))
                            root.posX=Math.max(0,Math.min(dragArea.originX+dx,win.screen.width-win.width))
                            root.posY=Math.max(0,Math.min(dragArea.originY+dy,win.screen.height-win.height))
                        } catch(e) {}
                    }
                }
            }
        }
        Ui.BorderSurface {
            visible:root.asideVisible && !root.opened;y:125;width:320;height:asideColumn.implicitHeight+24
            color:Color.popups.background;radius:Style.cornerRadius
            borderSpec:Border.surfaceSpec("popup","border",Color.popups.border,1)
            Column {id:asideColumn;x:12;y:12;width:parent.width-24;spacing:6
                Text {width:parent.width;text:root.profile.name+" · "+root.asideBasis;elide:Text.ElideRight;color:Color.accent;font.family:Style.font.family;font.pixelSize:Style.font.caption}
                Text {width:parent.width;text:root.asideText;textFormat:Text.PlainText;wrapMode:Text.Wrap;color:Color.foreground;font.family:Style.font.family;font.pixelSize:Style.font.body;maximumLineCount:5;elide:Text.ElideRight}
            }
            MouseArea {anchors.fill:parent;onClicked:root.asideVisible=false}
        }
        Rectangle {
            visible:root.opened; y:130; width:parent.width; height:386; radius:14
            color:Color.popups.background; border.color:Color.accent
            Column {
                anchors.fill:parent; anchors.margins:16; spacing:10
                Row {
                    spacing:8
                    Action {text:"Self";onClicked:root.identityOpen=!root.identityOpen}
                    Action {text:"Room";onClicked:root.roomOpen=!root.roomOpen}
                    Action {text:"Senses";onClicked:{root.awarenessOpen=!root.awarenessOpen;awarenessConfig.run(["awareness"])}}
                    Text { text:root.profile.name; color:Color.accent; font.family:Style.fontFamily; font.bold:true; font.pixelSize:12; width:40;elide:Text.ElideRight; anchors.verticalCenter:parent.verticalCenter }
                    Action { text:"—"; onClicked:root.opened=false }
                    Action { text:"×"; onClicked:{root.hidden=true;root.opened=false;root.persist()} }
                }
                Row {
                    spacing:8
                    Action { text:root.journalOpen?"Chat":"Growth"; onClicked:{root.journalOpen=!root.journalOpen;if(root.journalOpen)growthCall.run(["growth"])} }
                    Text { anchors.verticalCenter:parent.verticalCenter; text:!root.stateReady?"Restoring saved companion…":root.growth.stage+" · "+root.growth.trait+" · "+root.growth.xp+(root.growth.next?"/"+root.growth.next:"")+" XP"; color:Color.accent; font.pixelSize:11; font.family:Style.fontFamily }
                }
                Flickable {
                    width:parent.width; height:root.pending?96:128; contentHeight:answer.implicitHeight; clip:true
                    boundsBehavior:Flickable.StopAtBounds
                    Controls.ScrollBar.vertical: Controls.ScrollBar {}
                    Text { id:answer; width:parent.width-8; text:!root.stateReady ? (root.restoreError || "Restoring your saved companion…") : root.journalOpen ? (root.growthError || "Your machine leaves a little of itself in me.\n\n"+Object.keys(root.growth.traits).map(function(k){return k+" "+root.growth.traits[k]}).join(" · ")+"\n\n"+root.growth.journal.map(function(e){return (e.xp?"+"+e.xp+" XP · ":"")+e.text}).join("\n\n")+(root.growth.limited?"\n\nSampled activity: scan budget reached.":"")) : root.reply; textFormat:Text.PlainText; wrapMode:Text.Wrap; color:Color.popups.text; font.family:Style.fontFamily; font.pixelSize:13; lineHeight:1.2 }
                }
                Action { visible:!!root.pending; text:"Run · "+root.pending.replace(/_/g," "); enabled:!root.busy; onClicked:{root.mood="working";actor.run(["action",root.pending])} }
                Controls.TextField {
                    id:field; width:parent.width; height:36; placeholderText:root.busy?"One moment…":"Talk to your machine…"; enabled:!root.busy
                    color:Color.popups.text; placeholderTextColor:Qt.alpha(Color.popups.text,0.5); font.family:Style.fontFamily; selectByMouse:true
                    background:Rectangle {radius:7;color:Qt.alpha(Color.accent,0.08);border.color:Color.popups.border}
                    onAccepted:root.send(); Keys.onEscapePressed:root.opened=false
                }
                Row {
                    spacing:6
                    Action { text:"Send"; enabled:!root.busy; onClicked:root.send() }
                    Action { text:listener.busy?(root.micSeconds>0?"Mic · "+root.micSeconds+"s":"Decoding…"):"Mic · 7s"; enabled:!root.busy; onClicked:{root.micSeconds=7;root.mood="reading";root.reply="Listening now · speak for up to 7 seconds…";listener.run(["listen"])} }
                    Action { text:root.voice?"Voice on":"Voice off"; onClicked:{root.voice=!root.voice;root.persist()} }
                    Action { text:"Clear"; enabled:!root.busy; onClicked:{root.pending="";brain.run(["forget"])} }
                }
                Text { text:root.eco?"Battery care · slow animation · model unloads after reply":"Local AI · drag to move · right-click to hide"; color:Color.popups.text; opacity:0.55; font.pixelSize:10 }
            }
        }
    }
}
