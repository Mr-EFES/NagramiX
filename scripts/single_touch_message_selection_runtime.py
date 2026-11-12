"""Actual history range/gesture/scroll code with explicit list, timer and UIKit I/O boundaries."""
from pathlib import Path
from validate_quick_format import block

ROOT = Path(__file__).resolve().parents[1]
HISTORY = 'submodules/TelegramUI/Sources/ChatHistoryListNode.swift'
HELPER = 'submodules/TelegramUI/Sources/Chat/NagramiXMessageDragSelection.swift'


def production(source):
    helper = (source/HELPER).read_text().replace('import UIKit\n', '')
    history = (source/HISTORY).read_text()
    start = history.index('    private func nagramiXBindSingleSelection()')
    end = history.index('    private var selectionPanState:', start)
    methods = history[start:end]
    methods += '\n'.join(block(history, marker) for marker in [
        '    private func messagesAtPoint(',
        '    public func forEachVisibleMessageItemNode(',
        '    @objc private func selectionPanGesture(',
        '    private func handlePanSelection(',
        '    private func setupSelectionScrolling(',
    ])
    return helper, methods


def fixture(source):
    helper, methods = production(source)
    boundary = (ROOT/'scripts/tests/NagramiXMessageDragSelectionBoundary.swift').read_text()
    tests = (ROOT/'scripts/tests/NagramiXMessageDragSelectionChecks.swift').read_text()
    # Objective-C selectors are exercised by the separate real UIKit gate.
    methods = methods.replace('@objc ', '').replace('#selector(self.nagramiXSingleSelectionPan(_:))', '"single-selection"')
    return 'import Foundation\n'+boundary+'\n'+helper+'\nfinal class HistoryHarness {\n'+HISTORY_FIELDS+methods+'\n'+tests+'\n}\n@main struct Main { static func main() { HistoryHarness.checkAll() } }\n'


HISTORY_FIELDS = '''
    var isSelectionGestureEnabled = true
    let listView = ListBackend()
    let controllerInteraction = ControllerInteraction()
    var historyView: ChatHistoryView?
    var frame = CGRect(x: 0, y: 0, width: 390, height: 800)
    var insets = Insets(left: 0, top: 60, bottom: 50)
    private var selectionPanState: (selecting: Bool, initialMessageId: MessageId, toggledMessageIds: [[MessageId]])?
    private var selectionScrollActivationTimer: SwiftSignalKit.Timer?
    private var selectionScrollDisplayLink: ConstantDisplayLinkAnimator?
    private var selectionScrollDelta: CGFloat?
    private var selectionLastLocation: CGPoint?
    private var selectionScrollSkipUpdate = false
    func forEachVisibleItemNode(_ body: (ASDisplayNode) -> Void) { listView.nodes.forEach(body) }
'''


def negatives(code):
    variants = [
        ('baseline', 'let next = range.subtracting(self.baseline)', 'let next = range', 'earlier selection survives reversal'),
        ('reverse', 'remove: self.added.subtracting(next)', 'remove: Set<ID>()', 'reverse retracts only this gesture'),
        ('fast-skip', 'lower <= order && order <= upper', 'lower <= order && order <= upper && order == target', 'fast drag includes intermediate rows'),
        ('window-cache', 'for (order, ids) in rows {', 'self.positions.removeAll()\n        for (order, ids) in rows {', 'loaded windows retain the anchor range'),
        ('disabled-column', 'return point.x >= leftInset && point.x <= leftInset + 44.0', 'return point.x >= leftInset && point.x <= leftInset + 440.0', 'outside checkbox column scrolls normally'),
        ('service', 'let ids = messages.filter { message in !message.media.contains { $0 is TelegramMediaAction } }.map { $0.id }', 'let ids = messages.map { $0.id }', 'service rows cannot enter selection'),
        ('stop-timer', 'self.selectionScrollActivationTimer?.invalidate()\n        self.selectionScrollActivationTimer = nil', 'self.selectionScrollActivationTimer = nil', 'release cancels edge activation'),
        ('scroll-host', 'let scrollHost = self.listView.scrollGestureHostView', 'let scrollHost = self.listView.view', 'both backends use actual scroll pan host'),
    ]
    for name, before, after, diagnostic in variants:
        assert code.count(before) == 1, (name, code.count(before))
        yield name, code.replace(before, after, 1), diagnostic
