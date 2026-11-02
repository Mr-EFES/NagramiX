import Foundation

// Existing public TelegramCore compatibility alias, same identity as Message.
typealias EngineRawMessage = Message

// UIKit/AVFoundation, gallery selection and engine/Photos are API boundaries.
// Actual policies, image protection/notification bodies and menu actions are
// inserted by the validator. No screenshot or real media export runs here.
public class CALayer: NSObject {
    weak var superlayer: CALayer?
    var sublayers: [CALayer]? = []
    var disabled = false
    func addSublayer(_ layer: CALayer) {
        layer.removeFromSuperlayer()
        self.sublayers?.append(layer)
        layer.superlayer = self
    }
    func removeFromSuperlayer() {
        self.superlayer?.sublayers?.removeAll(where: { $0 === self })
        self.superlayer = nil
    }
}
public class AVSampleBufferDisplayLayer: CALayer { var preventsCapture = false }
func setLayerDisableScreenshots(_ layer: CALayer, _ protected: Bool) { layer.disabled = protected }
final class UIImage {}
struct UIColor { init(rgb: Int) {} }
class UIView {
    let layer = CALayer()
    var frame: CGRect
    var backgroundColor: UIColor?
    init(frame: CGRect = .zero) { self.frame = frame }
}
final class UIImageView: UIView {
    enum Mode { case scaleAspectFill }
    var contentMode = Mode.scaleAspectFill
    var imageWrites = 0
    var image: UIImage? { didSet { self.imageWrites += 1 } }
}
final class UITextField: UIView {
    var isSecureTextEntry = false
    override init(frame: CGRect = .zero) {
        super.init(frame: frame)
        self.layer.addSublayer(CALayer())
    }
}
final class Disposable { func dispose() {} }
enum ComponentTransition { case immediate }
struct AccountContext { let account = Account() }
struct Account { let peerId = 1 }
struct PresentationStrings {}
struct EnginePeer { let id: Int }
struct ImageMedia { var representations = [1] }
struct FileMedia { var isVideo = true; var mimeType = "video/mp4" }
enum EngineMedia { case image(ImageMedia), file(FileMedia), liveStream, unsupported }
struct StoryItem { var id: Int32 = 9; var isForwardingDisabled = false; var media: EngineMedia = .image(ImageMedia()) }
struct SliceItem { var storyItem = StoryItem() }
struct StorySlice { var effectivePeer = EnginePeer(id: 2); var item = SliceItem() }
struct StoryComponent { let context = AccountContext(); var slice = StorySlice() }
struct AccountUser { let isPremium: Bool }
enum MenuDismiss { case `default` }
struct NagramiXTabSettings {
    static let changedNotification = Notification.Name("NagramiXTabSettingsChanged")
    static var current = NagramiXTabSettings()
    var showForwardWithoutAuthor = false
    var showBroadcastMessages = false
}
enum Namespaces { enum Peer { static let SecretChat = 99 } }
let viewOnceTimeout = Int32.max
struct PeerId { var namespace = 1; var isVerificationCodes = false }
struct MessageId { var peerId = PeerId() }
struct MessageFlags: OptionSet {
    let rawValue: Int
    static let Failed = MessageFlags(rawValue: 1)
    static let Sending = MessageFlags(rawValue: 2)
    var isSending: Bool { self.contains(.Sending) }
}
final class TelegramMediaPaidContent {}
final class TelegramMediaExpiredContent {}
final class TelegramMediaAction {}
struct Message {
    var id = MessageId()
    var containsSecretMedia = false
    var minAutoremoveOrClearTimeout: Int32?
    var flags = MessageFlags()
    var media: [Any] = []
    var paidContent: Int?
    var protected = false
    func isCopyProtected() -> Bool { self.protected }
    // ACTUAL_MESSAGE_ELIGIBILITY
}

final class StoryImage: UIView {
    private let contentView: UIImageView
    private var captureProtectedView: UITextField?
    private var nagramiXCaptureObserver: NSObjectProtocol?
    private var nagramiXCaptureUpdate: (() -> Void)?
    private var nagramiXCaptureBypass = NagramiXPrivacySettings.current.bypassScreenshots
    private var disposable: Disposable?
    var updates = 0
    var infoProtected = false
    var hasSecureWrapper: Bool { self.captureProtectedView != nil }
    var displayedImage: UIImage? { self.contentView.image }
    var imageWrites: Int { self.contentView.imageWrites }
    // ACTUAL_IMAGE_LIFECYCLE
    // ACTUAL_IMAGE_PROTECTION
    func update(context: AccountContext, strings: PresentationStrings, peer: EnginePeer, storyId: Int32,
                media: EngineMedia, size: CGSize, isCaptureProtected: Bool, attemptSynchronous: Bool,
                transition: ComponentTransition) {
        self.updates += 1
        // ACTUAL_IMAGE_UPDATE_PREAMBLE
        // CaptureProtectedInfo and the resource renderer are UI/engine boundaries.
        self.infoProtected = nagramiXIsCaptureProtected
    }
    func deliver(_ image: UIImage, required: Bool) { self.updateImage(image: image, isCaptureProtected: required) }
}

final class LegacyStoryImage: UIView {
    private let contentView = UIImageView()
    private var captureProtectedView: UITextField?
    var hasSecureWrapper: Bool { self.captureProtectedView != nil }
    // ACTUAL_LEGACY_IMAGE_PROTECTION
    func deliver(_ image: UIImage, required: Bool) { self.updateImage(image: image, isCaptureProtected: required) }
}

final class StoryActions {
    var component: StoryComponent?
    var downloads: [(Int, Int32)] = []
    var nativeSaves = 0
    var upgrades = 0
    var canDownload: Bool { self.nagramiXCanDownloadStory }
    var legacyCanDownload: Bool { self.baselineCanDownloadStory }
    // ACTUAL_STORY_ELIGIBILITY
    // ACTUAL_BASELINE_STORY_ELIGIBILITY
    // The unchanged save helper/Photos transaction is a boundary for this test.
    private func nagramiXDownloadStoryPressed() {
        if let component { self.downloads.append((component.slice.effectivePeer.id, component.slice.item.storyItem.id)) }
    }
    private func requestSave() {
        // ACTUAL_SAVE_DISPATCH
        self.nativeSaves += 1
    }
    private func presentSaveUpgradeScreen() { self.upgrades += 1 }
    func pressDownload() { if self.nagramiXCanDownloadStory { self.nagramiXDownloadStoryPressed() } }
    func showSaveItem() -> Bool {
        guard let component else { return false }
        if case .liveStream = component.slice.item.storyItem.media { return false }
        return /* ACTUAL_MENU_VISIBILITY */
    }
    func menuAction(premium: Bool) -> () -> Void {
        let component = self.component!
        let accountUser = AccountUser(isPremium: premium)
        // ACTUAL_MENU_ACTION
        return { action(nil, { _ in }) }
    }
}
