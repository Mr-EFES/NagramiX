const player = fixture({blocked: false, hasFrame: false});
function enter(request) {
    player.dispatch({command: 'probe', request});
    const candidate = player.messages.filter(m => m.kind === 'candidate' && m.request === request).at(-1);
    check(candidate, 'retry discovered the current video');
    check(player.dispatch({command: 'enter', video: candidate.video, request}), 'entry accepted');
}
enter('first');
player.video.webkitPresentationMode = 'picture-in-picture';
check(player.dispatch({command: 'status', request: 'first'}), 'missed enter event recovered');
check(player.messages.at(-1).active === true, 'start reported');
player.video.webkitPresentationMode = 'inline';
player.dispatch({command: 'status', request: 'first'});
check(player.messages.at(-1).active === false, 'missed exit event recovered');
enter('second');
check(!player.dispatch({command: 'status', request: 'first'}), 'old request ignored');
console.log('WebKit presentation reconciliation passed');
