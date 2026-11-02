import Foundation

enum MusicPlaybackSettingsOrder { case regular }
enum MusicPlaybackSettingsLooping { case none }
enum AudioPlaybackRate { case x1 }
final class Account {}
final class Author: Equatable {
    let debugDisplayTitle = "Author"
    static func == (lhs: Author, rhs: Author) -> Bool { lhs === rhs }
}
enum SharedMediaPlaybackDisplayData: Equatable {
    case music(String?, String?, String?, Bool, Bool)
    case voice(Author?, Bool)
    case instantVideo(Author?, Bool, Bool)
}
struct PlaylistItem: Equatable { let displayData: SharedMediaPlaybackDisplayData? }
struct SharedMediaPlayerItemPlaybackState: Equatable {
    let item: PlaylistItem
    let status: MediaPlayerStatus
}
enum SharedMediaPlayerItemPlaybackStateOrLoading { case state(SharedMediaPlayerItemPlaybackState), loading }
enum MediaManagerPlayerType { case music, voice, file }
struct Strings { let MediaPlayer_UnknownTrack = "Track"; let MediaPlayer_UnknownArtist = "Artist" }
struct PresentationData { let strings = Strings() }
enum SignalValue<T> { case single(T) }
final class Promise<T> {
    init() {}
    init(_ value: T) { self.value = value }
    var value: T?
    func set(_ value: SignalValue<T>) { if case let .single(v) = value { self.value = v } }
}
final class ValuePromise<T: Equatable> {
    var value: T
    init(_ value: T) { self.value = value }
    func set(_ value: T) { self.value = value }
}
final class Atomic<T> {
    private let lock = NSLock()
    private var value: T
    init(value: T) { self.value = value }
    func with<R>(_ f: (T) -> R) -> R { lock.lock(); defer { lock.unlock() }; return f(value) }
    func swap(_ value: T) -> T { lock.lock(); defer { lock.unlock() }; let old = self.value; self.value = value; return old }
}
enum NagramiXTabSettings { static var backgroundVideoPlaybackEnabled = true }
final class Queue {
    static let shared = Queue()
    var pending: [() -> Void] = []
    static func mainQueue() -> Queue { shared }
    func async(_ action: @escaping () -> Void) { pending.append(action) }
    func flush() { let work = pending; pending = []; work.forEach { $0() } }
}
let MPMediaItemPropertyTitle = "title"
let MPMediaItemPropertyArtist = "artist"
let MPMediaItemPropertyArtwork = "artwork"
let MPMediaItemPropertyPlaybackDuration = "duration"
let MPNowPlayingInfoPropertyMediaType = "mediaType"
let MPNowPlayingInfoPropertyExternalContentIdentifier = "owner"
let MPNowPlayingInfoPropertyElapsedPlaybackTime = "elapsed"
let MPNowPlayingInfoPropertyPlaybackRate = "rate"
enum MPNowPlayingInfoMediaType: Int { case video = 2 }
final class MPNowPlayingInfoCenter {
    static let shared = MPNowPlayingInfoCenter()
    var nowPlayingInfo: [String: Any]?
    static func `default`() -> MPNowPlayingInfoCenter { shared }
}
final class MPRemoteCommand {
    var isEnabled = false
    var targets = 0
    func addTarget(_ target: AnyObject, action: String) { targets += 1 }
    func removeTarget(_ target: AnyObject, action: String) { targets -= 1 }
}
final class MPRemoteCommandCenter {
    static let instance = MPRemoteCommandCenter()
    let playCommand = MPRemoteCommand(), pauseCommand = MPRemoteCommand()
    let previousTrackCommand = MPRemoteCommand(), nextTrackCommand = MPRemoteCommand()
    let togglePlayPauseCommand = MPRemoteCommand(), changePlaybackPositionCommand = MPRemoteCommand()
    static func shared() -> MPRemoteCommandCenter { instance }
}
typealias Selector = String
final class UIImage { let size = CGSize(width: 1, height: 1) }
final class MPMediaItemArtwork {
    init(boundsSize: CGSize, requestHandler: (CGSize) -> UIImage) {}
    init(image: UIImage) {}
}
