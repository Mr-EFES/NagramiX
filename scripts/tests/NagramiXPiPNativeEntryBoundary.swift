import Foundation

// UIKit, WindowHost presentation and AVKit support are explicit boundaries.
// Admission/footer/transfer/restore/fade/backdrop methods are production bodies.
final class Logger { static let shared = Logger(); func log(_ tag: String, _ value: @autoclosure () -> String) {} }
final class Layer {
    var opacity: Float = 1
    var callbacks: [() -> Void] = []
    var deferCompletions = false
    func presentation() -> Layer? { nil }
    func removeAnimation(forKey: String) {}
    func animateAlpha(from: CGFloat, to: CGFloat, duration: Double, completion: @escaping (Bool) -> Void) {
        if deferCompletions { callbacks.append { completion(false) } } else { completion(true) }
    }
}
class UIView {
    let layer = Layer()
    var window: UIWindow?
    var parent: UIView?
    var fallbackHost: WindowHost?
    var alpha: CGFloat = 1 { didSet { layer.opacity = Float(alpha) } }
    var effectiveAlpha: CGFloat { alpha * (parent?.effectiveAlpha ?? 1) }
}
class UIWindow: UIView {}
class PortalSourceView {}
enum PresentationSurfaceLevel { case root }
typealias ContainableController = GalleryController
func findWindow(_ view: UIView) -> WindowHost? { view.fallbackHost }
// WINDOW_HOST_DECLARATION
extension UIView {
    // WINDOW_HOST_GETTER
}
final class Host: UIWindow, WindowHost {
    var presentations = 0
    func forEachController(_ f: (ContainableController) -> Void) {}
    func present(_ controller: ContainableController, on: PresentationSurfaceLevel, blockInteraction: Bool, completion: @escaping () -> Void) {
        presentations += 1; controller.view.window = self; completion()
    }
    func presentInGlobalOverlay(_ controller: ContainableController) {}
    func addGlobalPortalHostView(sourceView: PortalSourceView) {}
    func invalidateDeferScreenEdgeGestures() {}
    func invalidatePrefersOnScreenNavigationHidden() {}
    func invalidateSupportedOrientations() {}
    func cancelInteractiveKeyboardGestures() {}
    var dismissedKeyboardByCurrentGesture: Bool { false }
}
enum UIAccessibility { static var isReduceMotionEnabled = false }
class GalleryItemNode {}
final class Pager { var current: GalleryItemNode?; func centralItemNode() -> GalleryItemNode? { current } }
final class GalleryControllerNode {
    let pager = Pager()
    let backgroundNode = UIView()
    var nagramiXAllowsSystemPiPTransition = true
    var restorations = 0
    func nagramiXPreparePiPRestoration() { restorations += 1 }
    // BACKDROP_METHOD
}
final class GalleryController {
    let view = UIView()
    let displayNode: AnyObject = GalleryControllerNode()
    var node: GalleryControllerNode { displayNode as! GalleryControllerNode }
    var presentationArguments: Int? = 42
}
class Media { var isAnimated = false }
struct Reference { let media: Media }
class NativeVideoContent { let fileReference = Reference(media: Media()) }
class HLSVideoContent { let fileReference = Reference(media: Media()) }
struct Message { var adAttribute: Int? }
enum ContentInfo { case message(Message, Int), other }
final class Item {
    var isSecret = false
    var contentInfo: ContentInfo? = .other
    var content: AnyObject = NativeVideoContent()
}
enum AVPictureInPictureController { static var supported = true; static func isPictureInPictureSupported() -> Bool { supported } }
final class AppConfiguration { var data: [String: Bool]? }
final class AtomicConfiguration { let value = AppConfiguration(); func with<T>(_ f: (AppConfiguration) -> T) -> T { f(value) } }
final class MediaManager { var currentPictureInPictureNode: GalleryItemNode? }
final class SharedContext { let mediaManager = MediaManager() }
final class Context { let currentAppConfiguration = AtomicConfiguration(); let sharedContext = SharedContext() }
final class VideoNode { let view = UIView(); var canAttachContent = false }
final class NavigationController { var currentWindow: WindowHost? }
final class NagramiXSystemPiPController {}
enum DismissType { case pip }
final class UniversalVideoGalleryItemNode: GalleryItemNode {
    let context = Context()
    let gallery = GalleryController()
    var navigation: NavigationController?
    var item: Item? = Item()
    var videoNode: VideoNode? = VideoNode()
    var isCentral: Bool? = true
    var hasPictureInPicture = true, isLivePhoto = false
    var nativePictureInPictureContent: AnyObject?
    var activePictureInPictureController: GalleryController?
    var activePictureInPictureNavigationController: NavigationController?
    var nagramiXActivePiPWindowHost: WindowHost?
    var beginCount = 0, dismissCount = 0, buttonCount = 0
    let footerContentNode = Footer()
    func galleryController() -> GalleryController? { gallery }
    func baseNavigationController() -> NavigationController? { navigation }
    func beginCustomDismiss(_ type: DismissType) { beginCount += 1 }
    func updateControlsVisibility(_ visible: Bool) {}
    func pictureInPictureButtonPressed() { buttonCount += 1 }
    var eligible: Bool { nagramiXCanUseSystemPiP }
    var reason: String? { nagramiXPiPUnavailableReason }
    lazy var visual = NagramiXPiPVisualHandoff(preview: { _ in }, fadeOut: { [weak self] completion in self?.fadeOut(completion) },
        fadeIn: { [weak self] animated, completion in self?.fadeIn(animated, completion) }, dismiss: { [weak self] in
            self?.dismissCount += 1; self?.gallery.view.window = nil
        })
    init(host: Host) {
        super.init()
        gallery.view.window = host; videoNode!.view.window = host; videoNode!.view.parent = gallery.view
        gallery.node.pager.current = self
        bindFooter()
    }
    func bindFooter() {
        // BIND_FOOTER
    }
    // ADMISSION_METHODS
    func fadeOut(_ completion: @escaping () -> Void) {
        let action: (@escaping () -> Void) -> Void = { [weak self] completion in
            // FADE_OUT_BODY
        }
        action(completion)
    }
    func fadeIn(_ animated: Bool, _ completion: @escaping () -> Void) {
        let action: (Bool, @escaping () -> Void) -> Void = { [weak self] animated, completion in
            // FADE_IN_BODY
        }
        action(animated, completion)
    }
    func transfer(_ content: NagramiXSystemPiPController) -> Bool {
        let node = videoNode, visual = self.visual
        let action: (NagramiXSystemPiPController) -> Bool = { [weak self, weak node] content in
            // TRANSFER_BODY
        }
        return action(content)
    }
    func restore(_ completion: @escaping (Bool) -> Void) {
        let node = videoNode, visual = self.visual
        let action: (@escaping (Bool) -> Void) -> Void = { [weak self, weak node] completion in
            // RESTORE_BODY
        }
        action(completion)
    }
}
final class ControllerInteraction {
    var current: GalleryItemNode?
    func currentItemNode() -> GalleryItemNode? { current }
}
final class Footer {
    var controllerInteraction: ControllerInteraction?
    var nagramiXPictureInPictureRequested: (() -> Void)?
    func press() { pipButtonPressed() }
    // FOOTER_METHOD
}
