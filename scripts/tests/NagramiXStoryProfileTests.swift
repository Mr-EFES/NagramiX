import Foundation

@main struct StoryProfileTests {
    static func main() throws {
        if CommandLine.arguments.count > 1, ["fresh", "set", "read"].contains(CommandLine.arguments[1]) {
            let value = CommandLine.arguments[2] == "true"
            if CommandLine.arguments[1] == "set" { NagramiXStoryDownloadSettings.setEnabled(value) }
            precondition(NagramiXStoryDownloadSettings.enabled == value)
            _ = UserDefaults.standard.synchronize()
            return
        }
        let baseline = CommandLine.arguments.contains("baseline")
        var checks = 0
        func check(_ value: @autoclosure () -> Bool, _ reason: String) { precondition(value(), reason); checks += 1 }
        func content(_ anonymous: Bool, ready: Bool = true, own: Bool = false) -> StoryContentContext {
            let value = StoryContentContext()
            value.nagramiXAnonymousViewing = anonymous
            if ready { value.stateValue = .init(slice: .init(effectivePeer: EnginePeer(id: own ? 1 : 2), item: .init(id: 9, storyItem: .init(id: 9, media: .image(TelegramMediaImage()))))) }
            return value
        }
        for anonymous in [false, true] {
            for confirm in [false, true] {
                NagramiXTabSettings.current.confirmStoryViewing = confirm
                let host = ViewController()
                var screen: StoryContainerScreen? = StoryContainerScreen(content(anonymous))
                weak var retained = screen
                screen!.nagramiXPush(from: host)
                screen = nil
                let needsConfirmation = anonymous || confirm
                check((retained != nil) == !(baseline && needsConfirmation), "confirmation must own the unpushed screen")
                if needsConfirmation {
                    check(host.pushed == nil && host.confirmation != nil, "tap alone does not open or read a story")
                    host.confirmation!.confirmed()
                    host.confirmation = nil
                }
                check((host.pushed != nil) == !(baseline && needsConfirmation), "acceptance opens the same viewer in ordinary/incognito mode")
                if let pushed = host.pushed {
                    check(pushed.nagramiXAcknowledgedAnonymousViewing == (anonymous && needsConfirmation), "acknowledgment does not change the session mode")
                }
                host.pushed = nil
                check(retained == nil, "navigation and confirmation release the viewer")
            }
        }
        if baseline {
            print("PASS \(checks) baseline checks reproduce dead confirmation in normal and incognito profile stories")
            return
        }
        NagramiXTabSettings.current.confirmStoryViewing = true
        do {
            let host = ViewController()
            var screen: StoryContainerScreen? = StoryContainerScreen(content(true))
            weak var retained = screen
            screen!.nagramiXPush(from: host); screen = nil
            check(retained != nil, "confirmation owns its pending viewer")
            host.confirmation!.cancelled(); host.confirmation = nil
            check(retained == nil && host.pushed == nil, "cancel releases without opening")
        }
        do {
            let host = ViewController(), pending = content(true, ready: false)
            var screen: StoryContainerScreen? = StoryContainerScreen(pending)
            weak var retained = screen
            screen!.nagramiXPush(from: host); screen = nil
            check(retained != nil, "first-state wait retains viewer")
            pending.subscriber!.putNext(content(true).stateValue!)
            check(host.confirmation != nil && retained != nil, "ownership transfers from subscription to confirmation")
            host.confirmation!.confirmed(); host.confirmation = nil
            check(host.pushed === retained, "late first state opens the selected viewer")
            host.pushed = nil
            check(retained == nil, "completed pending subscription has no retain cycle")
        }
        do {
            let host = ViewController(), pending = content(false, ready: false)
            var screen: StoryContainerScreen? = StoryContainerScreen(pending)
            weak var retained = screen
            screen!.nagramiXPush(from: host); screen = nil
            Timer.fire(30)
            check(retained == nil && host.confirmation == nil && host.pushed == nil, "unavailable source times out without leaking or opening")
        }
        do {
            let host = ViewController(), screen = StoryContainerScreen(content(true, own: true))
            screen.nagramiXPush(from: host)
            check(host.pushed === screen && host.confirmation == nil, "own story keeps native no-confirmation behavior")
        }
        do {
            let screen = StoryContainerScreen(content(false))
            check(!screen.nagramiXCanMarkStoryAsSeen(9), "unapproved story cannot be marked seen")
            screen.nagramiXApprovedStoryId = 9
            check(screen.nagramiXCanMarkStoryAsSeen(9), "approved ID is accepted")
            check(!screen.nagramiXCanMarkStoryAsSeen(9), "approval is consumed exactly once")
        }

        final class Events { var values: [Float] = []; var error: NagramiXStorySaveError?; var completed = 0 }
        let directory = URL(fileURLWithPath: NSTemporaryDirectory()).appendingPathComponent(UUID().uuidString)
        try FileManager.default.createDirectory(at: directory, withIntermediateDirectories: true)
        defer { try? FileManager.default.removeItem(at: directory) }
        func fixture(_ media: Any = TelegramMediaImage(), delayed: Bool = false, fetchError: Bool = false, missingFile: Bool = false) throws -> (AccountContext, Events, Disposable) {
            DeviceAccess.allowed = true; DeviceAccess.deferred = delayed; DeviceAccess.pending = nil
            let context = AccountContext(), events = Events()
            let file = directory.appendingPathComponent(UUID().uuidString)
            if !missingFile { try Data("full-story-resource".utf8).write(to: file) }
            context.engine.resources.path = file.path
            context.engine.resources.failFetch = fetchError
            let disposable = nagramiXSaveStoryToCameraRoll(context: context, userLocation: .peer(2), mediaReference: .init(media: media)).start(next: { events.values.append($0) }, error: { events.error = $0 }, completed: { events.completed += 1 })
            return (context, events, disposable)
        }
        for photo in [true, false] {
            let (context, events, disposable) = try fixture(photo ? TelegramMediaImage() : TelegramMediaFile())
            check(events.completed == 0 && !events.values.contains(1), "download completion is not a Photos success")
            Queue.drain()
            let saved = PHAssetCreationRequest.resource!
            check(saved.0 == (photo ? .photo : .video), "correct Photos resource type")
            try FileManager.default.removeItem(atPath: context.engine.resources.path)
            check(try! Data(contentsOf: saved.1) == Data("full-story-resource".utf8), "pinned bytes survive cache removal")
            PHPhotoLibrary.shared().finish(true)
            check(events.values.last == 1 && events.completed == 1 && events.error == nil, "only Photos commit completes save")
            check(!FileManager.default.fileExists(atPath: saved.1.path), "temporary file removed after Photos completion")
            disposable.dispose()
        }
        for media: Any in [TelegramMediaImage(false), TelegramMediaFile(false), "unsupported"] {
            let before = PHPhotoLibrary.shared().calls
            let (_, events, disposable) = try fixture(media)
            Queue.drain()
            check(events.error == .unavailable && events.completed == 0 && PHPhotoLibrary.shared().calls == before, "unsupported/empty media never reports success")
            disposable.dispose()
        }
        for missing in [false, true] {
            let (_, events, disposable) = try fixture(fetchError: !missing, missingFile: missing)
            let before = PHPhotoLibrary.shared().calls
            Queue.drain()
            check(events.error == .unavailable && events.completed == 0 && PHPhotoLibrary.shared().calls == before, "fetch/file failure does not write an empty asset")
            disposable.dispose()
        }
        for cancel in [false, true] {
            let (context, events, disposable) = try fixture(delayed: true)
            let before = PHPhotoLibrary.shared().calls
            if cancel { disposable.dispose() }
            DeviceAccess.pending!(cancel)
            DeviceAccess.pending = nil
            Queue.drain()
            check(context.engine.resources.fetches == 0 && PHPhotoLibrary.shared().calls == before && events.completed == 0, "denial/cancel before permission does not fetch or save")
            check(events.error == (cancel ? nil : .permissionDenied), "permission denial has an explicit result")
            disposable.dispose()
        }
        do {
            let (_, events, disposable) = try fixture()
            let before = PHPhotoLibrary.shared().calls
            disposable.dispose(); Queue.drain()
            check(PHPhotoLibrary.shared().calls == before && events.completed == 0, "cancel queued work before Photos")
        }
        for success in [true, false] {
            let (_, events, disposable) = try fixture()
            Queue.drain()
            let file = PHAssetCreationRequest.resource!.1
            if success { disposable.dispose() }
            check(FileManager.default.fileExists(atPath: file.path), "Photos keeps pinned file while in flight")
            PHPhotoLibrary.shared().finish(success)
            check(!FileManager.default.fileExists(atPath: file.path), "in-flight cleanup also runs after cancel/error")
            check(events.completed == 0 && events.error == (success ? nil : .library), "cancel/library error never presents saved state")
            disposable.dispose()
        }
        do {
            let (_, events, disposable) = try fixture()
            Queue.drain()
            PHPhotoLibrary.shared().finish(true, error: FetchError.failed)
            check(events.error == .library && events.completed == 0, "Photos error must not be hidden by a success flag")
            disposable.dispose()
        }
        print("PASS \(checks) production story lifetime/save checks; real SwiftSignalKit and files, OS boundaries simulated")
    }
}
