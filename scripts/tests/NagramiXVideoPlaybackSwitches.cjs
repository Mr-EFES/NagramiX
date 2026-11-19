for (const youtube of [true, false]) {
    const f = fixture({seedYouTube: youtube, blocked: false});
    for (const pip of [false, true, false]) {
        for (const background of [false, true]) {
            f.dispatch({command: 'policy', youtube, pipEnabled: pip, enabled: false, backgroundEnabled: background, pauseGuardEnabled: background});
            f.dispatch({command: 'background', enabled: background});
            check(f.video.hasAttribute('disablepictureinpicture') === !pip, 'embedded player control follows the live setting');
            const request = String(f.messages.length);
            const start = f.messages.length;
            f.dispatch({command: 'probe', request});
            check(f.messages.slice(start).some(m => m.kind === 'candidate' && m.request === request) === pip, 'web candidate follows PiP independently of audio');
        }
    }
}
