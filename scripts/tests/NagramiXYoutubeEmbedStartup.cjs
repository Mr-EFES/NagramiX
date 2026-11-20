const assert = require('node:assert/strict');
const {readFileSync} = require('node:fs');
const vm = require('node:vm');

const html = readFileSync(process.argv[2], 'utf8');
const scripts = [...html.matchAll(/<script([^>]*)>([\s\S]*?)<\/script>/g)];
const loader = scripts.find(match => match[1].includes('https://www.youtube.com/iframe_api'));
const inline = scripts.find(match => match[2].includes('new YT.Player'));
const meta = html.indexOf('<meta name="referrer" content="strict-origin-when-cross-origin">');
assert(meta >= 0 && meta < loader.index && inline.index < loader.index);

const messages = [], timers = [], sizes = [];
const iframe = {contentWindow: {postMessage(payload) { messages.push(JSON.parse(payload).command); }}};
const page = {location: {}, innerWidth: 320, innerHeight: 180,
    setInterval(fn) { timers.push(fn); return timers.length; }};
let events;
const player = {
    getIframe: () => iframe, getDuration: () => 37, getCurrentTime: () => 4,
    getVideoLoadedFraction: () => 0.5, setSize: (...size) => sizes.push(size)
};
const sandbox = vm.createContext({window: page, YT: {Player: function(id, options) {
    assert.equal(id, 'player');
    assert.equal(options.playerVars.origin, 'https://com.example.app');
    events = options.events;
    return player;
}}});
vm.runInContext(inline[2].replace('%@', JSON.stringify({videoId: 'sample', playerVars: {origin: 'https://com.example.app'}})), sandbox);
function exerciseEarlyControls() {
    page.onresize();
    sandbox.play();
    sandbox.pause();
    sandbox.seek(12);
    sandbox.setRate(1.5);
}
exerciseEarlyControls();
sandbox.onYouTubeIframeAPIReady();
exerciseEarlyControls();
assert.deepEqual([messages.length, timers.length, sizes.length], [0, 0, 0]);
const state = () => new URL(page.location.href).searchParams;
events.onError({data: 153});
assert.equal(state().get('errorCode'), '153');
events.onReady({target: player});
events.onReady({target: player});
assert.deepEqual(messages, ['initialize', 'tick']);
assert.deepEqual(sizes, [[320, 180]]);
assert.equal(timers.length, 1);
assert.equal(page.location.href, 'embed://onReady');
events.onStateChange({data: 3});
assert.equal(state().get('errorCode'), '153');
events.onStateChange({data: 1});
timers[0]();
assert.equal(state().get('errorCode'), null);
assert.equal(state().get('failed'), 'false');
assert.equal(state().get('position'), '4');
assert.equal(state().get('duration'), '37');
for (const value of [101, 150, 153, undefined]) {
    events.onError({data: value});
    assert.equal(state().get('failed'), 'true');
    assert.equal(state().get('errorCode'), value === undefined ? null : String(value));
}
console.log('PASS: delayed API and iframe readiness, startup policy, one progress timer, error codes and genuine recovery');
