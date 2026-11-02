private final class Player {
    var possible = false
    var active = false
    var valid = true
    var allowTransfer = true
    var prepares = 0
    var starts = 0
    var stops = 0
    var transfers = 0
    var releases = 0
    var ends = 0
    var outcomes: [Bool] = []
    var onStart: (() -> Void)?
    var onTransfer: (() -> Void)?
    lazy var session = NagramiXPiPPlaybackSession(
        prepare: { [unowned self] in self.prepares += 1 },
        possible: { [unowned self] in self.possible },
        active: { [unowned self] in self.active },
        start: { [unowned self] in self.starts += 1; self.onStart?() },
        stop: { [unowned self] in self.stops += 1 },
        transfer: { [unowned self] in self.transfers += 1; self.onTransfer?(); return self.allowTransfer },
        release: { [unowned self] in self.releases += 1 },
        ended: { [unowned self] in self.ends += 1 }
    )
    @discardableResult func request() -> Bool {
        self.session.request(validate: { [unowned self] in self.valid }, completion: { [unowned self] in self.outcomes.append($0) })
    }
}

@main struct PiPPlaybackSessionTests {
    static func main() {
        var checks = 0
        func check(_ value: @autoclosure () -> Bool, _ name: String) {
            precondition(value(), name); checks += 1
        }
        // Both production entry points call this actual lifecycle, not a gesture formula.
        for entry in ["button", "swipe"] {
            let p = Player()
            check(p.request(), entry + " accepted")
            check(p.session.phase == .waiting && p.starts == 0 && p.transfers == 0, "cold readiness")
            p.possible = true; p.session.readinessChanged()
            check(p.starts == 1 && p.transfers == 0 && p.outcomes.isEmpty, "willStart is not success")
            p.session.readinessChanged(); check(p.starts == 1, "KVO does not duplicate start")
            p.active = true; p.session.didStart()
            check(p.session.phase == .active && p.transfers == 1 && p.outcomes == [true], "native acknowledgement")
            p.session.didStart(); check(p.transfers == 1, "duplicate acknowledgement")
            p.session.cancelPreparation(); check(p.session.phase == .active && p.stops == 0, "active lifetime")
            p.session.didStop(); p.session.didStop()
            check(p.session.phase == .idle && p.releases == 1 && p.ends == 1 && p.outcomes == [true], "end once")
        }
        let failed = Player(); failed.possible = true; failed.request(); failed.session.failedToStart()
        check(failed.transfers == 0 && failed.releases == 1 && failed.outcomes == [false], "failure preserves gallery")
        check(failed.session.phase == .idle, "failure cannot leave PiP occupied")
        failed.session.didStart(); check(failed.transfers == 0, "late start after failure")
        check(failed.request() && failed.starts == 2, "explicit retry")

        let timeout = Player(); timeout.request(); timeout.session.timedOut()
        check(timeout.starts == 0 && timeout.transfers == 0 && timeout.outcomes == [false], "readiness timeout")
        timeout.possible = true; timeout.session.readinessChanged(); check(timeout.starts == 0, "no late auto start")

        let startTimeout = Player(); startTimeout.possible = true; startTimeout.request(); startTimeout.session.timedOut()
        check(startTimeout.stops == 1 && startTimeout.outcomes == [false], "native start timeout")

        let delayed = Player(); delayed.possible = true; delayed.request(); delayed.active = true; delayed.session.timedOut()
        check(delayed.transfers == 1 && delayed.outcomes == [true], "delayed delegate with active AVKit")
        delayed.session.didStart(); check(delayed.transfers == 1, "delayed delegate once")

        let canceled = Player(); canceled.request(); canceled.session.cancelPreparation()
        check(canceled.outcomes == [false] && canceled.releases == 1, "cancel waiting")

        let foreground = Player(); foreground.possible = true; foreground.request(); foreground.session.cancelPreparation()
        check(foreground.session.phase == .starting && foreground.stops == 0, "do not cancel iOS presentation")
        foreground.session.didStart(); check(foreground.outcomes == [true], "presentation finishes")

        let stale = Player(); stale.request(); stale.valid = false; stale.possible = true; stale.session.readinessChanged()
        check(stale.starts == 0 && stale.outcomes == [false], "stale source before ready")
        let changed = Player(); changed.possible = true; changed.request(); changed.valid = false; changed.session.didStart()
        check(changed.transfers == 0 && changed.stops == 1 && changed.outcomes == [false], "stale source after native start")

        let invalid = Player(); invalid.valid = false
        check(!invalid.request() && invalid.prepares == 0, "ineligible request")
        let double = Player(); double.request()
        check(!double.request() && double.prepares == 1, "one pending request")

        let refused = Player(); refused.possible = true; refused.allowTransfer = false; refused.request(); refused.session.didStart()
        check(refused.stops == 1 && refused.releases == 1 && refused.outcomes == [false], "UI transfer refused")

        let synchronous = Player(); synchronous.possible = true
        synchronous.onStart = { [unowned synchronous] in synchronous.session.didStart() }
        synchronous.request()
        check(synchronous.outcomes == [true] && synchronous.transfers == 1, "synchronous native callback")

        let reentrant = Player(); reentrant.possible = true
        reentrant.onTransfer = { [unowned reentrant] in reentrant.session.didStop() }
        reentrant.request(); reentrant.session.didStart()
        check(reentrant.session.phase == .idle && reentrant.outcomes == [false] && reentrant.releases == 1, "stop during transfer")
        print("PASS: \(checks) PiP lifecycle checks")
    }
}
