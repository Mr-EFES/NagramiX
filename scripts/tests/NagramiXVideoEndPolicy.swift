import Foundation
extension Notification.Name {
    static let AVPlayerItemDidPlayToEndTime = Notification.Name("test-player-ended")
}
final class CompletionPlayer { let currentItem = NSObject() }
final class ListenerBag {
    var callbacks: [() -> Void] = []
    func copyItems() -> [() -> Void] { callbacks }
}
final class SystemCompletionBoundary {
    let player = CompletionPlayer()
    let playbackCompletedListeners = ListenerBag()
    var didPlayToEndTimeObserver: NSObjectProtocol?
    var pauses = 0
    func pause() { pauses += 1 }
    init() {
        // PRODUCTION_OBSERVER
    }
    deinit { if let didPlayToEndTimeObserver { NotificationCenter.default.removeObserver(didPlayToEndTimeObserver) } }
}
enum MediaPlayerPlayOnceWithSoundActionAtEnd { case stop, loop }
struct CompletionPolicy {
    var isLivePhoto = false
    var isLivePhotoPlaybackActive = false
    // PRODUCTION_POLICY
}
@main struct CompletionBoundaryTests {
    static func main() {
        let node = SystemCompletionBoundary()
        var completions = 0
        node.playbackCompletedListeners.callbacks = [{ completions += 1 }]
        NotificationCenter.default.post(name: .AVPlayerItemDidPlayToEndTime, object: NSObject())
        precondition(completions == 0)
        NotificationCenter.default.post(name: .AVPlayerItemDidPlayToEndTime, object: node.player.currentItem)
        precondition(completions == 1 && node.pauses == 1)
        precondition(CompletionPolicy().actionAtEnd == .stop)
        precondition(CompletionPolicy(isLivePhoto: true).actionAtEnd == .stop)
        precondition(CompletionPolicy(isLivePhoto: true, isLivePhotoPlaybackActive: true).actionAtEnd == .loop)
        print("System media completion and normal video/Live Photo end policy passed")
    }
}
