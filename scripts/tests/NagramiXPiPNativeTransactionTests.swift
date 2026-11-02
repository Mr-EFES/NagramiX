import Foundation

@main struct NativeTransactionTests {
    final class Owner {
        var validate: (() -> Bool)?
        var acquirePrevious: (() -> Bool)?
        var rollbackTransition: () -> Void = {}
        var nagramiXReadinessReason = "avkit_unavailable"
        var now = 0.0
        var ready = NagramiXPiPLifecycle.Readiness.ready
        var active = false
        var stopCalls = 0
        var releaseCalls = 0
        var result: Bool?
        var rollbacks = 0
        var dismissals = 0
        var faded = false
        var fadeCompletion: (() -> Void)?
        lazy var visual = NagramiXPiPVisualHandoff(preview: { _ in }, fadeOut: { [unowned self] callback in
            self.faded = true; self.fadeCompletion = callback
        }, fadeIn: { [unowned self] _, callback in self.faded = false; callback() }, dismiss: { [unowned self] in self.dismissals += 1 })
        lazy var lifecycle: NagramiXPiPLifecycle = NagramiXPiPLifecycle(now: { [unowned self] in self.now }, valid: { [unowned self] in self.validate?() == true },
            prepare: {}, readiness: { [unowned self] in self.ready }, nativeActive: { [unowned self] in self.active },
            start: {}, stop: { [unowned self] in self.stopCalls += 1 }, commit: { [unowned self] in self.visual.commit(); return true },
            restore: { [unowned self] completion in self.visual.restore(); completion(true) },
            release: { [unowned self] in self.releaseCalls += 1; if !self.lifecycle.transferred { self.rollbackTransition() } },
            ended: { _ in }, changed: {})
        init() { rollbackTransition = { [unowned self] in self.rollbacks += 1; self.visual.cancel() } }
        // START_METHOD
        func begin() {
            precondition(start(acquirePrevious: { true }, validate: { true }, completion: { [unowned self] value in
                if !value { precondition(!self.faded && self.rollbacks > 0, "rollback before completion") }
                self.result = value
            }))
        }
    }
    static func main() {
        // Success cannot wait forever for an interrupted CoreAnimation callback.
        for order in 0..<3 {
            let o = Owner(); o.begin()
            if order != 2 { o.visual.willStart() }
            if order == 1 { o.fadeCompletion?() }
            o.active = true; o.lifecycle.didStart()
            precondition(o.result == true && o.dismissals == 1, "native success must dismiss without fade completion")
            o.fadeCompletion?(); o.lifecycle.didStart()
            precondition(o.dismissals == 1)
        }
        do {
            let o = Owner(); o.begin(); o.visual.willStart()
            o.now = 8.1; o.lifecycle.update()
            precondition(o.lifecycle.phase == .stopping && o.result == false)
            precondition(!o.faded && o.releaseCalls == 0 && o.stopCalls == 1)
            o.fadeCompletion?(); precondition(o.dismissals == 0)
            o.now = 12.2; o.lifecycle.update()
            precondition(o.lifecycle.phase == .finished && o.releaseCalls == 1)
        }
        do {
            let o = Owner(); o.ready = .waiting; o.begin()
            o.now = 8.1; o.lifecycle.update()
            precondition(o.result == false && o.lifecycle.phase == .finished && o.dismissals == 0)
        }
        do {
            let o = Owner(); o.begin(); o.visual.willStart(); o.lifecycle.failedToStart()
            precondition(o.result == false && !o.faded && o.dismissals == 0)
        }
        do {
            let o = Owner(); o.begin(); o.visual.willStart()
            o.active = true; o.lifecycle.didStart()
            o.lifecycle.restoreInterface { precondition($0) }
            precondition(!o.faded && o.lifecycle.restored)
            o.fadeCompletion?(); precondition(o.dismissals == 1)
        }
        print("PASS: production start wrapper/lifecycle/visual; didStart without fade callback, duplicate delegates, immediate timeout rollback before stop grace, error/Expand")
    }
}
