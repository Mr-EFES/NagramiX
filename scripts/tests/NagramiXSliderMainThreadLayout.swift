@main struct SliderMainThreadLayoutTests {
    static func requestWorkerLayout(_ views: [UIView]) {
        let finished = DispatchSemaphore(value: 0)
        DispatchQueue.global().async {
            for _ in 0..<3 {
                for view in views { view.layoutSubviews() }
            }
            finished.signal()
        }
        check(finished.wait(timeout: .now() + 5) == .success, "worker layout returned without waiting for the main thread")
    }

    static func main() {
        let cell = NagramiXRoundBitRateCell(presentationData: PresentationData())
        let slider = cell.slider
        let thumb = slider.glassThumbView
        let views = [slider as UIView, thumb]
        for view in views {
            view.setNeedsLayout()
            view.layoutIfNeeded()
            check(view.nativeLayoutCount == 1, "normal layout reaches UIKit synchronously")
        }

        requestWorkerLayout(views)
        check(views.allSatisfy { $0.nativeLayoutCount == 1 && !$0.layoutRequested }, "worker touched UIKit")
        let drained = DispatchSemaphore(value: 0)
        DispatchQueue.main.async { drained.signal() }
        let deadline = Date().addingTimeInterval(5)
        while drained.wait(timeout: .now()) != .success && Date() < deadline {
            RunLoop.main.run(until: Date().addingTimeInterval(0.01))
        }
        check(views.allSatisfy { $0.layoutRequested }, "deferred layout was lost")
        slider.bounds = CGRect(x: 0, y: 0, width: 240, height: 44)
        cell.update(.init(enabled: true, bitRate: 1_300_000))
        for view in views {
            view.layoutIfNeeded()
            view.layoutIfNeeded()
            check(view.nativeLayoutCount == 2, "repeated worker callbacks must coalesce into one pass")
        }
        let track = slider.trackRect(forBounds: slider.bounds)
        let expected = slider.thumbRect(forBounds: slider.bounds, trackRect: track, value: 3)
        check(thumb.frame == expected && slider.value == 3, "deferred layout must use the latest width and bitrate")
        RoundBitrateControlTests.main()
    }
}
