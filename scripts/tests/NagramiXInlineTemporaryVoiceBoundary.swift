import Foundation

struct PeerId: Hashable { var namespace: Int32 = 0; var isVerificationCodes = false; var value = 1 }
struct MessageId: Hashable { var peerId = PeerId(); var namespace: Int32 = 0; var value = 1 }
enum Namespaces { enum Message { static let Cloud: Int32 = 0 }; enum Peer { static let CloudUser: Int32 = 0; static let SecretChat: Int32 = 3 } }
struct MessageFlags: OptionSet {
    let rawValue: Int
    static let Incoming = Self(rawValue: 1)
    static let Failed = Self(rawValue: 2)
    static let sending = Self(rawValue: 4)
    var isSending: Bool { contains(.sending) }
}
class Media {}
final class TelegramMediaFile: Media {
    var isVoice = true
    var isInstantVideo = false
    var isVideo = false
    var isMusic = false
    var isAnimated = false
}
final class TelegramMediaImage: Media {}
final class TelegramMediaPaidContent: Media {}
final class TelegramMediaExpiredContent: Media {}
protocol MessageAttribute {}
final class NagramiXArchivedMessageAttribute: MessageAttribute { let isTemporary: Bool; init(_ value: Bool) { isTemporary = value } }
final class Message {
    var id = MessageId()
    var flags: MessageFlags = [.Incoming]
    var media: [Media] = [TelegramMediaFile()]
    var attributes: [MessageAttribute] = []
    var minAutoremoveOrClearTimeout: Int32? = .max
    var containsSecretMedia: Bool { minAutoremoveOrClearTimeout != nil }
    var paidContent: Media? { media.first { $0 is TelegramMediaPaidContent } }
    var consumed = false
    var deleted = false
}
let viewOnceTimeout: Int32 = .max
struct NagramiXPrivacySettings { static var current: Self { .init() }; var bypassScreenshots: Bool { false } }
struct EngineMessage {
    let raw: Message
    var id: MessageId { raw.id }
    func _asMessage() -> Message { raw }
    func effectivelyIncoming(_ id: PeerId) -> Bool { raw.flags.contains(.Incoming) }
}
class ViewController {}
struct View {}
final class NavigateButtons { let view = View() }
final class ChatDisplayNode { let navigateButtons = NavigateButtons() }
final class ChatBackgroundNode {}
final class Engine {}
final class ScreenCaptureManager { var isRecordingActive = false }
struct Strings {
    let Chat_PlayOnceMesasge_DisableScreenCapture = "recording blocked"
    let Common_OK = "OK"
    let Chat_PlayOnceMesasgeCloseAndDelete = "close and delete"
    let Chat_PlayOnceMesasgeClose = "close"
}
struct PresentationData { let strings = Strings() }
enum MediaPlayerType { case voice }
enum PlaybackAction { case pause }
enum PlayerControl { case playback(PlaybackAction) }
final class MediaManager {
    var stops = 0
    func setPlaylist(_ value: Int?, type: MediaPlayerType, control: PlayerControl) { stops += 1 }
}
enum PeerMessagesPlaylistLocation { case singleMessage(MessageId); case recentActions(Message) }
typealias PlaylistLocation = PeerMessagesPlaylistLocation
struct OpenChatMessageParams {
    let message: Message
    let standalone: Bool
    let playlistLocation: PlaylistLocation
    init(context: AccountContext, chatLocation: Int?, chatFilterTag: Int?, chatLocationContextHolder: Int?, message: Message, standalone: Bool,
         reverseMessageGalleryOrder: Bool, navigationController: Int?, dismissInput: () -> Void,
         present: (Int, Int, Int) -> Void, transitionNode: (Int, Int, Int) -> Int?, addToTransitionSurface: (Int) -> Void,
         openUrl: (Int) -> Void, openPeer: (Int, Int) -> Void, callPeer: (Int, Int) -> Void, openConferenceCall: (Int) -> Void,
         enqueueMessage: (Int) -> Void, sendSticker: Int?, sendEmoji: Int?, setupTemporaryHiddenMedia: (Int, Int, Int) -> Void,
         chatAvatarHiddenMedia: (Int, Int) -> Void, playlistLocation: PlaylistLocation) {
        self.message = message; self.standalone = standalone; self.playlistLocation = playlistLocation
    }
}
final class SharedContext {
    let mediaManager = MediaManager()
    var opened: [OpenChatMessageParams] = []
    func openChatMessage(_ params: OpenChatMessageParams) -> Bool { opened.append(params); return true }
}
final class Account { let peerId = PeerId() }
final class AccountContext { let account = Account(); let engine = Engine(); let sharedContext = SharedContext() }
enum PresentationSurface { case window(PresentationPosition) }
enum PresentationPosition { case root }
enum ContextSurface { case current }
struct TextAlertAction { enum Kind { case defaultAction }; init(type: Kind, title: String, action: () -> Void) {} }
func textAlertController(context: AccountContext, updatedPresentationData: Int?, title: String?, text: String, actions: [TextAlertAction]) -> ViewController { ViewController() }
final class ChatViewOnceMessageContextExtractedContentSource {
    init(context: AccountContext, presentationData: PresentationData, chatNode: ChatDisplayNode, backgroundNode: ChatBackgroundNode, engine: Engine, message: EngineMessage, present: (ViewController) -> Void) {}
}
final class ContextController: ViewController {
    struct Configuration { let sources: [Source]; let initialId: Int }
    struct Source {
        enum ContentSource { case extracted(ChatViewOnceMessageContextExtractedContentSource) }
        let id: Int; let title: String; let source: ContentSource; let items: Signal<Items>; let closeActionTitle: String; let closeAction: () -> Void
    }
    struct Items { enum Content { case list([Int]) }; let content: Content }
    let configuration: Configuration
    var getOverlayViews: (() -> [View])?
    init(_ configuration: Configuration) { self.configuration = configuration }
    func present(_ controller: ViewController, in surface: ContextSurface) {}
}
struct Signal<T> { let value: T; static func single(_ value: T) -> Self { .init(value: value) } }
func makeContextController(presentationData: PresentationData, configuration: ContextController.Configuration) -> ContextController { ContextController(configuration) }
final class ChatControllerImpl {
    let context = AccountContext()
    let presentationData = PresentationData()
    let chatDisplayNode = ChatDisplayNode()
    let chatBackgroundNode = ChatBackgroundNode()
    var screenCaptureManager: ScreenCaptureManager? = ScreenCaptureManager()
    var updatedPresentationData: Int? = nil
    var currentContextController: ContextController?
    var overlays: [ContextController] = []
    var alerts = 0
    func present(_ controller: ViewController, in surface: PresentationSurface) { alerts += 1 }
    func presentInGlobalOverlay(_ controller: ContextController) { overlays.append(controller) }
}
struct PlaybackStatus {
    enum State { case playing, paused }
    let timestamp: Double
    let duration: Double
    let generationTimestamp: Double
    let baseRate: Double
    let status: State
}
private var nativeClock = 10.0
func CACurrentMediaTime() -> Double { nativeClock }
struct WaveformComponent { let isViewOnceMessage: Bool }
struct SemanticAppearance: Equatable { let inset: CGFloat; let lineWidth: CGFloat }
enum SemanticStatusNodeState: Equatable {
    case play, pause
    case secretTimeout(position: Double, duration: Double, generationTimestamp: Double, appearance: SemanticAppearance)
}
let UIScreenPixel: CGFloat = 0.5
final class UnreadIndicator { var isHidden = false }
