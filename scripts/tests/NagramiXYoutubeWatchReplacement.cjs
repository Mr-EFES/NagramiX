const assert = require('node:assert/strict');
const test = require('node:test');
const {createWatchPage, Video} = require('./youtube_watch_page_host.cjs');
const page = () => createWatchPage(process.argv[2]);

function enter(player, request) {
    assert(player.submit('probe', {request}));
    const {frameKey, video} = player.events.at(-1);
    const selection = {request, frameKey, video};
    assert(player.submit('enter', selection));
    return selection;
}

function checkLateWebKitEntry(beforeObserver) {
    const p = page(), old = p.video, next = new Video();
    const original = old.webkitSetPresentationMode.bind(old);
    let completeEntry;
    old.webkitSetPresentationMode = mode => {
        if (mode === 'picture-in-picture') completeEntry = () => original(mode);
        else original(mode);
    };
    p.transport('play', 1);
    enter(p, 'old');
    if (beforeObserver) {
        p.replace(next, false);
        completeEntry();
        p.observe();
    } else {
        p.replace(null);
        p.replace(next);
    }
    assert.equal(p.events.filter(e => e.kind === 'unavailable' && e.request === 'old').length, 1);
    const selection = enter(p, 'new');
    if (!beforeObserver) completeEntry();
    assert.equal(old.webkitPresentationMode, 'inline', 'old window must close after delayed entry');
    assert.equal(next.webkitPresentationMode, 'picture-in-picture');
    assert.equal(p.events.filter(e => e.kind === 'state' && e.request === 'old').length, 0);
    assert(p.submit('status', selection));
    assert(p.submit('stop', selection));
    assert.equal(next.webkitPresentationMode, 'inline');
}

function checkReusedElement() {
    const p = page(), old = p.video;
    const setMode = old.webkitSetPresentationMode.bind(old);
    old.webkitSetPresentationMode = () => {};
    enter(p, 'old');
    p.replace(new Video());
    p.replace(old);
    old.webkitSetPresentationMode = setMode;
    const current = enter(p, 'reused');
    assert.equal(old.webkitPresentationMode, 'picture-in-picture');
    assert.equal(p.events.filter(e => e.kind === 'state' && e.request === 'reused' && e.active).length, 1);
    assert(p.submit('stop', current));
}

async function checkStandardEntry(result) {
    const p = page(), old = p.video, next = new Video(), doc = p.document;
    old.webkitSetPresentationMode = undefined;
    let succeed, fail;
    old.requestPictureInPicture = () => new Promise((resolve, reject) => { succeed = resolve; fail = reject; });
    let exits = 0;
    doc.exitPictureInPicture = () => {
        assert.equal(doc.pictureInPictureElement, old);
        ++exits;
        doc.pictureInPictureElement = null;
        old.dispatchEvent(new Event('leavepictureinpicture'));
        return Promise.resolve();
    };
    enter(p, 'old');
    p.replace(next);
    const selection = enter(p, 'new');
    if (result === 'reject') fail(new Error('source replaced'));
    else {
        doc.pictureInPictureElement = old;
        if (result === 'event-and-promise') old.dispatchEvent(new Event('enterpictureinpicture'));
        succeed();
    }
    await Promise.resolve();
    assert.equal(exits, result === 'reject' ? 0 : 1, 'close only the old document PiP element');
    assert.equal(p.events.filter(e => e.kind === 'unavailable' && e.request === 'old').length, 1);
    assert(p.submit('status', selection));
    assert.equal(next.webkitPresentationMode, 'picture-in-picture');
}

function checkSound() {
    for (const muted of [true, false]) {
        const p = page();
        p.transport('play', 1);
        p.video.muted = muted;
        p.video.dispatchEvent(new Event('volumechange'));
        p.transport('pause', 2);
        p.replace(null);
        const next = new Video();
        next.muted = !muted;
        p.replace(next);
        assert.equal(next.muted, muted, 'restore sound choice before reporting ready');
        assert(next.paused);
        p.transport('play', 3);
        assert.equal(next.muted, muted, 'resume keeps the chosen mute state');
        const selection = enter(p, 'pip');
        next.muted = !muted;
        const replacement = new Video();
        replacement.muted = muted;
        p.replace(replacement);
        p.submit('stop', selection);
        p.transport('play', 4);
        assert.equal(replacement.muted, !muted, 'carry the latest PiP sound choice to inline playback');
    }
    const fresh = page();
    fresh.replace(new Video());
    fresh.transport('play', 1);
    assert.equal(fresh.video.muted, false, 'initial playback still starts with sound');
    const autoplay = page();
    autoplay.video.play();
    autoplay.video.dispatchEvent(new Event('playing'));
    autoplay.transport('play', 1);
    assert.equal(autoplay.video.muted, false, 'the initial native Play can unmute page autoplay');
    const fromPage = page();
    fromPage.video.play();
    fromPage.video.dispatchEvent(new Event('playing'));
    fromPage.video.muted = true;
    fromPage.replace(new Video());
    fromPage.transport('play', 1);
    assert.equal(fromPage.video.muted, true, 'playback started on the page also keeps mute');
}

test('delayed entry closes the replaced player and preserves the current PiP session', async () => {
    for (const beforeObserver of [false, true]) checkLateWebKitEntry(beforeObserver);
    checkReusedElement();
    for (const result of ['event-and-promise', 'promise-only', 'reject']) await checkStandardEntry(result);
});

test('a replacement keeps the sound selected during inline or PiP playback', checkSound);
