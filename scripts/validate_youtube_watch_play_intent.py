#!/usr/bin/env python3
"""Exercise native iOS Play events against the real watch script, controller and audio policy."""
import argparse
from pathlib import Path
import shutil
import subprocess
import tempfile

from system_web_picture_in_picture_runtime import WEB, CONTENT
from validate_local_copy_delivery import execute, run
from validate_quick_format import block
from validate_release_095_apple_preflight import canonical_projection
from validate_upstream_13_2_release import OVERLAY, checked_plan, digest, guard_checks
from validate_video_playback_switches import player_host
from validate_youtube_pip_readiness import TESTS, youtube_controller_host

STAGE = 'youtube_watch_play_intent'
CONTROLLER = str(Path(WEB).with_name('YoutubeEmbedImplementation.swift'))


def audio_host(source):
    controller = (source / CONTROLLER).read_text()
    content = (source / CONTENT).read_text()
    host = player_host(source, False)
    # WebKit adapters declare the actual watch-page APIs; transport is exercised
    # separately by the production JavaScript and controller tests below.
    host = '#if canImport(FoundationNetworking)\nimport FoundationNetworking\n#endif\n' + host
    host = host.replace('enum WKContentWorld {case page}', 'enum WKContentWorld: Equatable {case page,defaultClient}')
    host = host.replace('struct WKScriptMessage {', 'struct WKScriptMessage {var world=WKContentWorld.page;')
    host = host.replace('final class WKFrameInfo {', 'final class WKFrameInfo {var isMainFrame=true;var request=URLRequest(url:URL(string:"https://m.youtube.com/watch?v=b_uhOUMfp3k")!);')
    host = host.replace('final class WKUserContentController {', '''final class WKNavigation {}
final class WKWebViewConfiguration {let userContentController=WKUserContentController()}
extension WKUserScript {
 init(source:String,injectionTime:Time,forMainFrameOnly:Bool,in world:WKContentWorld) {
  self.init(source:source,injectionTime:injectionTime,forMainFrameOnly:forMainFrameOnly)
 }
}
final class WKUserContentController {
 func removeAllUserScripts() {}
 func removeScriptMessageHandler(forName:String) {}
 func add(_ handler:WKScriptMessageHandler,contentWorld:WKContentWorld,name:String) {}
''')
    host = host.replace('final class WKWebView: UIView {', '''final class WKWebView: UIView {
 let configuration=WKWebViewConfiguration()
 func load(_ request:URLRequest)->WKNavigation? {WKNavigation()}
''')
    stub = 'final class YoutubeEmbedImplementation:EmbedImplementation {}'
    replacement = block(controller, 'public enum NagramiXYoutubeAvailability:') + '''
final class YoutubeEmbedImplementation: EmbedImplementation {
 var availability = NagramiXYoutubeAvailability.watchPlayable
 var wantsPlayingPictureInPicture = true
}
'''
    assert host.count(stub) == 1
    host = host.replace(stub, replacement)
    prepare = block(content, '    func nagramiXPrepareGalleryPlayback(_ ready: @escaping () -> Bool) {')
    host = host.replace('final class WebPolicy {', 'final class WebPolicy {\n var nagramiXPreparedGalleryPlay: (() -> Bool)?\n' + prepare + '\n')
    marker = ' init(youtube:Bool=true){playerNode=Player(youtube:youtube)\n'
    assert host.count(marker) == 1
    binding = block(content, '        self.playerNode.nagramiXActualPlaybackRequested = ')
    return host.replace(marker, marker + binding + '\n')


def validate(source, swiftc, work):
    plan = checked_plan(STAGE)
    for name, sha in {**plan['outputs'], **plan['guards']}.items():
        assert digest(source / name) == sha, name
    for name in plan['outputs']:
        run([swiftc, '-frontend', '-parse', source / name])
    print('Stage guard checks:', len(guard_checks(source, STAGE, plan, work / 'guards')), flush=True)
    # The same behavioral test must reject the exact previous shipped script.
    old = OVERLAY / plan['previous'][WEB]
    result = subprocess.run(['node', str(TESTS / 'NagramiXYoutubeWatchPlayIntent.cjs'), str(old)], text=True, capture_output=True)
    assert result.returncode != 0 and 'native Play must announce a new playback intent' in result.stderr
    print('Previous native-controls Play/Pause loop reproduced', flush=True)
    for suite in ['NagramiXYoutubeWatchPlayIntent', 'NagramiXYoutubeWatchPage', 'NagramiXYoutubeWatchContinuity', 'NagramiXYoutubeWatchReplacement', 'NagramiXYoutubePlaybackCompletion']:
        print(run(['node', TESTS / (suite + '.cjs'), source / WEB]).stdout.strip(), flush=True)
    for name in ['Youtube.html', 'YoutubeUserScript.js']:
        shutil.copy(source / ('submodules/TelegramUI/Resources/WebEmbed/' + name), work / name)
    controller = youtube_controller_host((source / CONTROLLER).read_text())
    node = (source / WEB).read_text()
    requested = next(line for line in node.splitlines() if line.strip().startswith('var nagramiXActualPlaybackRequested:'))
    binding = next(line for line in node.splitlines() if 'youtube.onPlaybackRequested = ' in line)
    controller += '\nfinal class WatchNativeIntentBridge {\n' + requested + '\n init(_ youtube: YoutubeEmbedImplementation) {\n' + binding + '\n }\n}\n'
    audio = audio_host(source)
    for name, host in [('YoutubeWatchPlayIntent', controller + (TESTS / 'NagramiXYoutubeWatchPlayIntent.swift').read_text()),
                       ('YoutubeWatchContinuity', controller + (TESTS / 'NagramiXYoutubeWatchContinuity.swift').read_text()),
                       ('YoutubePlaybackCompletion', controller + (TESTS / 'NagramiXYoutubePlaybackCompletion.swift').read_text()),
                       ('YoutubeWatchAudioIntent', audio + '\n' + (TESTS / 'NagramiXYoutubeWatchAudioIntent.swift').read_text())]:
        for result in execute(swiftc, work, name, host):
            print(result['mode'], result['output'], flush=True)
    old_content = (OVERLAY / plan['previous'][CONTENT]).read_text()
    previous_status = old_content[old_content.index('            switch status.status {'):old_content.index('            self.nagramiXUpdateManagedPlayback()', old_content.index('            switch status.status {'))]
    content = (source / CONTENT).read_text()
    current_status = content[content.index('            switch status.status {'):content.index('            self.nagramiXUpdateManagedPlayback()', content.index('            switch status.status {'))]
    assert audio.count(current_status) == 1
    old_audio = audio.replace(current_status, previous_status) + '\n' + (TESTS / 'NagramiXYoutubeWatchAudioIntent.swift').read_text()
    for result in execute(swiftc, work, 'PreviousWatchAudio', old_audio, 'accepted preroll must wait for the final audio handoff'):
        print(result['mode'], 'previous audio handoff regression reproduced', flush=True)
    bridge = (source / WEB).read_text()
    assert 'youtube.onPlaybackRequested = { [weak self] in self?.nagramiXActualPlaybackRequested?() }' in bridge


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument('--source', type=Path)
    mode.add_argument('--canonical', action='store_true')
    parser.add_argument('--swiftc', required=True)
    args = parser.parse_args()
    with tempfile.TemporaryDirectory(prefix='youtube-watch-play-intent-') as temp:
        work = Path(temp)
        source = args.source
        if source is None:
            source = work / 'source'
            canonical_projection(source, STAGE)
            plan = checked_plan(STAGE)
            for name, template in plan['guard_sources'].items():
                path = source / name
                if not path.exists():
                    path.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copyfile(OVERLAY / template, path)
        validate(source, args.swiftc, work)


if __name__ == '__main__':
    main()
