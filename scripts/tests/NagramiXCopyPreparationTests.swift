@main struct CopyPreparationTests {
    static func main() {
        var checks = 0
        func check(_ value: @autoclosure () -> Bool, _ label: String) { if !value() { fatalError("Copy preparation regression: " + label) }; checks += 1 }
        let box = MediaBox()
        var post = Message(); post.media = [TelegramMediaFile(resource: CloudResource("video"))]
        var lease: NagramiXCopyMediaLease?
        var failed = false, progress: [Float] = []
        func listen(_ event: NagramiXCopyMediaPreparationEvent) {
            switch event { case let .ready(value): lease = value; case .failed: failed = true; case let .progress(value): progress.append(value) }
        }
        let ordinary = nagramiXPrepareCopyMedia(mediaBox: box, messages: [post]).start(next: listen)
        check(lease != nil && box.activeFetches == 0 && box.activeKeeps == 0, "ordinary video never waits for download")
        ordinary.dispose(); lease = nil
        post.protected = true
        let downloading = nagramiXPrepareCopyMedia(mediaBox: box, messages: [post, post]).start(next: listen)
        check(box.activeFetches == 1 && box.activeKeeps == 1 && lease == nil, "one deduplicated transfer pins the whole source")
        box.status("video", .Fetching(true, 0.65))
        check(progress.last == 0.65, "real native progress propagated")
        box.emit("video", ResourceData(complete: false))
        check(lease == nil, "partial resource cannot become a ready copy")
        box.emit("video", ResourceData(complete: true))
        check(lease != nil && !failed, "full resource becomes ready")
        check(box.activeFetches == 0 && box.activeKeeps == 1, "completion transfers lease instead of unpinning early")
        downloading.dispose()
        check(box.activeKeeps == 1, "signal disposal does not invalidate delivered lease")
        lease?.dispose(); lease = nil
        check(box.activeKeeps == 0, "recipient staging can release the lease")
        let cancelled = nagramiXPrepareCopyMedia(mediaBox: box, messages: [post]).start(next: listen)
        cancelled.dispose()
        check(box.activeFetches == 0 && box.activeKeeps == 0, "cancel releases fetch and cache pins")
        Scheduler.advance(121)
        check(!failed && lease == nil, "cancelled timeout cannot fire completion")
        let stalled = nagramiXPrepareCopyMedia(mediaBox: box, messages: [post]).start(next: listen)
        Scheduler.advance(100); box.status("video", .Fetching(true, 0.8)); Scheduler.advance(100)
        check(!failed && lease == nil, "active download resets inactivity timeout")
        Scheduler.advance(21)
        check(failed && box.activeFetches == 0 && box.activeKeeps == 0, "stalled download ends visibly and releases resources")
        stalled.dispose(); failed = false
        let broken = nagramiXPrepareCopyMedia(mediaBox: box, messages: [post]).start(next: listen)
        box.errors["video"]?(.failed)
        check(failed && box.activeKeeps == 0, "fetch failure does not leave preparation spinning")
        broken.dispose(); failed = false
        box.complete.insert("video")
        let cached = nagramiXPrepareCopyMedia(mediaBox: box, messages: [post]).start(next: listen)
        check(lease != nil && box.activeFetches == 0 && box.activeKeeps == 1, "cached complete bytes reused without new fetch")
        cached.dispose(); lease?.dispose(); lease = nil
        post.media = [TelegramMediaPaidContent(extendedMedia: [.preview])]
        let locked = nagramiXPrepareCopyMedia(mediaBox: box, messages: [post]).start(next: listen)
        check(failed && box.activeKeeps == 0, "locked paid portion fails without partial send")
        locked.dispose()
        print("Copy preparation real SignalKit checks: \(checks)")
    }
}
