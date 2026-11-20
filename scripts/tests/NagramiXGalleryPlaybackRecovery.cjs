// PROVIDER CALLBACKS
for (const code of [2, 5, 100, 101, 150, 153]) {
    const page = vm.createContext({window: {location: {}}, failed: false, playbackState: 0,
        position: 0, duration: 30, downloadProgress: 0, quality: '', availableQualities: '', storyboardSpec: ''});
    vm.runInContext(providerCallbacks, page);
    page.onPlayerError({data: code});
    check(new URL(page.window.location.href).searchParams.get('failed') === 'true', 'report the provider error');
    page.onStateChange({data: 3});
    check(page.failed, 'buffering is not a confirmed recovery');
    page.onStateChange({data: 1});
    check(!page.failed && page.playbackState === 1, 'genuine playback clears the error');
}
for (const pip of [false, true]) {
    mockAudioSession.type = 'auto';
    const f = fixture({blocked: false});
    f.dispatch({command: 'background', enabled: true});
    check(mockAudioSession.type === 'playback', 'request the WebKit playback category before locking');
    if (pip) {
        f.dispatch({command: 'probe', request: 'playing'});
        const candidate = f.messages.find(m => m.kind === 'candidate');
        f.dispatch({command: 'enter', request: 'playing', video: candidate.video});
        f.flush();
    }
    f.dispatch({command: 'application', active: false});
    check(mockAudioSession.type === 'playback', 'retain the audio category while locked with or without PiP');
    f.dispatch({command: 'playback', enabled: false});
    check(mockAudioSession.type === 'auto', 'release the category on explicit pause');
    mockAudioSession.type = 'play-and-record';
    f.dispatch({command: 'playback', enabled: true});
    f.dispatch({command: 'background', enabled: false});
    check(mockAudioSession.type === 'play-and-record', 'leave the page-owned category intact');
}
console.log('PASS: provider errors, playback category on lock, explicit pause and page-owned audio');
