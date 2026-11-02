import Foundation

@main private struct Tests {
    static func main() {
        typealias Policy = NagramiXPiPAudioPolicy
        var checks = 0
        func expect(_ active: Bool, _ category: Policy.Category, _ elapsed: Double, _ requested: Bool, _ expected: Bool, _ scenario: String) {
            checks += 1
            precondition(Policy.needsPlaybackLease(managedPlaybackActive: active, category: category,
                elapsed: elapsed, alreadyRequested: requested) == expected, scenario)
        }
        expect(true, .playback, 0.5, false, false, "playing video's own audio must not be preempted")
        expect(true, .ambient, 0.5, false, true, "ambient isPlay flag is not PiP playback readiness")
        expect(true, .other, 0.5, false, true, "unrelated ambient-like session cannot block silent PiP forever")
        expect(false, .playback, 0.5, false, true, "inactive playback category requires activation")
        expect(false, .ambient, 0.5, false, true, "silent clip receives managed activation")
        expect(false, .playAndRecord, 10, false, false, "do not acquire over a call or recording")
        expect(true, .playAndRecord, 10, false, false, "do not borrow a record route even if marked playing")
        expect(false, .other, 0, false, false, "allow original renderer activation first")
        expect(false, .ambient, 0.499, false, false, "activation grace period")
        expect(false, .ambient, 0.5, true, false, "one lease per request")
        expect(false, .playback, 5, true, false, "repeated readiness does not duplicate holder")
        expect(false, .other, -.infinity, false, false, "invalid elapsed time")
        expect(false, .other, .infinity, false, false, "infinite elapsed time")
        expect(false, .other, .nan, false, false, "NaN elapsed time")
        expect(false, .ambient, -1, false, false, "negative elapsed time")
        // Native renderer activation wins during the grace period: the next
        // check reuses it instead of adding a competing audio holder.
        expect(false, .ambient, 0.1, false, false, "cold activation pending")
        expect(true, .playback, 0.6, false, false, "renderer activated before fallback")
        for (active, category, ready) in [
            (true, Policy.Category.playback, true), (false, .playback, false),
            (true, .ambient, false), (false, .ambient, false),
            (true, .playAndRecord, true), (false, .playAndRecord, false),
            (true, .other, false), (false, .other, false)
        ] {
            checks += 1
            precondition(Policy.isReady(managedPlaybackActive: active, category: category) == ready,
                         "AVKit possible cannot bypass real playback audio readiness")
        }
        print("\(checks) проверок аудиоготовности PiP: PASS")
    }
}
