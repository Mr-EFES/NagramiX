import Foundation

// UIKit, chat metadata and navigation-container boundaries. The actual avatar
// handler, native row-selection body and preview commit closure are extracted.
class UIView {
    var isHidden = false
    func convert(_ point: CGPoint, to view: UIView?) -> CGPoint { point }
}
class Node { let view = UIView() }
final class ContextGesture {}
final class ContextContainer: Node {
    var cancelled = false
    func cancelGesture() { cancelled = true }
}
final class TapRecognizer {
    enum State { case ended, began, cancelled, failed }
    var state: State = .ended
    var cancellations = 0
    var isEnabled = true { didSet { if !isEnabled { cancellations += 1 } } }
}
struct Peer { var id: Int; var containerPeerId: Int? }
struct BotFlags: OptionSet {
    let rawValue: Int
    static let hasForum = Self(rawValue: 1)
}
struct BotInfo { var flags: BotFlags }
struct UserPeer { var id: Int; var botInfo: BotInfo? }
struct ChannelPeer { var id: Int; var isForumOrMonoForum = true }
enum EnginePeer {
    case user(UserPeer), channel(ChannelPeer), community(Peer), plain(Peer)
    var id: Int {
        switch self {
        case let .user(p): return p.id
        case let .channel(p): return p.id
        case let .community(p), let .plain(p): return p.id
        }
    }
    var containerPeerId: Int? {
        if case let .plain(p) = self { return p.containerPeerId }
        return nil
    }
}
struct RenderedPeer { var peer: EnginePeer?; var peers: [Int: EnginePeer] = [:]; var peerId: Int = 7 }
struct StoryStats { var totalCount: Int; var hasLiveItems = false }
struct StoryState { var stats: StoryStats }
struct Message { var id: Int; var threadId: Int64? }
struct Topic { var id: Int64 }
struct PeerData {
    var peer = RenderedPeer(peer: .plain(Peer(id: 7)))
    var messages: [Message] = []
    var promoInfo: Int?
    var displayAsMessage = false
    var storyState: StoryState?
    var forumTopicData: Topic?
    var topForumTopicItems: [Topic] = []
    var sourcePeer: EnginePeer?
}
struct GroupData { var groupId: Int }
enum Content { case loading, peer(PeerData), groupReference(GroupData) }
enum ItemIndex { case forum(Int, Int, Int64, Int, Int), chatList(Int) }
enum StorySubject { case peer(Int), archive }
struct Settings { var chatActionsOnHold = true }
enum NagramiXTabSettings { static var current = Settings() }
final class Interaction {
    var inlineNavigationLocation: Bool?
    var isInlineMode = false
    var searchTextHighightState: Bool?
    var nagramiXOpenChatWithoutReadReceipts: ((ChatListItem) -> Void)?
    var activateChatPreview: ((ChatListItem, Int64?, ContextContainer, ContextGesture?, CGPoint?) -> Void)?
    var openStories: (StorySubject, RowHost) -> Void = { _, _ in }
    var openCommunity: (Int) -> Void = { _ in }
    var peerSelected: (EnginePeer, Int64?, Int?, Int?, Bool) -> Void = { _, _, _, _, _ in }
    var messageSelected: (EnginePeer, Int64?, Message, Int?) -> Void = { _, _, _, _ in }
    var groupSelected: (Int) -> Void = { _ in }
}
func communitySourcePeer(peerData: PeerData, message: Message) -> EnginePeer? { peerData.sourcePeer }
final class ListView {}
class ViewController {}
final class NavigationController {
    var viewControllers: [ViewController]
    var commits = 0
    init(_ controllers: [ViewController]) { viewControllers = controllers }
    func pushViewController(_ controller: ViewController, animated: Bool, completion: @escaping () -> Void) {
        viewControllers.append(controller)
        commits += 1
        completion()
    }
    func replaceControllersAndPush(controllers: [ViewController], controller: ViewController, animated: Bool, completion: @escaping () -> Void) {
        commits += 1
        viewControllers = controllers + [controller]
        completion()
    }
}
struct NativeNavigationParams {
    let navigationController: NavigationController
    let animated: Bool
    let completion: (ViewController) -> Void
}
typealias PreviewCommit = (ViewController, Bool, @escaping () -> Void) -> Void
