const assert = require('node:assert/strict');
const {createWatchPage, Video} = require('./youtube_watch_page_host.cjs');
const path = process.argv[2];
let checks = 0;
for (const mode of ['inline', 'fullscreen', 'picture-in-picture']) {
    const p = createWatchPage(path);
    for (let index = 1; index <= 12; index++) {
        p.transport('pause', index * 2);
        p.video.webkitPresentationMode = mode;
        // iOS media controls produce media events without a document gesture.
        p.video.play();
        p.video.dispatchEvent(new Event('play'));
        assert.equal(p.events.at(-1).event, 'attempt', 'native Play must announce a new playback intent');
        p.video.dispatchEvent(new Event('playing'));
        p.video.currentTime += 0.2;
        p.video.dispatchEvent(new Event('timeupdate'));
        assert.equal(p.video.paused, false, 'native Play must not be forced back to pause');
        assert.equal(p.events.at(-1).event, 'playing');
        checks += 3;
    }
    if (mode === 'inline') {
        assert(p.submit('probe', {request:'next'}));
        const {request, frameKey, video} = p.events.at(-1);
        assert(p.submit('enter', {request, frameKey, video, requiresPlaying:true}));
        assert.equal(p.events.at(-1).active, true);
        checks += 3;
    }
}
const p = createWatchPage(path);
p.transport('pause', 1);
p.video.dispatchEvent(new Event('play')); // An already queued event with a paused element.
assert.equal(p.events.filter(e => e.event === 'attempt').length, 0);
p.video.paused = false;
p.video.dispatchEvent(new Event('playing')); // No new Play: still the cancelled command.
assert.equal(p.video.paused, true);
const old = p.video;
p.replace(new Video());
const count = p.events.length;
old.play(); old.dispatchEvent(new Event('play')); old.dispatchEvent(new Event('playing'));
assert.equal(p.events.length, count, 'replaced elements cannot request audio');
p.submit('policy', {pipEnabled:false});
p.video.play();p.video.dispatchEvent(new Event('play'));p.video.dispatchEvent(new Event('playing'));
assert(p.video.disablePictureInPicture);
assert.equal(p.submit('probe', {request:'disabled'}), false);
p.location.search='?v=ukfI4WLziCM';
const previous = p.events.length;
p.video.dispatchEvent(new Event('play'));
assert.equal(p.events.length, previous, 'another page cannot request this video');
console.log(`Native YouTube Play intent: ${checks + 6} checks; inline/fullscreen/PiP, repeated Play, stale events, replacement and preferences passed`);
