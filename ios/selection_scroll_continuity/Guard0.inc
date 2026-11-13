import Foundation
import UIKit

// The baseline is immutable for the gesture: retracting its range never clears
// an earlier selection. Cache order across loaded windows, not just hit rows.
struct NagramiXMessageDragSelection<ID: Hashable, Order: Comparable> {
    let baseline: Set<ID>
    let anchorId: ID
    let anchorFallback: Order
    private var positions: [ID: Order] = [:]
    private var added: Set<ID> = []

    init(baseline: Set<ID>, anchorId: ID, anchorOrder: Order) {
        self.baseline = baseline
        self.anchorId = anchorId
        self.anchorFallback = anchorOrder
        self.positions[anchorId] = anchorOrder
    }

    mutating func cache(_ rows: [(Order, [ID])]) {
        for (order, ids) in rows {
            for id in ids { self.positions[id] = order }
        }
    }

    mutating func cacheMissing(order: Order, ids: [ID]) {
        let position = ids.compactMap { self.positions[$0] }.first ?? order
        for id in ids where self.positions[id] == nil { self.positions[id] = position }
    }

    mutating func update(targetId: ID, fallbackOrder: Order) -> (add: Set<ID>, remove: Set<ID>) {
        let anchor = self.positions[self.anchorId] ?? self.anchorFallback
        let target = self.positions[targetId] ?? fallbackOrder
        let lower = min(anchor, target), upper = max(anchor, target)
        let range = Set(self.positions.compactMap { id, order in lower <= order && order <= upper ? id : nil })
        let next = range.subtracting(self.baseline)
        let change = (add: next.subtracting(self.added), remove: self.added.subtracting(next))
        self.added = next
        return change
    }
}

enum NagramiXMessageSelectionColumn {
    static func contains(_ point: CGPoint, leftInset: CGFloat, topInset: CGFloat, bottomInset: CGFloat, height: CGFloat) -> Bool {
        guard point.x.isFinite, point.y.isFinite, height.isFinite, height > topInset + bottomInset else { return false }
        return point.x >= leftInset && point.x <= leftInset + 44.0 && point.y >= topInset && point.y <= height - bottomInset
    }
}

// Separate from Telegram's shared two-finger recognizer. It fails at touch-down
// outside the live checkbox column, so ordinary scrolling acquires that touch.
final class NagramiXMessageDragSelectionRecognizer: UIPanGestureRecognizer {
    var shouldBeginAt: ((CGPoint) -> Bool)?
    private(set) var initialPoint: CGPoint = .zero
    private var receivedInitialTouch = false

    override init(target: Any?, action: Selector?) {
        super.init(target: target, action: action)
        self.minimumNumberOfTouches = 1
        self.maximumNumberOfTouches = 1
        self.allowedTouchTypes = [NSNumber(value: UITouch.TouchType.direct.rawValue)]
    }

    override func reset() {
        super.reset()
        self.initialPoint = .zero
        self.receivedInitialTouch = false
    }

    override func touchesBegan(_ touches: Set<UITouch>, with event: UIEvent) {
        if self.receivedInitialTouch {
            super.touchesBegan(touches, with: event)
            return
        }
        self.receivedInitialTouch = true
        guard let touch = touches.first, self.shouldBeginAt?(touch.location(in: self.view)) == true else {
            self.state = .failed
            return
        }
        self.initialPoint = touch.location(in: self.view)
        super.touchesBegan(touches, with: event)
    }

    override func touchesMoved(_ touches: Set<UITouch>, with event: UIEvent) {
        if self.state == .possible, let touch = touches.first {
            let point = touch.location(in: self.view)
            let dx = abs(point.x - self.initialPoint.x), dy = abs(point.y - self.initialPoint.y)
            if dx >= 8.0 && dx > dy * 1.25 {
                self.state = .failed
                return
            }
            if dy < 5.0 { return }
        }
        super.touchesMoved(touches, with: event)
    }
}
