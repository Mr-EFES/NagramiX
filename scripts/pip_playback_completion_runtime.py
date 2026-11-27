"""Run real gallery focus/finish handlers with controlled AVKit and status delivery."""
from pathlib import Path
from validate_pip_playback_focus import playback_host
from validate_pip_swipe_handoff import U, clean
from validate_quick_format import block

TESTS = Path(__file__).with_name('tests')
YOUTUBE = 'submodules/TelegramUniversalVideoContent/Sources/YoutubeEmbedImplementation.swift'


def fixture(source, previous_footer=None):
    gallery = (source / U).read_text()
    host = playback_host(source)
    host = host.replace(' var isLivePhoto = false, actionAtEnd = 0', '''
 var isLivePhoto = false, actionAtEnd = 0
 var playOnContentOwnership=false, isPlaying=false, isPaused=true, didPause=false
 var playbackBeforePaging:(timestamp:Double,playing:Bool)?
 let isPlayingPromise=Signal(false)
 let footerContentNode=Footer()
 var nagramiXYoutubeSource: WatchReadinessSource?
 var nagramiXUsesWatchControls: Bool { nagramiXYoutubeAvailability.showsWatchControls }
''')
    availability = clean(block((source / YOUTUBE).read_text(), 'public enum NagramiXYoutubeAvailability:'))
    host = host.replace('enum Availability { case loading, playable, unavailable }',
                        availability + '\ntypealias Availability = NagramiXYoutubeAvailability')
    host += '''
final class WatchReadinessSource {
 func checkWatchPictureInPicture(_ completion: @escaping (Bool)->Void) { completion(false) }
}
final class Footer { var playbackControl: (()->Void)? }
extension UniversalVideoNode {
 func togglePlayPause() { play() }
}
extension GalleryLifecycleBoundary {
 func installControls() {
''' + clean(previous_footer or block(gallery, '        self.footerContentNode.playbackControl = {')) + '''
 }
}
'''
    host = host.replace('let scrollView=ScrollView(),pager=Pager();var resets=0',
                        'var onDismiss:(()->Void)?\n let scrollView=ScrollView(),pager=Pager();var resets=0')
    host = host.replace('var dismiss: (() -> Void)? { nil }', 'var dismiss: (() -> Void)? { onDismiss }')
    host = host.replace('    static func main() {', '    static func main() {\n        checkResumptionAndCompletion()')
    return host + '\n' + (TESTS / 'NagramiXPiPPlaybackCompletion.swift').read_text()
