import QtQuick
import Quickshell.Wayland
import "InputRhythm.js" as Rhythm

Item {
    id: root
    // Enabled is consent/power/visibility; blocked is a temporary desktop state.
    enabled: false
    property bool blocked: true
    property bool mouseGestures: false
    property bool activityResponses: false
    property int revision: 0
    property double clock: Date.now()
    property double checkedAt: 0
    property bool gateOpen: false
    property int generation: 0
    property int requestGeneration: -1
    property double requestAt: 0
    property bool focused: false
    property string reason: "Checking desktop signals…"
    property var motion: Rhythm.newMotion()
    property var activityState: Rhythm.newActivity()
    property bool allowed: enabled && !blocked && gateOpen && clock-checkedAt < 8000
    property bool polling: allowed && mouseGestures && !shortIdle.isIdle
    property string summary: !enabled ? "Input responses are off or resting." :
        !allowed ? (blocked ? "Giving this window space." : reason) :
        focused ? "Quiet company during sustained activity" :
        awayIdle.isIdle ? "Resting while you are away" : "Ready for a nearby mouse wiggle or your return"
    signal wiggle()
    signal welcome()

    function invalidate() {
        generation++; gateOpen=false; checkedAt=0;
        motion.points=[]; Rhythm.pauseActivity(activityState); focused=false;
    }
    function requestGate() {
        if(enabled && !blocked && !gateCall.busy) {
            requestGeneration=generation;requestAt=Date.now();gateCall.run(["input_gate"]);
        }
    }
    function pointer(x, y, near) {
        if(!polling) {motion.points=[];return;}
        if(Rhythm.sample(motion,x,y,Date.now(),near)) wiggle();
    }
    onEnabledChanged: {
        invalidate(); motion=Rhythm.newMotion(); activityState=Rhythm.newActivity();
    }
    onRevisionChanged: {invalidate();motion=Rhythm.newMotion();activityState=Rhythm.newActivity();}
    onBlockedChanged: invalidate()
    onAllowedChanged: if(!allowed){motion.points=[];Rhythm.pauseActivity(activityState);focused=false;}
    onPollingChanged: if(!polling)motion.points=[]
    onMouseGesturesChanged: motion=Rhythm.newMotion()
    onActivityResponsesChanged: {activityState=Rhythm.newActivity();focused=false;}

    IdleMonitor {id:shortIdle;enabled:root.enabled;timeout:12;respectInhibitors:false}
    IdleMonitor {id:awayIdle;enabled:root.enabled && root.activityResponses;timeout:60;respectInhibitors:false}
    Timer {interval:1000;running:root.enabled;repeat:true;onTriggered:{
        root.clock=Date.now();
        if(gateCall.busy && root.clock-root.requestAt>12000){
            root.invalidate();gateCall.cancel();root.reason="Desktop check timed out; retrying shortly.";
        }
        if(root.allowed && root.activityResponses){
            var result=Rhythm.activity(root.activityState,root.clock,shortIdle.isIdle,awayIdle.isIdle);
            root.focused=result.focused;if(result.welcome)root.welcome();
        }
    }}
    Timer {interval:5000;running:root.enabled && !root.blocked;repeat:true;triggeredOnStart:true;onTriggered:root.requestGate()}
    Call {id:gateCall;onReceived:function(data){
        if(!root.enabled || root.blocked || root.requestGeneration!==root.generation)return;
        if(data.error){root.gateOpen=false;root.reason=data.error;return;}
        if(data.revision!==root.revision)return;
        root.checkedAt=Date.now();root.clock=root.checkedAt;
        root.gateOpen=data.allowed===true;root.reason=data.reason||"Desktop check passed.";
    }}
}
