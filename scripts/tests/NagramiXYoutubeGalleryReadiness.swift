import Foundation

// MODEL
enum NoError: Error {}
final class Subscription { func dispose() {} }
final class MetaDisposable { func set(_ subscription: Subscription?) {} }
final class Signal<T, E> {
    var value: T
    var observers: [(T) -> Void] = []
    init(_ value: T) { self.value = value }
    func start(next: @escaping (T) -> Void) -> Subscription {
        observers.append(next)
        next(value)
        return Subscription()
    }
    func deliver(_ value: T) { self.value = value; observers.forEach { $0(value) } }
}
infix operator |> : AdditionPrecedence
func |> <T,R>(lhs: T, rhs: (T) -> R) -> R { rhs(lhs) }
func deliverOnMainQueue<T>(_ signal: T) -> T { signal }
// SOURCE INTERFACE

final class Player: NagramiXYoutubePlaybackSource {
    let nagramiXYoutubeAvailability = Signal<NagramiXYoutubeAvailability, NoError>(.loading)
    var retries = 0
    func nagramiXRetryYoutubePlayback() { retries += 1 }
}
final class Video { var ownsContentNode = true }
struct Content { var id: String }
struct Item { var content = Content(id: "first") }
final class Manager {
    var players: [String: Player] = [:]
    func withUniversalVideoContent(id: String, _ inspect: (AnyObject?) -> Void) { inspect(players[id]) }
}
struct MediaManager { let universalVideoManager = Manager() }
struct Shared { let mediaManager = MediaManager() }
struct Context { let sharedContext = Shared() }

func nagramiXCanOfferPictureInPicture(_ item: Item?) -> Bool { item != nil }
final class Gallery {
    var isCentral: Bool? = true
    var item: Item? = Item()
    var videoNode: Video? = Video()
    var isLivePhoto = false
    var nagramiXWebPiPHasStarted = false
    var nagramiXYoutubeId: String? { item?.content.id }
    var nagramiXYoutubeAvailability: NagramiXYoutubeAvailability = .loading
    weak var nagramiXYoutubeSource: NagramiXYoutubePlaybackSource?
    let nagramiXYoutubeSubscription = MetaDisposable()
    let context = Context()
    var controlsVisible = false
    func updateControlsVisibility(_ value: Bool) { controlsVisible = value }
    func nagramiXUpdatePlaybackSettings() {}
    // GALLERY MEMBERS
}
@main struct Tests {
    static func main() {
        let g = Gallery(), manager = g.context.sharedContext.mediaManager.universalVideoManager
        let a = Player(), b = Player()
        manager.players = ["first": a, "next": b]
        g.nagramiXBindYoutubePlayback()
        precondition(!g.hasPictureInPicture)
        a.nagramiXYoutubeAvailability.deliver(.unavailable)
        g.nagramiXRetryYoutube()
        precondition(a.retries == 1 && g.controlsVisible && !g.hasPictureInPicture)
        a.nagramiXYoutubeAvailability.deliver(.playable)
        precondition(g.hasPictureInPicture)
        g.item = Item(content: Content(id: "next"))
        g.nagramiXBindYoutubePlayback()
        a.nagramiXYoutubeAvailability.deliver(.playable)
        precondition(!g.hasPictureInPicture)
        b.nagramiXYoutubeAvailability.deliver(.playable)
        precondition(g.hasPictureInPicture)
        g.videoNode!.ownsContentNode = false
        g.nagramiXBindYoutubePlayback()
        b.nagramiXYoutubeAvailability.deliver(.unavailable)
        precondition(g.nagramiXYoutubeAvailability == .loading && !g.hasPictureInPicture)
        print("PASS: only the attached YouTube source controls the action, retry and swipe availability")
    }
}
