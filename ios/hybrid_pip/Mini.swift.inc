private final class NagramiXHybridMiniNode: OverlayMediaItemNode {
    private let dimensions: CGSize
    private var observers: [NSObjectProtocol] = []
    private let retainedOwner: AnyObject
    let video: UniversalVideoNode
    private weak var originalParent: ASDisplayNode?
    private let originalFrame: CGRect
    private let expandAction: () -> Void
    private let closeAction: () -> Void
    var removing = false
    let removalAction: () -> Void
    private let controls = UIStackView()
    init(owner: AnyObject, video: UniversalVideoNode, dimensions: CGSize, half: Double,
         expand: @escaping () -> Void, close: @escaping () -> Void, removed: @escaping () -> Void, background: @escaping () -> Void, foreground: @escaping () -> Void) {
        self.dimensions = dimensions
        self.retainedOwner = owner
        self.video = video
        self.originalParent = video.supernode
        self.originalFrame = video.frame
        self.expandAction = expand
        self.closeAction = close
        self.removalAction = removed
        super.init()
        self.nagramiXHybridHalf = half
        self.hasAttachedContext = true
        self.clipsToBounds = true
        self.cornerRadius = 10
        self.backgroundColor = .black
        self.addSubnode(video)
        self.controls.axis = .horizontal
        self.controls.distribution = .fillEqually
        for (symbol, action, label) in [("arrow.up.left.and.arrow.down.right", #selector(expandPressed), "Развернуть"),
                                        ("playpause.fill", #selector(playPressed), "Воспроизвести или приостановить"),
                                        ("xmark", #selector(closePressed), "Закрыть")] {
            let button = UIButton(type: .system)
            button.setImage(UIImage(systemName: symbol), for: .normal)
            button.tintColor = .white
            button.accessibilityLabel = label
            button.addTarget(self, action: action, for: .touchUpInside)
            self.controls.addArrangedSubview(button)
        }
        self.controls.backgroundColor = UIColor.black.withAlphaComponent(0.5)
        self.view.addSubview(self.controls)
        self.observers.append(NotificationCenter.default.addObserver(forName: UIApplication.willResignActiveNotification, object: nil, queue: .main) { _ in background() })
        self.observers.append(NotificationCenter.default.addObserver(forName: UIApplication.didBecomeActiveNotification, object: nil, queue: .main) { _ in foreground() })
    }
    deinit { for observer in self.observers { NotificationCenter.default.removeObserver(observer) } }
    override func preferredSizeForOverlayDisplay(boundingSize: CGSize) -> CGSize {
        return self.dimensions.aspectFitted(CGSize(width: min(260, max(100, boundingSize.width - 24)), height: 190))
    }
    override func updateLayout(_ size: CGSize) {
        self.video.frame = CGRect(origin: .zero, size: size)
        self.video.updateLayout(size: size, transition: .immediate)
        self.controls.frame = CGRect(x: 0, y: max(0, size.height - 44), width: size.width, height: min(44, size.height))
    }
    override func nagramiXOverlayWillRemove() {
        if !self.removing { self.removing = true; self.removalAction() }
    }
    func restoreVideo() -> Bool {
        guard let parent = self.originalParent else { return false }
        parent.addSubnode(self.video)
        self.video.frame = self.originalFrame
        self.video.updateLayout(size: self.originalFrame.size, transition: .immediate)
        return true
    }
    @objc private func expandPressed() { self.expandAction() }
    @objc private func playPressed() { self.video.togglePlayPause() }
    @objc private func closePressed() { self.closeAction() }
}
