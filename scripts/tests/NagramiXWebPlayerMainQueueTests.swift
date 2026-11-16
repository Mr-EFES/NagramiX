@main private struct Tests {
    static func main() {
        // Real production FIFO, including synchronous/reentrant callbacks.
        let view = WKWebView()
        var values: [String] = []
        let queue = NagramiXWebJavaScriptQueue { js, done in
            view.evaluateJavaScript(js) { result, _ in done(result) }
        }
        queue.enqueue("play") { value in
            values.append(value as? String ?? "nil")
            queue.enqueue("seek-after-play", completion: nil)
        }
        queue.enqueue("rate") { value in values.append(value as? String ?? "nil") }
        expect(view.scripts == ["play"], "one WebKit evaluation in flight")
        let stale = view.callbacks[0]
        view.complete("started")
        expect(view.scripts == ["play", "rate"], "reentrant enqueue preserves FIFO")
        stale("duplicate", nil)
        expect(view.scripts.count == 2 && values == ["started"], "duplicate callback cannot advance another command")
        view.complete(nil, error: Failure())
        expect(values == ["started", "nil"], "WebKit error delivers nil and drains queue")
        expect(view.scripts == ["play", "rate", "seek-after-play"], "next evaluation after error")
        view.complete()
        queue.enqueue("close") { _ in queue.invalidate(); queue.enqueue("forbidden", completion: nil) }
        queue.enqueue("queued-before-close", completion: nil)
        view.complete()
        expect(view.scripts.last == "close" && view.callbacks.isEmpty, "close in completion cancels pending and reentrant work")

        let pending = WKWebView()
        let qprobe = Probe<NagramiXWebJavaScriptQueue>()
        var cancelled: NagramiXWebJavaScriptQueue? = NagramiXWebJavaScriptQueue { js, done in
            pending.evaluateJavaScript(js) { result, _ in done(result) }
        }
        qprobe.value = cancelled
        cancelled?.enqueue("pending") { _ in expect(false, "invalidated callback must be suppressed") }
        cancelled?.enqueue("never", completion: nil)
        cancelled?.invalidate()
        cancelled = nil
        expect(qprobe.value == nil, "outstanding evaluation does not retain queue")
        pending.complete("late")
        expect(pending.scripts == ["pending"], "late WebKit completion does not restart a closed player")

        let synchronous = Box<NagramiXWebJavaScriptQueue?>(nil)
        var syncScripts: [String] = []
        synchronous.value = NagramiXWebJavaScriptQueue { js, done in
            syncScripts.append(js); done(js)
        }
        synchronous.value?.enqueue("a") { _ in synchronous.value?.enqueue("b", completion: nil) }
        expect(syncScripts == ["a", "b"], "synchronous evaluator preserves callback order")
        synchronous.value?.invalidate(); synchronous.value = nil

        // Execute the actual node enqueue and deinit using real Dispatch queues.
        let ownedView = Box<WKWebView?>(WKWebView())
        let viewProbe = Probe<WKWebView>(); viewProbe.value = ownedView.value
        let owner = Box<Player?>(Player(ownedView.value!))
        let ownerProbe = Probe<Player>(); ownerProbe.value = owner.value
        owner.value?.send("first") { _ in expect(false, "closed player callback must be suppressed") }
        owner.value?.send("second", completion: nil)
        pump { ownedView.value?.scripts.count == 1 }
        let removedBefore = Evidence.removed
        let stoppedBefore = Evidence.stops
        let released = DispatchSemaphore(value: 0)
        DispatchQueue.global().async {
            owner.value = nil  // Texture/SignalKit's final background release.
            released.signal()
        }
        expect(released.wait(timeout: .now() + 5) == .success, "worker release does not block waiting for WebKit")
        expect(ownerProbe.value == nil, "pending JavaScript does not retain player")
        pump { Evidence.removed == removedBefore + 1 }
        expect(Evidence.stops == stoppedBefore + 1, "main-thread cleanup stops WebKit exactly once")
        expect(ownedView.value!.gestureRecognizers!.allSatisfy { !$0.isEnabled }, "existing gesture cleanup preserved")
        ownedView.value?.complete("late")
        expect(ownedView.value?.scripts == ["first"], "no queued evaluation after background destruction")
        ownedView.value = nil
        expect(viewProbe.value == nil, "WebKit graph released on main without debug delay")

        // Last release on main before scheduled enqueue must also be harmless.
        let quickView = WKWebView()
        let quick = Box<Player?>(Player(quickView))
        let quickProbe = Probe<Player>(); quickProbe.value = quick.value
        let enqueued = DispatchSemaphore(value: 0)
        DispatchQueue.global().async {
            quick.value?.send("never-started")
            quick.value = nil
            enqueued.signal()
        }
        expect(enqueued.wait(timeout: .now() + 5) == .success, "worker enqueue remains nonblocking")
        expect(quickProbe.value == nil, "queued enqueue must keep owner weak")
        pump { quickView.callbacks.isEmpty && quickProbe.value == nil }
        _ = RunLoop.current.run(mode: .default, before: Date().addingTimeInterval(0.01))
        expect(quickView.scripts.isEmpty, "weak queued enqueue cannot resurrect closed player")

        // No external view reference may mask final-release thread ownership.
        for _ in 0 ..< 32 {
            let sole = Box<Player?>(Player(WKWebView()))
            let probe = Probe<Player>(); probe.value = sole.value
            let before = Evidence.destroyedViews
            let done = DispatchSemaphore(value: 0)
            DispatchQueue.global().async { sole.value = nil; done.signal() }
            expect(done.wait(timeout: .now() + 5) == .success, "sole graph worker release returns")
            expect(probe.value == nil, "queue-local graph does not keep node alive")
            pump { Evidence.destroyedViews == before + 1 }
        }
        print("Web player main queue: \(Evidence.checks) assertions; real worker release and main RunLoop; FIFO, error, reentrancy, cancellation and late replies passed")
    }
}
