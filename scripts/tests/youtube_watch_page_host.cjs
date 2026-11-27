const fs = require('node:fs');
const vm = require('node:vm');
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

function createWatchPage(path) {
    const source = fs.readFileSync(path, 'utf8')
        .split('private static let watchScript = #"""')[1].split('"""#')[0]
        .replaceAll('__VIDEO_ID__', 'b_uhOUMfp3k').replaceAll('__TOKEN__', 'test-token').replaceAll('__PIP_ENABLED__', 'true');

    const events = [];
    let video = new Video(), observe, errorPanel = null;
    const handlers = new Map();
    const document = Object.assign(new EventTarget(), {
        addEventListener(name, listener, options) {
            if (!handlers.has(name)) handlers.set(name, []);
            handlers.get(name).push(listener);
            EventTarget.prototype.addEventListener.call(this, name, listener, options);
        },
        querySelector: selector => selector.startsWith('.ytp-error') ? errorPanel : video, createElement: () => ({}), head: {appendChild() {}}, documentElement: {}
    });
    const window = Object.assign(new EventTarget(), {getComputedStyle: () => ({visibility: 'visible'}), navigator: {audioSession: {type: 'auto'}}, webkit: {messageHandlers: {nagramiXSystemPiP: {postMessage: event => events.push(event)}}}});
    const location = new URL('https://m.youtube.com/watch?v=b_uhOUMfp3k');
    let now = 0, nextTimer = 0;
    const timers = new Map();
    function advance(milliseconds) {
        now += milliseconds;
        for (const [id, timer] of timers) {
            if (timer.deadline <= now) { timers.delete(id); timer.callback(); }
        }
    }
    const context = {document, window, location, URLSearchParams, Date: class extends Date { static now() { return now; } },
        setTimeout(callback, delay) { timers.set(++nextTimer, {callback, deadline: now + delay}); return nextTimer; },
        clearTimeout(id) { timers.delete(id); }, MutationObserver: class {
        constructor(callback) { observe = callback; } observe() {}
    }};
    vm.runInNewContext(source, context);
    const submit = (command, extra = {}) => window.nagramiXNativePiPDispatch({token: 'test-token', command, ...extra});
    const transport = (action, revision) => submit('watchControl', {action, revision});

    return {window, events, submit, transport, observe, location, advance, get video() { return video; },
        replace(value) { video = value; observe(); }, setErrorPanel(value) { errorPanel = value; },
        gesture(name, data) { for (const listener of handlers.get(name) || []) listener({isTrusted: true, ...data}); }
    };
}

module.exports = {createWatchPage, Video};
