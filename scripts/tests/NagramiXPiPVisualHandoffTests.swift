import Foundation

@main struct PiPVisualHandoffTests {
    final class Fixture {
        var hidden = false
        var previews: [Bool] = []
        var out: [() -> Void] = []
        var into: [() -> Void] = []
        var dismissals = 0
        var animatedReturns: [Bool] = []
        lazy var visual = NagramiXPiPVisualHandoff(preview: { [weak self] in self?.previews.append($0) },
            fadeOut: { [weak self] done in self?.hidden = true; self?.out.append(done) },
            fadeIn: { [weak self] animated, done in self?.hidden = false; self?.animatedReturns.append(animated); self?.into.append(done) },
            dismiss: { [weak self] in self?.dismissals += 1 })
    }
    static func main() {
        var checks = 0
        func check(_ value: @autoclosure () -> Bool, _ label: String) { precondition(value(), label); checks += 1 }
        for fadeFirst in [false, true] {
            let f = Fixture(); f.visual.willStart()
            check(f.hidden, "willStart hides the duplicate source with native transition")
            check(f.dismissals == 0 && f.previews == [true], "willStart does not prematurely dismiss gallery")
            f.visual.willStart(); check(f.out.count == 1, "duplicate willStart does not start another fade")
            if fadeFirst {
                f.out[0](); check(f.dismissals == 0, "fading alone cannot commit failed PiP")
                f.visual.commit()
            } else {
                f.visual.commit(); check(f.dismissals == 0, "native success waits for the already-running fade")
                f.out[0]()
            }
            check(f.dismissals == 1 && f.previews == [true, false], "one dismissal after both conditions")
            f.visual.commit(); f.out[0](); f.visual.willStart()
            check(f.dismissals == 1 && f.out.count == 1, "duplicate callbacks do not create a second transition")
            f.visual.cancel(); check(f.hidden && f.into.isEmpty, "resource release cannot roll back a committed native player")
        }
        for fadeFinished in [false, true] {
            let f = Fixture(); f.visual.willStart(); if fadeFinished { f.out[0]() }
            f.visual.cancel()
            check(!f.hidden && f.dismissals == 0 && f.animatedReturns == [true], "failure returns the still-present gallery")
            f.out[0](); check(f.dismissals == 0, "stale fade completion cannot dismiss after failure")
            check(f.previews == [true], "keep poster until failed-transition return finishes")
            f.into[0](); check(f.previews == [true, false], "rollback releases its own poster lease")
        }
        do {
            let f = Fixture(); f.visual.cancel()
            check(f.into.isEmpty && f.previews.isEmpty, "failure before willStart changes no presentation")
            f.visual.commit(); check(f.hidden && f.out.count == 1, "didStart-only fallback uses the same visual path")
            f.out[0](); check(f.dismissals == 1, "fallback has exactly one dismissal")
        }
        for fadeFinished in [false, true] {
            let f = Fixture(); f.visual.willStart(); f.visual.commit()
            if fadeFinished { f.out[0]() }
            let count = f.dismissals
            f.visual.restore()
            check(!f.hidden && f.animatedReturns == [false], "Expand immediately presents source for native return")
            f.out[0](); f.visual.commit(); f.visual.willStart()
            check(f.dismissals == count, "Expand cannot be closed by late outgoing fade")
        }
        do {
            let f = Fixture(); f.visual.willStart(); f.visual.cancel()
            f.visual.willStart(); f.into[0]()
            check(f.previews == [true, true], "old rollback cannot clear preview of a new transition")
            f.out[0](); f.visual.commit()
            check(f.dismissals == 0, "old fade cannot satisfy a new native handoff")
            f.out[1](); check(f.dismissals == 1, "new generation waits for its own fade")
        }
        // Actual generated GalleryController setter and source-map closure,
        // with the real upstream Promise/ValuePromise/combineLatest operators.
        let gallery = GalleryPreviewHarness()
        let gesture = UUID(), native = UUID(), other = UUID()
        let original = TestMedia(id: 10)
        gallery.hiddenMedia.set(.single((1, original)))
        var hidden: [GalleryHiddenMediaId?] = []
        let d = gallery.source().start(next: { hidden.append($0) })
        check(hidden == [.chat(5, 1, original)], "normal gallery hides its source as before")
        gallery.nagramiXSetPiPSourcePreview(owner: gesture, visible: true)
        check(hidden.last! == nil, "drag immediately reveals static source poster")
        gallery.nagramiXSetPiPSourcePreview(owner: native, visible: true)
        gallery.nagramiXSetPiPSourcePreview(owner: gesture, visible: false)
        check(hidden.last! == nil, "gesture cleanup does not revoke active native preview")
        gallery.nagramiXSetPiPSourcePreview(owner: other, visible: false)
        check(hidden.last! == nil, "unrelated owner cannot revoke preview")
        gallery.nagramiXSetPiPSourcePreview(owner: native, visible: false)
        check(hidden.last! == .chat(5, 1, original), "last owner restores original hide request on cancellation")
        gallery.nagramiXSetPiPSourcePreview(owner: gesture, visible: true)
        gallery.hiddenMedia.set(.single((2, TestMedia(id: 20))))
        check(hidden.last! == nil, "source change remains revealed while preview is leased")
        gallery.nagramiXSetPiPSourcePreview(owner: gesture, visible: false)
        check(hidden.last! == .chat(5, 2, TestMedia(id: 20)), "cancellation hides current source, not a stale captured message")
        gallery.nagramiXSetPiPSourcePreview(owner: gesture, visible: true)
        gallery.hiddenMedia.set(.single(nil))
        gallery.nagramiXSetPiPSourcePreview(owner: gesture, visible: false)
        check(hidden.last! == nil, "committed dismissal does not resurrect old hidden media")
        d.dispose()
        print("PASS: \(checks) PiP visual callback ordering/rollback/restore and real SignalKit preview checks")
    }
}
