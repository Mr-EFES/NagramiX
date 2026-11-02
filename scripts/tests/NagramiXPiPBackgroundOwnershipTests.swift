import Foundation

// The harness compiles the actual MediaManager owner setters/update method,
// extracted by validate_pip_runtime.py, with only signal/queue dependencies doubled.
@main private struct Tests {
    static func main() {
        precondition(Thread.isMainThread)
        let manager = MediaManagerHarness()
        let client: PiPMediaManager = manager
        let ordinary = UUID(), first = UUID(), second = UUID()
        var checks = 0
        func expect(_ keep: Bool, _ reason: String) {
            checks += 1
            precondition(manager.keepAudio == keep, reason)
        }
        NagramiXTabSettings.backgroundVideoPlaybackEnabled = false
        expect(false, "cold start has no implicit PiP owner")
        manager.setNagramiXBackgroundVideoPlayback(id: ordinary, active: true)
        expect(false, "background OFF preserves ordinary video policy")
        manager.settingsChanged(true)
        expect(true, "background ON permits ordinary playback")
        manager.settingsChanged(false)
        expect(false, "background OFF remains effective without PiP")
        client.setNagramiXSystemPiPPlayback(id: first, active: true)
        expect(true, "explicit PiP retains session even with background OFF")
        client.setNagramiXSystemPiPPlayback(id: first, active: true)
        expect(true, "duplicate prepare is idempotent")
        client.setNagramiXSystemPiPPlayback(id: second, active: true)
        client.setNagramiXSystemPiPPlayback(id: first, active: false)
        expect(true, "previous PiP stop cannot release next request's session")
        client.setNagramiXSystemPiPPlayback(id: UUID(), active: false)
        expect(true, "stale cleanup cannot release a different owner")
        manager.setNagramiXBackgroundVideoPlayback(id: ordinary, active: false)
        expect(true, "silent PiP has no ordinary audible-video owner")
        manager.settingsChanged(true)
        expect(true, "changing background setting does not interrupt PiP")
        manager.settingsChanged(false)
        expect(true, "PiP remains independent of background OFF")
        client.setNagramiXSystemPiPPlayback(id: second, active: false)
        expect(false, "last PiP cleanup restores native foreground policy")
        client.setNagramiXSystemPiPPlayback(id: second, active: false)
        expect(false, "deinit after release is harmless")
        manager.settingsChanged(true)
        manager.setNagramiXBackgroundVideoPlayback(id: ordinary, active: true)
        client.setNagramiXSystemPiPPlayback(id: ordinary, active: true)
        client.setNagramiXSystemPiPPlayback(id: ordinary, active: false)
        expect(true, "PiP cleanup preserves ordinary owner with same UUID")
        manager.setNagramiXBackgroundVideoPlayback(id: ordinary, active: false)
        expect(false, "ordinary cleanup still works")
        let owners = (0..<8).map { _ in UUID() }
        for id in owners { client.setNagramiXSystemPiPPlayback(id: id, active: true) }
        for (index, id) in owners.enumerated() {
            client.setNagramiXSystemPiPPlayback(id: id, active: false)
            expect(index != owners.count - 1, "independent owner lifetime \(index)")
        }
        precondition(NagramiXTabSettings.backgroundVideoPlaybackEnabled,
                     "PiP never mutates the user's saved preference")
        checks += 1
        print("\(checks) проверок реального MediaManager PiP ownership: PASS")
    }
}
