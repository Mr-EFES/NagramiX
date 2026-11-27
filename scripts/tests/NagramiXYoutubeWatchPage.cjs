const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const source = fs.readFileSync(process.argv[2], 'utf8')
    .split('private static let watchScript = #"""')[1].split('"""#')[0]
    .replaceAll('__VIDEO_ID__', 'b_uhOUMfp3k').replaceAll('__TOKEN__', 'test-token').replaceAll('__PIP_ENABLED__', 'true');

class Video extends EventTarget {
    constructor() {
        super();
        this.currentTime = 0; this.duration = 90; this.readyState = 4; this.paused = true;
        this.attributes = new Map(); this.plays = 0; this.muted = true; this.webkitPresentationMode = 'inline';
    }
    get disablePictureInPicture() { return this.hasAttribute('disablepictureinpicture'); }
    hasAttribute(name) { return this.attributes.has(name); }
    getAttribute(name) { return this.attributes.get(name); }
    setAttribute(name, value) { this.attributes.set(name, value); }
    removeAttribute(name) { this.attributes.delete(name); }
    play() { this.plays++; this.paused = false; return Promise.resolve(); }
    pause() { this.paused = true; }
    webkitSupportsPresentationMode() { return true; }
    webkitSetPresentationMode(mode) { this.webkitPresentationMode = mode; this.dispatchEvent(new Event('webkitpresentationmodechanged')); }
    getBoundingClientRect() { return {width: 320, height: 180}; }
}
const events = [];
let video = new Video(), observe, errorPanel = null;
const document = Object.assign(new EventTarget(), {
    querySelector: selector => selector.startsWith('.ytp-error') ? errorPanel : video, createElement: () => ({}), head: {appendChild() {}}, documentElement: {}
});
const window = {getComputedStyle: () => ({visibility: 'visible'}), navigator: {audioSession: {type: 'auto'}}, webkit: {messageHandlers: {nagramiXSystemPiP: {postMessage: event => events.push(event)}}}};
const location = new URL('https://m.youtube.com/watch?v=b_uhOUMfp3k');
const context = {document, window, location, URLSearchParams, MutationObserver: class {
    constructor(callback) { observe = callback; } observe() {}
}};
vm.runInNewContext(source, context);
const submit = (command, extra = {}) => window.nagramiXNativePiPDispatch({token: 'test-token', command, ...extra});
const transport = (action, revision) => submit('watchControl', {action, revision});
assert.equal(events.at(-1).event, 'ready');
submit('policy', {pipEnabled: true, backgroundEnabled: true}); assert.equal(window.navigator.audioSession.type, 'playback');
submit('policy', {pipEnabled: true, backgroundEnabled: false}); assert.equal(window.navigator.audioSession.type, 'auto');
transport('play', 1); assert.equal(video.plays, 1); assert.equal(video.muted, false);
video.dispatchEvent(new Event('playing')); assert.equal(events.at(-1).event, 'playing');
assert.equal(transport('pause', 0), false);
submit('probe', {request: 'one'});
const candidate = events.at(-1);
assert.equal(candidate.kind, 'candidate');
const selection = {request: 'one', frameKey: candidate.frameKey, video: candidate.video, requiresPlaying: true};
assert.equal(submit('enter', selection), true); assert.equal(events.at(-1).active, true);
assert.equal(submit('status', selection), true);
submit('stop', selection); assert.equal(events.at(-1).active, false); assert.equal(events.at(-1).restore, false);
submit('policy', {pipEnabled: false}); assert.equal(video.disablePictureInPicture, true);
submit('policy', {pipEnabled: true}); assert.equal(video.disablePictureInPicture, false);
video.setAttribute('disablepictureinpicture', ''); submit('policy', {pipEnabled: false}); submit('policy', {pipEnabled: true});
assert.equal(submit('probe', {request: 'two'}), false);
const old = video; video = new Video(); observe();
assert.equal(events.at(-1).event, 'ready');
const count = events.length; old.dispatchEvent(new Event('error')); assert.equal(events.length, count);
transport('pause', 3); video.paused = false; video.dispatchEvent(new Event('playing')); assert.equal(video.paused, true);
errorPanel = {textContent: 'Unavailable', getClientRects: () => []};
observe(); assert.notEqual(events.at(-1).event, 'pageError');
errorPanel.getClientRects = () => [{}];
observe(); observe(); assert.equal(events.filter(e => e.event === 'pageError').length, 1);
location.search = '?v=ukfI4WLziCM'; assert.equal(transport('play', 4), false);
console.log('Official watch page transport, media replacement, PiP, provider policy and origin checks passed');
