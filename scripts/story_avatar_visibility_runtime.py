"""Execute real story confirmation, transition callbacks and viewer lifecycle.

UIKit drawing/navigation, peer data and OS scheduling are explicit adapters.
SignalKit, presentation decisions, avatar callbacks and lifecycle bodies come
from the guarded application source; no copied implementation of those bodies.
"""
from pathlib import Path
from validate_quick_format import block
from validate_contact_chat_readiness import NATIVE, KIT

ROOT = Path(__file__).resolve().parents[1]
SCREEN = 'submodules/TelegramUI/Components/Stories/StoryContainerScreen/Sources/StoryContainerScreen.swift'
OPEN = 'submodules/TelegramUI/Components/Stories/StoryContainerScreen/Sources/OpenStories.swift'
PROFILE = 'submodules/TelegramUI/Components/PeerInfo/PeerInfoScreen/Sources/PeerInfoScreenOpenStories.swift'


def declaration(text, marker):
    """Balance the body after a full signature containing a default closure."""
    if not marker.endswith('{'):
        return block(text, marker)
    assert text.count(marker) == 1, marker
    start = text.index(marker)
    brace = start + len(marker) - 1
    depth = 1
    for end in range(brace + 1, len(text)):
        if text[end] == '{': depth += 1
        elif text[end] == '}': depth -= 1
        if depth == 0: return text[start:end + 1]
    raise AssertionError(marker)


def fixture(source):
    screen = (source / SCREEN).read_text()
    opened = (source / OPEN).read_text()
    profile = (source / PROFILE).read_text()
    kit = 'import Foundation\nimport CoreFoundation\n#if canImport(CoreGraphics)\nimport CoreGraphics\n#endif\n'
    for name in NATIVE:
        text = (source / (KIT + name)).read_text()
        if name == 'Signal.swift':
            text = text.split('@available(iOS 13.0, macOS 10.15, *)', 1)[0]
        kit += '\n' + text
    kit += '\n' + block((source / (KIT + 'Signal_Timing.swift')).read_text(), 'public func timeout<')
    boundary = (ROOT / 'scripts/tests/NagramiXStoryProfileBoundary.swift').read_text().split('final class StoryContainerScreen: ViewController {')[0]
    boundary = boundary.replace('final class SharedContext {', 'final class SharedContext {\n    let hasPreloadBlockingContent = Promise<Bool>()')
    boundary = boundary.replace('class ViewController {', 'class ViewController {\n    let view = UIView()\n    func viewDidAppear(_ animated: Bool) {}')
    transition = block(screen, '    public final class TransitionIn {')
    # An actual source76 transition has no callback. The old regression fixture
    # still compiles so its early hiding fails semantically, not syntactically.
    property_line = '    private let nagramiXSourceTransition: TransitionIn?'
    property_line = property_line if property_line in screen else ''
    assignment = '        self.nagramiXSourceTransition = transitionIn'
    assignment = assignment if assignment in screen else '        _ = transitionIn'
    methods = '\n'.join(declaration(screen, marker) for marker in [
        '    private func nagramiXUsesAnonymousViewing(',
        '    fileprivate func nagramiXCanMarkStoryAsSeen(',
        '    public func nagramiXPresent(',
        '    public func nagramiXPush(from parentController: ViewController, completion: @escaping () -> Void = {}) {',
        '    override public func viewDidAppear(',
    ])
    methods = methods.replace('public func ', 'func ')
    # The StoryContainerScreen deinitializer, after its required init.
    life = screen[screen.index('    required public init(coder aDecoder: NSCoder)'):]
    destructor = block(life, '    deinit {')
    archive = opened[opened.index('            var transitionIn:'):opened.index('            let storyContainerScreen =')]
    peer = opened[opened.index('                if let avatarNode {', opened.index('    static func openPeerStories(')):opened.index('            },\n            transitionOut:', opened.index('    static func openPeerStories('))]
    peer_header = opened[opened.index('            transitionIn: { [weak avatarNode] in', opened.index('    static func openPeerStories(')):].split('\n', 1)[0]
    assert '[weak avatarNode]' in peer_header
    profile_setup = profile[profile.index('                var transitionIn:'):profile.index('                let storyContainerScreen =')]
    helpers = '''
func archiveTransition(_ avatarNode: AvatarNode?) -> StoryContainerScreen.TransitionIn? {
ARCHIVE
    return transitionIn
}
func peerTransition(_ avatar: AvatarNode?) -> () -> StoryContainerScreen.TransitionIn? {
    return { [weak avatarNode = avatar] in
PEER
    }
}
final class PeerInfoScreenNode {
    struct Container { let avatarNode: AvatarNode }
    struct List {
        let avatarContainerNode: Container
        let listContainerNode: Indicator
    }
    struct Header { let avatarListNode: List }
    struct Indicator { let expandedStorySetIndicatorTransitionView: (UIView, CGRect)? }
    let headerNode: Header
    init(avatar: AvatarNode, indicator: UIView?) {
        self.headerNode = Header(avatarListNode: List(avatarContainerNode: Container(avatarNode: avatar), listContainerNode: Indicator(expandedStorySetIndicatorTransitionView: indicator.map { ($0, $0.bounds) })))
    }
    func transition(fromAvatar: Bool) -> StoryContainerScreen.TransitionIn? {
PROFILE
        return transitionIn
    }
}
'''.replace('ARCHIVE', archive).replace('PEER', peer).replace('PROFILE', profile_setup)
    adapter = (ROOT / 'scripts/tests/NagramiXStoryAvatarVisibilityBoundary.swift').read_text()
    viewer = '''
final class StoryContainerScreen: ViewController {
TRANSITION
    private let context = AccountContext()
    private var didAnimateIn: Bool = false
PROPERTY
    private let nagramiXContent: StoryContentContext
    private var nagramiXIsPresentingConfirmation = false
    private var nagramiXAcknowledgedAnonymousViewing = false
    private var nagramiXApprovedStoryId: Int?
    private var nagramiXPresentationDisposable: Disposable?
    private let focusedItemPromise = Promise<EngineStoryId?>()
    let node = Node()
    init(_ content: StoryContentContext, transitionIn: TransitionIn?) {
        self.nagramiXContent = content
ASSIGNMENT
        super.init()
    }
DESTRUCTOR
METHODS
}
'''
    for key, value in [('TRANSITION', transition), ('PROPERTY', property_line), ('ASSIGNMENT', assignment), ('DESTRUCTOR', destructor), ('METHODS', methods)]:
        viewer = viewer.replace(key, value)
    return '\n'.join([kit, boundary, adapter, viewer, helpers, (ROOT / 'scripts/tests/NagramiXStoryAvatarVisibilityTests.swift').read_text()])
