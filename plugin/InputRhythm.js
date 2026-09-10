// Pure, bounded, transient state. No input text, files, networking or rewards.
function newMotion() { return {points: [], lastReaction: -Infinity}; }
function sample(state, x, y, now, near) {
    if (!near || !Number.isFinite(x) || !Number.isFinite(y)) {
        state.points = []; return false;
    }
    var points = state.points;
    var previous = points.length ? points[points.length - 1] : null;
    if (previous && (now <= previous.t || now - previous.t > 600 ||
                     Math.hypot(x - previous.x, y - previous.y) > 600)) points = [];
    points.push({x:x, y:y, t:now});
    state.points = points = points.filter(function(p) {return now-p.t <= 1800;}).slice(-14);
    if (now - state.lastReaction < 20000 || points.length < 5) return false;
    // Several substantial reversals on either axis, not a single fast sweep.
    for (var axis of ['x', 'y']) {
        var direction = 0, reversals = 0, travel = 0, anchor = points[0][axis];
        var low = anchor, high = anchor;
        for (var i = 1; i < points.length; i++) {
            var value = points[i][axis], delta = value - anchor;
            low = Math.min(low, value); high = Math.max(high, value);
            if (Math.abs(delta) < 24) continue;
            var next = delta > 0 ? 1 : -1;
            if (direction && next !== direction) reversals++;
            direction = next; travel += Math.abs(delta); anchor = value;
        }
        if (reversals >= 3 && travel >= 180 && high-low >= 70) {
            state.lastReaction = now; state.points = []; return true;
        }
    }
    return false;
}

function newActivity() {return {since:null, last:null, away:false, lastWelcome:-Infinity};}
function pauseActivity(state) {state.since = null; state.last = null;}
function activity(state, now, idle, away) {
    if (state.last !== null && (now <= state.last || now-state.last > 2500)) state.since = null;
    state.last = now;
    var welcome = false;
    if (away) state.away = true;
    if (idle) state.since = null;
    else {
        if (state.away && now-state.lastWelcome >= 300000) {
            welcome = true; state.lastWelcome = now;
        }
        state.away = false;
        if (state.since === null) state.since = now;
    }
    return {focused:state.since !== null && now-state.since >= 45000, welcome:welcome};
}
