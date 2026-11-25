// The validator inserts the production gallery callbacks and route repair below.
import Foundation

// DISMISS GESTURE

enum MediaPlayerSeek: Equatable { case none, start, automatic, timecode(Double) }
enum End { case stop }
enum Phase { case idle, active, restoring }
struct VisualState { var phase = Phase.idle }
class VideoContent {}
struct FileReference { var media = Media() }
struct Media { var isAnimated = false }
class NativeVideoContent: VideoContent { var fileReference = FileReference() }
class HLSVideoContent: VideoContent { var fileReference = FileReference() }
class WebEmbedVideoContent: VideoContent {}
class PlatformVideoContent: VideoContent {}
struct ForwardVideoTimestampAttribute { let timestamp: Int }
struct Message { var attributes: [Any] }
enum Info { case message(Message, Int) }
final class Item {
    var content: VideoContent = NativeVideoContent()
    var fromPlayingVideo = false
    var timecode: Double?
    var contentInfo: Info?
}
func nagramiXUsesEmbeddedPictureInPicture(_ item: Item?) -> Bool { item?.content is WebEmbedVideoContent }
final class Node {
    var ownsContentNode = true
    var canAttachContent = true
    var commands: [String] = []
    var timestamp = 6.0
    func seek(_ value: Double) { timestamp = value; commands.append("seek") }
    func play() { commands.append("play") }
    func pause() { commands.append("pause") }
    func playOnceWithSound(playAndRecord: Bool, seek: MediaPlayerSeek, actionAtEnd: End) {
        precondition(!playAndRecord)
        if case let .timecode(value) = seek { timestamp = value }
        commands.append("play")
    }
    func setBaseRate(_ rate: Double) {}
}
final class Button { var isHidden = false }
class Base {
    func activateAsInitial() {}
    func visibilityUpdated(isVisible: Bool) {}
}
final class Gallery: Base {
    var item: Item? = Item()
    var videoNode: Node? = Node()
    var isCentral: Bool? = true
    var _isVisible: Bool? = true
    var playbackRate: Double?
    var playerStatusValue: Int?
    var initiallyActivated = false
    var isAnimatingOut = false
    var nagramiXPiPVisualState = VisualState()
    var nagramiXWebPiPTransitionStarted = false
    var nagramiXWebPiPHasStarted = false
    var playOnContentOwnership = false
    var playbackBeforePaging: (timestamp: Double, playing: Bool)?
    var actionAtEnd = End.stop
    var hideStatusNodeUntilCentrality = false
    var statusNodeShouldBeHidden = false
    let statusButtonNode = Button()
    func playLivePhotoAutoplayIfNeeded(videoNode: Node) -> Bool { false }
    func updateDisplayPlaceholder() {}
    func maybeStorePlaybackStatus(status: Int) {}
    func shouldAutoplayOnCentrality() -> Bool { true }
    func nagramiXFinishSystemWebPiP(stop: Bool) { preconditionFailure("Interrupted PiP") }
    // GALLERY METHODS
}

enum SessionType { case play(Bool), playWithPossiblePortOverride, voiceCall, record }
enum Output { case system, speakerIfNoHeadphones, custom }
enum Port { case builtInReceiver, builtInSpeaker, bluetooth, headphones, airPlay }
struct PortDescription { let portType: Port }
struct Route { var outputs: [PortDescription] = [] }
final class AVAudioSession {
    static let session = AVAudioSession()
    static func sharedInstance() -> AVAudioSession { session }
    enum Option: Hashable { case mixWithOthers }
    enum Category { case playback }
    enum Mode { case `default` }
    var currentRoute = Route()
    var activations = 0
    var options: Set<Option> = []
    func setCategory(_ category: Category, mode: Mode, options: Set<Option>) throws { self.options = options }
    func setActive(_ active: Bool) throws { precondition(active); activations += 1 }
}
func managedAudioSessionLog(_ line: String) {}
final class AudioManager {
    var isActiveValue = true
    var callKitAudioSessionIsActive = false
    var currentTypeAndOutputMode: (SessionType, Output)? = (.play(false), .system)
    var repairedReceiverForMedia = false
    // AUDIO METHOD
}

struct MediaPlayerLoadedState {
    struct ControlTimebase { var timebase: Double }
    let controlTimebase: ControlTimebase
    init(_ seconds: Double) { controlTimebase = ControlTimebase(timebase: seconds) }
}
func CMTimeGetSeconds(_ t: Double) -> Double { t }
func CMTimebaseGetTime(_ t: Double) -> Double { t }
struct Cancel { func dispose() {} }
enum Action { case play, pause }
enum State {
    case empty, playing(MediaPlayerLoadedState), paused(MediaPlayerLoadedState)
    case seeking(Int, Double, Int?, Cancel, Action, Bool)
}
struct ImmediateQueue { func isCurrent() -> Bool { true } }
final class Core {
    var state = State.empty
    let queue = ImmediateQueue()
    let video = true, isAudioVideoMessage = false
    var audioRenderer: Int? = 1
    var audioRendererGeneration: UInt64 = 2
    var enableSound = false, stoppedAtEnd = false, playAndRecord = false
    var continuePlayingWithoutSoundOnLostAudioSession = true
    var lastStatusUpdateTimestamp: Double?
    var seeks: [Double] = []
    func currentDuration() -> Double? { 30 }
    func seek(timestamp: Double, action: Action) {
        seeks.append(timestamp)
        state = action == .play ? .playing(MediaPlayerLoadedState(timestamp)) : .paused(MediaPlayerLoadedState(timestamp))
    }
    func play() { state = .playing(MediaPlayerLoadedState(currentVideoPosition())) }
    func pause(lostAudioSession: Bool, faded: Bool) { state = .paused(MediaPlayerLoadedState(currentVideoPosition())) }
    // CORE METHODS
}

@main enum Tests {
    static func main() {
        let core = Core()
        core.state = .seeking(0, 17, nil, Cancel(), .play, false)
        core.playOnceWithSound(playAndRecord: false, seek: .none)
        precondition(core.seeks == [17])
        core.audioRendererInterrupted(generation: 1)
        precondition(core.enableSound && core.seeks == [17])
        core.state = .paused(MediaPlayerLoadedState(29.5))
        core.audioRendererInterrupted(generation: 2)
        precondition(core.enableSound && core.seeks == [17])
        core.state = .playing(MediaPlayerLoadedState(29.5))
        core.audioRendererInterrupted(generation: 2)
        precondition(!core.enableSound && core.seeks == [17, 29.5])
        core.playOnceWithSound(playAndRecord: false, seek: .none)
        precondition(core.enableSound && core.seeks == [17, 29.5, 29.5])

        let gallery = Gallery(), video = gallery.videoNode!
        video.ownsContentNode = false
        gallery.activateAsInitial()
        precondition(video.commands.isEmpty && gallery.playOnContentOwnership)
        video.ownsContentNode = true
        gallery.activateAsInitial()
        precondition(video.timestamp == 6 && video.commands == ["play"])
        video.pause()
        gallery.visibilityUpdated(isVisible: false)
        gallery.visibilityUpdated(isVisible: true)
        gallery.activateAsInitial()
        precondition(video.timestamp == 6 && video.canAttachContent && video.commands == ["play", "pause"])
        precondition(!gallery.statusButtonNode.isHidden)
        gallery.playbackBeforePaging = (12, false)
        gallery.activateAsInitial()
        precondition(video.timestamp == 12 && video.commands.suffix(2) == ["pause", "seek"])
        gallery.playbackBeforePaging = (21, true)
        gallery.activateAsInitial()
        precondition(video.timestamp == 21 && video.commands.last == "play")
        let linked = Gallery()
        linked.item?.timecode = 42
        linked.activateAsInitial()
        linked.videoNode?.timestamp = 44
        linked.activateAsInitial()
        precondition(linked.videoNode?.timestamp == 44 && linked.videoNode?.commands == ["play"])
        let pip = Gallery()
        pip.nagramiXPiPVisualState.phase = .restoring
        pip.nagramiXWebPiPTransitionStarted = true
        pip.visibilityUpdated(isVisible: false)
        pip.activateAsInitial()
        precondition(pip.videoNode!.commands.isEmpty && pip.videoNode!.canAttachContent)

        func closes(_ x: CGFloat, _ y: CGFloat, _ speed: CGFloat) -> Bool {
            nagramiXIsVideoDismissSwipe(translation: CGPoint(x: x, y: y),
                                        velocity: CGPoint(x: 0, y: speed), height: 840)
        }
        precondition(closes(5, 85, 0) && closes(0, 12, -1.2))
        precondition(!closes(0, -90, 2) && !closes(100, 80, -1.2) && !closes(0, 8, -0.1))
        precondition(!closes(.nan, 100, -2))
        let manager = AudioManager(), audio = AVAudioSession.session
        func route(_ ports: [Port]) {
            audio.currentRoute.outputs = ports.map { PortDescription(portType: $0) }
            manager.reconcilePlaybackReceiver()
        }
        for ports: [Port] in [[], [.builtInSpeaker], [.bluetooth], [.headphones], [.airPlay], [.builtInReceiver, .bluetooth]] {
            route(ports)
        }
        precondition(audio.activations == 0)
        route([.builtInReceiver]); route([.builtInReceiver])
        precondition(audio.activations == 1 && audio.options.isEmpty)
        for type in [SessionType.voiceCall, .record] {
            manager.currentTypeAndOutputMode = (type, .system)
            route([.builtInReceiver])
        }
        manager.currentTypeAndOutputMode = (.play(true), .custom)
        route([.builtInReceiver])
        manager.currentTypeAndOutputMode = (.play(true), .system)
        manager.callKitAudioSessionIsActive = true
        route([.builtInReceiver])
        precondition(audio.activations == 1)
        manager.callKitAudioSessionIsActive = false
        route([.builtInReceiver])
        precondition(audio.activations == 2 && audio.options == [.mixWithOthers])
        manager.currentTypeAndOutputMode = (.playWithPossiblePortOverride, .system)
        route([.builtInReceiver])
        precondition(audio.activations == 2)
        manager.currentTypeAndOutputMode = (.playWithPossiblePortOverride, .speakerIfNoHeadphones)
        route([.builtInReceiver])
        precondition(audio.activations == 3 && audio.options.isEmpty)
    }
}
