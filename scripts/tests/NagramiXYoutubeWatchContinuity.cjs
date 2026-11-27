const assert = require('node:assert/strict');
const {createWatchPage, Video} = require('./youtube_watch_page_host.cjs');
const page = () => createWatchPage(process.argv[2]);
function enter(player) {
    assert(player.submit('probe', {request: 'pip'}));
    const {request, frameKey, video} = player.events.at(-1);
    const selection = {request, frameKey, video};
    assert(player.submit('enter', selection));
    return selection;
}
function exitState(player) {
    return player.events.filter(event => event.kind === 'state' && !event.active).at(-1);
}

function checkOwner() {
    const p = page(), owner = p.video;
    p.transport('play', 1);
    const session = enter(p);
    const next = new Video();
    next.play();
    p.replace(next);
    assert(next.paused && !owner.paused);
    assert.equal(p.events.filter(e => e.event === 'ready').length, 1);
    next.play(); p.gesture('play', {target: next});
    assert(next.paused);
    p.transport('pause', 2);
    assert(owner.paused);
    owner.dispatchEvent(new Event('pause'));
    assert.equal(p.events.at(-1).event, 'paused');
    p.submit('watchControl', {action: 'seek', revision: 3, value: 25});
    assert.equal(owner.currentTime, 25);
    assert.equal(next.currentTime, 0);
    p.replace(null);
    p.transport('play', 4);
    assert(!owner.paused);
    p.replace(next);
    assert(p.submit('stop', session));
    assert.equal(exitState(p).restore, false);
    assert(owner.paused);
    assert.equal(p.events.at(-1).event, 'ready');
    p.transport('play', 5);
    assert(!next.paused && owner.paused);
    const count = p.events.length;
    owner.dispatchEvent(new Event('error'));
    assert.equal(p.events.length, count);
}

function checkExits() {
    for (const pauseFirst of [true, false]) {
        const p = page();
        p.transport('play', 1);
        const selection = enter(p);
        if (pauseFirst) p.video.pause();
        p.video.webkitSetPresentationMode('inline');
        assert(p.submit('status', selection));
        p.video.pause(); p.video.dispatchEvent(new Event('pause'));
        p.advance(301);
        assert.equal(exitState(p).restore, false);
        assert.equal(p.events.filter(e => e.kind === 'state' && !e.active).length, 1);
    }
    for (const mode of ['playing', 'returnToApp', 'fullscreen', 'backgroundClose', 'pausedClose']) {
        const p = page();
        p.transport('play', 1);
        const selection = enter(p);
        if (mode !== 'playing') p.video.pause();
        if (mode === 'returnToApp' || mode === 'backgroundClose') p.submit('application', {active:false});
        p.video.webkitPresentationMode = mode === 'fullscreen' ? 'fullscreen' : 'inline';
        p.submit('status', selection); // Lost DOM event: poll also adjudicates exit.
        if (mode === 'returnToApp') p.submit('application', {active:true});
        p.advance(301);
        assert.equal(exitState(p).restore, ['playing', 'returnToApp', 'fullscreen'].includes(mode), mode);
    }
    const resumed = page();
    resumed.transport('play', 1);
    enter(resumed);
    resumed.transport('pause', 2);
    resumed.video.play(); // System Play supersedes the earlier inline Pause.
    resumed.video.dispatchEvent(new Event('playing'));
    resumed.video.webkitSetPresentationMode('inline');
    resumed.advance(301);
    resumed.video.dispatchEvent(new Event('timeupdate'));
    assert(exitState(resumed).restore && !resumed.video.paused);
    const p = page();
    p.transport('play', 1);
    const s = enter(p);
    p.video.webkitSetPresentationMode('inline');
    p.submit('stop', s);
    p.advance(500);
    assert.equal(exitState(p).restore, false);
    assert.equal(p.events.filter(e => e.kind === 'state' && !e.active).length, 1);
}

async function checkPlayResponses() {
    for (const action of ['rate', 'seek', 'pause', 'play', 'replace']) {
        const p = page();
        let reject;
        p.video.play = () => new Promise((_, fail) => { reject = fail; });
        p.transport('play', 1);
        const originalReject = reject;
        if (action === 'replace') p.replace(new Video());
        else p.submit('watchControl', {action, value: 3, revision: 2});
        originalReject(Object.assign(new Error('gesture'), {name:'NotAllowedError'}));
        await Promise.resolve();
        const replies = p.events.filter(e => e.event === 'gesture');
        assert.equal(replies.length, ['rate', 'seek'].includes(action) ? 1 : 0, action);
        if (replies.length) assert.equal(replies[0].revision, 1);
    }
}
async function main() {
    checkOwner();
    checkExits();
    await checkPlayResponses();
    const p = page();
    const owner = p.video;
    owner.currentTime = 25;
    owner.seekable = {length:1, start:() => 0, end:() => 90};
    p.transport('play', 1);
    const session = enter(p);
    p.transport('recover', 2);
    assert(!owner.paused && owner.plays === 2 && owner.currentTime === 25);
    assert(p.submit('status', session));
    p.window.dispatchEvent(new Event('online'));
    assert.equal(p.events.at(-1).event, 'online');
    owner.pause(); // The DOM can already be paused when a queued retry arrives.
    p.transport('recover', 3);
    assert(owner.paused && owner.plays === 2 && p.events.at(-1).event === 'paused');
    console.log('Watch PiP ownership, live commands, close and return, network retry and delayed Play responses passed');
}
main().catch(error => { console.error(error); process.exitCode = 1; });
