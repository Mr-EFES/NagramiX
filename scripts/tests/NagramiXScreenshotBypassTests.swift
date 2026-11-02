import Foundation

// UIKit/AVFoundation and encrypted enqueue are boundary doubles. The settings,
// registry, message eligibility and engine method are production code.
public class CALayer: NSObject {
    var disabled = false
    var writes = 0
}
public class AVSampleBufferDisplayLayer: CALayer {
    var preventsCapture = false { didSet { writes += 1 } }
}
func setLayerDisableScreenshots(_ layer: CALayer, _ required: Bool) {
    layer.disabled = required
    layer.writes += 1
}
public struct TestPeerId { let isVerificationCodes: Bool }
public struct TestMessageId { let peerId: TestPeerId }
public struct Message {
    let containsSecretMedia: Bool
    let minAutoremoveOrClearTimeout: Int32?
    let paidContent: Int?
    let id: TestMessageId
}
let viewOnceTimeout = Int32.max
public enum NoError {}
public struct Signal<T, E> { static func complete() -> Self { Self() } }
infix operator |> : AdditionPrecedence
func |> <A, B>(value: A, transform: (A) -> B) -> B { transform(value) }
func ignoreValues<T, E>(_ signal: Signal<T, E>) -> Signal<Never, E> { .complete() }
public typealias PeerId = Int
final class ScreenshotAccount { var calls: [PeerId] = [] }
func _internal_addSecretChatMessageScreenshot(account: ScreenshotAccount, peerId: PeerId) -> Signal<Never, NoError> {
    account.calls.append(peerId)
    return .complete()
}

@main struct ScreenshotBypassTests {
    static func main() {
        let args = CommandLine.arguments
        if args.count == 4 && args[1] == "--set" {
            let defaults = UserDefaults(suiteName: args[2])!
            NagramiXPrivacySettings.update(in: defaults) { $0[.screenshotBypass] = args[3] == "true" }
            defaults.synchronize()
            return
        }
        if args.count == 4 && args[1] == "--cold" {
            let settings = NagramiXPrivacySettings.read(from: UserDefaults(suiteName: args[2])!)
            precondition(settings.bypassScreenshots == (args[3] == "true"))
            return
        }
        var checks = 0
        func check(_ value: @autoclosure () -> Bool, _ name: String) { precondition(value(), name); checks += 1 }
        let fresh = NagramiXPrivacySettings.current
        check(!fresh.bypassScreenshots && fresh.hidesTyping, "fresh install: screenshot bypass OFF and other defaults unchanged")
        let suite = "nagramix.capture.migration." + UUID().uuidString
        let defaults = UserDefaults(suiteName: suite)!
        defer { defaults.removePersistentDomain(forName: suite) }
        for master in [false, true] {
            for legacy in [nil, false, true] {
                var record: [String: Bool] = ["enabled": master]
                if let legacy { record["screenshotBypass"] = legacy }
                defaults.set(record, forKey: "nagramix.privacy.ghost.v1")
                check(!NagramiXPrivacySettings.read(from: defaults).bypassScreenshots, "legacy master cannot activate a new opt-in protection bypass")
            }
        }
        defaults.set(["online": true, "typing": false], forKey: "nagramix.privacy.individual.v2")
        check(!NagramiXPrivacySettings.read(from: defaults).bypassScreenshots, "existing canonical settings without new field stay OFF")
        for enabled in [true, false, true, false] {
            NagramiXPrivacySettings.update(in: defaults) { $0[.screenshotBypass] = enabled }
            let value = NagramiXPrivacySettings.read(from: UserDefaults(suiteName: suite)!)
            check(value.bypassScreenshots == enabled && value.hidesOnline && !value.hidesTyping, "user choice survives reopen without changing other options")
        }
        for mask in 0..<16 {
            let message = Message(containsSecretMedia: mask & 1 != 0, minAutoremoveOrClearTimeout: mask & 2 != 0 ? viewOnceTimeout : nil, paidContent: mask & 4 != 0 ? 1 : nil, id: TestMessageId(peerId: TestPeerId(isVerificationCodes: mask & 8 != 0)))
            check(message.nagramiXAllowsScreenshotBypass == (mask == 0), "actual message policy permits ordinary content and preserves special-media/code boundaries")
        }

        let ordinary = CALayer(), mandatory = CALayer(), open = CALayer()
        let video = AVSampleBufferDisplayLayer(), protectedVideo = AVSampleBufferDisplayLayer()
        nagramiXSetLayerDisableScreenshots(ordinary, true)
        nagramiXSetLayerDisableScreenshots(mandatory, true, allowsBypass: false)
        nagramiXSetLayerDisableScreenshots(open, false)
        nagramiXSetVideoCaptureProtection(video, true, allowsBypass: true)
        nagramiXSetVideoCaptureProtection(protectedVideo, true, allowsBypass: false)
        check(ordinary.disabled && mandatory.disabled && !open.disabled && video.preventsCapture && protectedVideo.preventsCapture, "OFF preserves native layer and video protection")
        let account = ScreenshotAccount(), engine = ProductionScreenshotEngine(account: ScreenshotAccount())
        let reporting = ProductionScreenshotEngine(account: account)
        _ = reporting.addSecretChatMessageScreenshot(peerId: 42)
        check(account.calls == [42], "OFF retains the exact native secret screenshot enqueue")
        NagramiXPrivacySettings.update { $0[.screenshotBypass] = true }
        check(!ordinary.disabled && mandatory.disabled && !open.disabled, "ON changes only eligible chat layers without recreating them")
        check(!video.preventsCapture && protectedVideo.preventsCapture, "ON changes only eligible existing video layers")
        _ = reporting.addSecretChatMessageScreenshot(peerId: 43)
        _ = engine.addSecretChatMessageScreenshot(peerId: 99)
        check(account.calls == [42] && engine.account.calls.isEmpty, "ON does not enqueue screenshot notifications on either account")
        let writes = ordinary.writes + mandatory.writes + video.writes
        NagramiXPrivacySettings.update { $0[.typing].toggle() }
        check(writes == ordinary.writes + mandatory.writes + video.writes, "unrelated privacy switches do not reconfigure capture layers")
        let late = CALayer()
        nagramiXSetLayerDisableScreenshots(late, true)
        check(!late.disabled, "a layer created after ON reads the current setting")
        weak var released: CALayer?
        do {
            let transient = CALayer(); released = transient
            nagramiXSetLayerDisableScreenshots(transient, true)
        }
        check(released == nil, "registry does not retain a dismissed layer")
        for _ in 0..<130 { nagramiXSetLayerDisableScreenshots(CALayer(), true) }
        NagramiXPrivacySettings.update { $0[.screenshotBypass] = false }
        check(ordinary.disabled && late.disabled && video.preventsCapture && mandatory.disabled && protectedVideo.preventsCapture, "OFF restores protection on all existing surviving layers")
        _ = reporting.addSecretChatMessageScreenshot(peerId: 44)
        check(account.calls == [42, 44], "OFF restores secret screenshot reporting for future events")
        nagramiXSetLayerDisableScreenshots(ordinary, false)
        NagramiXPrivacySettings.update { $0[.screenshotBypass] = true }
        NagramiXPrivacySettings.update { $0[.screenshotBypass] = false }
        check(!ordinary.disabled, "changing a layer's native requirement cannot leave a stale protection rule")
        let options = NagramiXPrivacySettings.Option.allCases
        check(options.map(productionPrivacyStableId) == [123, 150, 151, 153, 154], "actual UI keeps old IDs and reserves a new one for screenshots")
        check(options.map(productionPrivacyPosition) == [493, 494, 495, 497, 498], "actual UI appends the switch within privacy")
        print("PASS: \(checks) screenshot defaults/migration/live layers/video/notification/weak ownership checks")
    }
}
