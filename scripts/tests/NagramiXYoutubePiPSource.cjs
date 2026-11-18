async function exerciseStandardAPI() {
    const f = fixture({standardOnly: true, blocked: false});
    f.dispatch({command: 'policy', youtube: true, enabled: true});
    f.flush();
    function probe(request) {
        f.dispatch({command: 'probe', request});
        return f.messages.filter(m => m.kind === 'candidate' && m.request === request).at(-1);
    }
    function enter(candidate) {
        return f.dispatch({command: 'enter', request: candidate.request, video: candidate.video});
    }
    const first = probe('first');
    check(first, 'standard-only player was not discovered');
    f.removeVideo(f.video);
    check(!enter(first) && f.messages.at(-1).kind === 'unavailable', 'removed video accepted');
    const replacement = f.appendVideo();
    f.flush();
    const next = probe('first');
    check(next.video !== first.video, 'replacement reused a stale element key');
    let rejectOld;
    replacement.requestPictureInPicture = () => new Promise((resolve, reject) => { rejectOld = reject; });
    check(enter(next), 'standard request declined');
    check(!f.messages.some(m => m.kind === 'state' && m.active), 'unconfirmed request reported active');
    f.dispatch({command: 'stop', request: 'first'});
    const retry = probe('second');
    replacement.requestPictureInPicture = async () => {
        f.document.pictureInPictureElement = replacement;
        replacement.media('enterpictureinpicture');
    };
    check(enter(retry), 'standard retry failed');
    rejectOld(Error('old request'));
    await Promise.resolve();
    f.flush();
    check(f.messages.at(-1).kind === 'state' && f.messages.at(-1).active && f.messages.at(-1).request === 'second', 'wrong session active');
    f.document.pictureInPictureElement = null;
    replacement.media('leavepictureinpicture');
    f.flush();
    check(!f.messages.at(-1).active && f.messages.at(-1).restore, 'return from standard PiP failed');
    replacement.requestPictureInPicture = () => Promise.reject(Error('unavailable'));
    enter(probe('declined'));
    await Promise.resolve();
    f.flush();
    check(f.messages.at(-1).request === 'declined' && !f.messages.at(-1).active, 'system refusal reported active');
    console.log('Standard PiP entry, rejection, replacement and return passed');
}
exerciseStandardAPI().catch(error => { console.error(error); process.exitCode = 1; });
