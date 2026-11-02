import Foundation

private var checks = 0
private func expect(_ value: @autoclosure () -> Bool, _ message: String) {
    checks += 1
    precondition(value(), message)
}

private final class Rig {
    var now = 0.0
    var valid = true
    var ready: NagramiXPiPLifecycle.Readiness = .waiting
    var active = false
    var commitAllowed = true
    var events: [String] = []
    var results: [Bool] = []
    var restoreResults: [Bool] = []
    var restoreCompletion: ((Bool) -> Void)?
    var onStart: (() -> Void)?
    var onCommit: (() -> Void)?
    var onReadiness: (() -> Void)?
    var onRelease: (() -> Void)?
    lazy var flow = NagramiXPiPLifecycle(now: { self.now }, valid: { self.valid },
        prepare: { self.events.append("prepare") }, readiness: {
            self.onReadiness?(); return self.ready
        }, nativeActive: { self.active }, start: {
            self.events.append("start"); self.onStart?()
        }, stop: { self.events.append("stop") }, commit: {
            self.events.append("commit"); self.onCommit?(); return self.commitAllowed
        }, restore: { completion in self.events.append("restore"); self.restoreCompletion = completion },
        release: { self.events.append("release"); self.onRelease?() },
        ended: { restored in self.events.append(restored ? "restored" : "closed") }, changed: {})
    func begin() { expect(self.flow.begin(timeout: 8) { self.results.append($0) }, "request accepted") }
    func start() {
        self.ready = .ready; self.begin()
        expect(self.flow.phase == .starting, "wait for confirmed native start")
        self.active = true; self.flow.didStart()
        expect(self.results == [true], "successful result once")
    }
    func restore() { self.flow.restoreInterface { self.restoreResults.append($0) } }
}

@main private struct Tests {
    static func main() {
        do {
            let r = Rig(); r.begin()
            expect(r.events == ["prepare"], "preparation cannot dismiss gallery")
            for _ in 0..<100 { r.flow.update() }
            expect(r.events == ["prepare"], "readiness polling cannot duplicate start")
            r.ready = .ready; r.flow.update(); r.flow.update()
            expect(r.events == ["prepare", "start"], "one native start")
            expect(r.results.isEmpty, "start call is not success")
            r.active = true; r.flow.didStart(); r.flow.didStart()
            expect(r.events == ["prepare", "start", "commit"], "one transfer after didStart")
            expect(!r.flow.needsTimer, "no polling during active playback")
            r.flow.didStop(); r.flow.didStop()
            expect(r.events.suffix(2) == ["release", "closed"], "one cleanup and close")
            expect(r.results == [true], "stop cannot invert delivered success")
        }
        do {
            let r = Rig(); r.begin(); r.flow.cancelPreparation()
            r.ready = .ready; r.flow.update(); r.flow.didStart()
            expect(r.events == ["prepare", "release"], "cancel before readiness cannot start")
            expect(r.results == [false], "cancel completes once")
            expect(!r.flow.needsTimer, "cancel releases timer")
        }
        for invalid in [true, false] {
            let r = Rig(); r.begin()
            if invalid { r.valid = false } else { r.now = 8 }
            r.flow.update()
            expect(r.results == [false] && r.events == ["prepare", "release"], "source loss / waiting timeout")
        }
        do {
            let r = Rig(); r.ready = .ready; r.begin(); r.flow.cancelPreparation()
            expect(r.flow.phase == .starting, "resign-active cancellation preserves native animation")
            r.flow.failedToStart(); r.flow.failedToStart()
            expect(r.results == [false], "native failure once")
            expect(r.events.filter { $0 == "release" }.count == 1, "failure cleanup once")
        }
        do {
            let r = Rig(); r.ready = .ready; r.begin(); r.valid = false; r.flow.update()
            expect(r.flow.phase == .stopping && r.results == [false], "structural invalidation stops in-flight start")
            expect(!r.events.contains("release"), "retain source until native stop")
            r.active = true; r.flow.didStart()
            expect(r.events.filter { $0 == "stop" }.count == 2, "late start stopped again")
            expect(!r.events.contains("commit"), "late start cannot dismiss a different gallery")
            r.active = false; r.flow.didStop()
            expect(r.events.last == "release", "late native stop cleans source")
        }
        do {
            let r = Rig(); r.begin(); r.now = 7.9; r.ready = .ready; r.flow.update()
            r.now = 8.1; r.flow.update()
            expect(r.flow.phase == .starting && r.results.isEmpty, "native start gets its own timeout after slow preparation")
            r.now = 15.9; r.flow.update()
            expect(r.flow.phase == .stopping && r.results == [false], "native timeout remains bounded")
        }
        do {
            let r = Rig(); r.ready = .ready; r.begin(); r.now = 8; r.flow.update()
            expect(r.flow.phase == .stopping, "start timeout requests stop")
            r.now = 12; r.flow.update()
            expect(r.flow.phase == .finished && r.results == [false], "missing callbacks cannot retain indefinitely")
        }
        do {
            let r = Rig(); r.ready = .ready; r.begin(); r.active = true; r.now = 8; r.flow.update()
            expect(r.results == [true], "confirmed active recovers a delayed didStart")
        }
        do {
            let r = Rig(); r.onStart = { r.active = true; r.flow.didStart() }; r.ready = .ready; r.begin()
            expect(r.results == [true], "synchronous delegate supported")
        }
        do {
            let r = Rig(); r.ready = .ready; r.onReadiness = { r.flow.cancelPreparation() }; r.begin()
            expect(!r.events.contains("start") && r.results == [false], "reentrant readiness cancellation")
        }
        do {
            let r = Rig(); r.ready = .ready; r.begin()
            r.onCommit = { r.flow.didStop() }; r.active = true; r.flow.didStart()
            expect(r.results == [false], "stop during transfer cannot report successful PiP")
            expect(r.events.suffix(2) == ["release", "closed"], "reentrant stop during transfer still releases owner")
        }
        do {
            let r = Rig(); r.commitAllowed = false; r.ready = .ready; r.begin(); r.active = true; r.flow.didStart()
            expect(r.results == [false] && r.flow.phase == .stopping, "failed gallery transfer stops native PiP")
            r.flow.didStop()
            expect(!r.events.contains("closed"), "no transferred gallery owner on rejected commit")
        }
        for stopFirst in [true, false] {
            let r = Rig(); r.start(); r.restore(); r.restore()
            expect(r.events.filter { $0 == "restore" }.count == 1, "duplicate restore coalesced")
            expect(r.flow.needsTimer, "restore has bounded completion")
            if stopFirst {
                r.flow.didStop()
                expect(!r.events.contains("release"), "restore retains source across early didStop")
            }
            r.restoreCompletion?(true)
            if !stopFirst { r.flow.didStop() }
            expect(r.restoreResults == [true, true], "every restore completion once")
            expect(r.events.suffix(2) == ["release", "restored"], "restore/stop ordering preserves playback")
            expect(!r.flow.needsTimer, "restored session timer cleared")
            r.restoreCompletion?(false)
            expect(r.restoreResults == [true, true], "late restore completion ignored")
        }
        do {
            let r = Rig(); r.start(); r.restore(); r.flow.didStop(); r.now = 5; r.flow.update()
            expect(r.restoreResults == [false], "restore timeout completes AVKit callback")
            expect(r.events.suffix(2) == ["release", "closed"], "failed restore releases hidden owner")
        }
        do {
            let r = Rig(); r.start(); r.restore(); r.restoreCompletion?(false)
            expect(r.flow.phase == .active, "failed restore leaves existing native PiP usable")
            r.restore(); r.restoreCompletion?(true)
            expect(r.restoreResults == [false, true], "restore can be retried")
        }
        do {
            let r = Rig(); r.start(); r.flow.stopRequested(); r.flow.stopRequested()
            expect(r.events.filter { $0 == "stop" }.count == 1, "stop idempotent")
            r.flow.didStop()
            expect(r.events.suffix(2) == ["release", "closed"], "close releases decoder")
        }
        // Every callback ordering after a rejected request remains inert. These
        // are real production transitions, not a second model of the algorithm.
        for mask in 0..<256 {
            let r = Rig(); r.begin(); r.flow.cancelPreparation()
            for shift in 0..<4 {
                switch (mask >> (shift * 2)) & 3 {
                case 0: r.flow.didStart()
                case 1: r.flow.didStop()
                case 2: r.flow.failedToStart()
                default: r.flow.update()
                }
            }
            expect(r.events == ["prepare", "release"] && r.results == [false], "retired callback ordering \(mask)")
        }
        print("\(checks) проверок жизненного цикла PiP: PASS")
    }
}
