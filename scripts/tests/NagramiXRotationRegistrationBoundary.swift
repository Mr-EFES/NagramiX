// AVKit/KVO boundary only. The tested binding method is extracted from the
// transformed native source; the lifecycle is the production implementation.
import Foundation
class CALayer {}
final class AVSampleBufferDisplayLayer: CALayer {}
final class AVPlayerLayer: CALayer {}
final class UniversalVideoNode {
    var layer: CALayer?
    func nagramiXPictureInPictureSourceLayer() -> CALayer? { layer }
}
final class Observation { func invalidate() {} }
enum ObservationOption { case new }
final class Queue {
    static func mainQueue() -> Queue { Queue() }
    func async(_ f: () -> Void) { f() }
}
final class AVPictureInPictureController {
    final class ContentSource {
        init(sampleBufferDisplayLayer: AVSampleBufferDisplayLayer, playbackDelegate: NSObject) {}
    }
    static var creations = 0
    var delegate: AnyObject?
    var contentSource: ContentSource?
    var canStartPictureInPictureAutomaticallyFromInline = true
    var requiresLinearPlayback = true
    var isPictureInPicturePossible = false
    init(contentSource: ContentSource) { Self.creations += 1; self.contentSource = contentSource }
    init(playerLayer: AVPlayerLayer) { Self.creations += 1 }
    func observe(_ key: KeyPath<AVPictureInPictureController, Bool>, options: [ObservationOption], change: @escaping (AVPictureInPictureController, Bool) -> Void) -> Observation { Observation() }
    func invalidatePlaybackState() {}
}
