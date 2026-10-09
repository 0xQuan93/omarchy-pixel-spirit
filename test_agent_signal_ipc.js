// Exercise the QML IPC decision code without starting a second desktop shell.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');

const qml = fs.readFileSync('plugin/Desktop.qml', 'utf8');
const start = qml.indexOf('    function presentAgentSignal(source, status) {');
const end = qml.indexOf('    property string pendingAgentSignal:', start);
assert(start >= 0 && end > start);
const implementation = qml.slice(start, end);
const callback = qml.match(/Call \{id:agentSignalGate;onReceived:function\(d\)\{([\s\S]*?)\n    \}\}/);
assert(callback);

let calls = 0;
const ctx = {
    commentAllowed: true,
    pendingAgentSignal: '',
    agentSignalGate: {busy: false, run(args) {calls++; assert.deepEqual(Array.from(args), ['bubble_gate']);}},
};
vm.createContext(ctx);
vm.runInContext(implementation, ctx);
ctx.root = {
    get pendingAgentSignal() {return ctx.pendingAgentSignal;},
    set pendingAgentSignal(value) {ctx.pendingAgentSignal = value;},
    get commentAllowed() {return ctx.commentAllowed;},
    showAgentSignal(message) {this.shown = message;},
};
const finish = vm.runInContext('(function(d){' + callback[1] + '\n})', ctx);

assert.equal(ctx.presentAgentSignal('codex', 'private request'), 'invalid');
assert.equal(calls, 0);
ctx.commentAllowed = false;
assert.equal(ctx.presentAgentSignal('codex', 'finished'), 'quiet');
assert.equal(calls, 0);
ctx.commentAllowed = true;
ctx.agentSignalGate.busy = true;
assert.equal(ctx.presentAgentSignal('codex', 'finished'), 'busy');
ctx.agentSignalGate.busy = false;
assert.equal(ctx.presentAgentSignal('codex', 'needs_input'), 'accepted');
assert.equal(calls, 1);
assert.equal(ctx.root.shown, undefined);
finish({allowed: false});
assert.equal(ctx.root.shown, undefined);
assert.equal(ctx.pendingAgentSignal, '');

assert.equal(ctx.presentAgentSignal('herdr', 'finished'), 'accepted');
ctx.commentAllowed = false;
finish({allowed: true});
assert.equal(ctx.root.shown, undefined);
assert.equal(ctx.pendingAgentSignal, '');

ctx.commentAllowed = true;
assert.equal(ctx.presentAgentSignal('herdr', 'finished'), 'accepted');
finish({allowed: true});
assert.equal(ctx.root.shown, 'An agent in Herdr finished its work.');
assert.equal(ctx.pendingAgentSignal, '');
console.log('Agent signal IPC: fixed input, quiet gate, asynchronous drop and display passed');
