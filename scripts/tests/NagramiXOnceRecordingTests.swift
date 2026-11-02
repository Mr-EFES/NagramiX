import Foundation

// UIKit/Telegram boundaries only. GeneratedNative.swift contains the actual
// composer methods, CameraState, selection and native attribute construction.
public enum NagramiXTabSettings { public static let changedNotification = Notification.Name("NagramiXSettingsChanged") }
struct PeerId: Equatable { var namespace: Int32; var id: Int64 }
enum Namespaces { enum Peer { static let CloudUser: Int32 = 0; static let SecretChat: Int32 = 1; static let CloudGroup: Int32 = 2; static let CloudChannel: Int32 = 3 } }
protocol Peer {}
struct TelegramUser: Peer { var botInfo: Int? = nil }
struct OtherPeer: Peer {}
struct RenderedPeer { var peer: Peer }
struct ChatLocation { var peerId: PeerId? }
enum Subject { case normal; case scheduledMessages }
struct Strings { let Chat_PlayVoiceMessageOnceTooltip = "Listen once" }
struct InterfaceState {
    var chatLocation = ChatLocation(peerId: PeerId(namespace: 0, id: 2))
    var accountPeerId = PeerId(namespace: 0, id: 1)
    var renderedPeer: RenderedPeer? = RenderedPeer(peer: TelegramUser())
    var subject = Subject.normal
    var sendPaidMessageStars: Int? = nil
    var strings = Strings()
    var inputTextPanelState = InputTextPanelState()
}
struct InputTextPanelState { var mediaRecordingState: Bool? = true }
final class ViewOnceButton {
    var selected = false
    func update(isSelected: Bool, animated: Bool) { selected = isSelected }
}
final class Tooltip { func dismiss() {} }
final class SharedContext { let accountManager = 0 }
final class AccountContext { let sharedContext = SharedContext() }
enum RecordingAction { case send(viewOnce: Bool); case dismiss }
final class Interaction {
    var sent: [Bool] = []; var cancelled = false
    func dismissAllTooltips() {}
    func finishMediaRecording(_ action: RecordingAction) { switch action { case let .send(viewOnce): sent.append(viewOnce); case .dismiss: cancelled = true } }
}
enum RemoveAnimation { case recordingToAttachButton }
final class InputPanel {
    var presentationInterfaceState: InterfaceState? = InterfaceState()
    var context: AccountContext? = AccountContext()
    var viewOnce = false
    let viewOnceButton = ViewOnceButton()
    var tooltipController: Tooltip? = Tooltip()
    var interfaceInteraction: Interaction? = Interaction()
    var audioRecordingRemoveAnimationState: RemoveAnimation?
    func displayViewOnceTooltip(text: String) {}
}
struct NoticeOperation { func startStandalone() -> Int { 0 } }
enum ApplicationSpecificNotice {
    static func incrementVoiceMessagesPlayOnceSuggestion(accountManager: Int, count: Int) -> NoticeOperation { NoticeOperation() }
}
struct UIColor { init(rgb: Int) {}; static let white = UIColor(rgb: 0xffffff) }
enum Camera { enum Position { case front; case back }; enum FlashMode { case off; case on } }
enum Transition { case easeInOut(duration: Double) }
struct AvailabilityController { let viewOnceAvailable: Bool }
final class VideoController {
    var cameraState: CameraState
    init(controller: AvailabilityController) { cameraState = makeInitialCameraState(controller: controller) }
    func getController() -> VideoController? { self }
    func updateCameraState(_ f: (CameraState) -> CameraState, transition: Transition) { cameraState = f(cameraState) }
}
protocol MessageAttribute {}
enum EngineMessage { typealias Attribute = MessageAttribute }
let viewOnceTimeout = Int32.max
struct AutoremoveTimeoutMessageAttribute: MessageAttribute { let timeout: Int32; let countdownBeginTime: Int32? }
final class ChatDisplayNode { var textInputPanelNode: InputPanel? = InputPanel() }
final class AudioController { let chatDisplayNode = ChatDisplayNode() }
final class NotificationCount: @unchecked Sendable {
    private let lock = NSLock(); private var count = 0
    func increment() { lock.lock(); count += 1; lock.unlock() }
    var value: Int { lock.lock(); defer { lock.unlock() }; return count }
}

@main struct OnceRecordingTests {
    static func main() {
        let defaults = UserDefaults.standard, key = "nagramix.recording.viewOnce"
        if CommandLine.arguments.count > 1 {
            let command = CommandLine.arguments[1], value = CommandLine.arguments[2] == "true"
            if command == "set" { NagramiXRecordingSettings.setViewOnceEnabled(value); _ = defaults.synchronize() }
            else {
                precondition(NagramiXRecordingSettings.viewOnceEnabled == value, "saved choice survives a cold process")
                if command == "fresh" { precondition(defaults.object(forKey: key) == nil, "reading fresh default does not persist artificial state") }
            }
            print("PASS cold " + command + " " + String(value)); return
        }
        var count = 0
        func check(_ value: @autoclosure () -> Bool, _ message: String) { precondition(value(), message); count += 1 }
        defaults.removeObject(forKey: key)
        defer { defaults.removeObject(forKey: key); _ = defaults.synchronize() }
        check(!NagramiXRecordingSettings.viewOnceEnabled, "first launch OFF")
        check(defaults.object(forKey: key) == nil, "getter never overwrites an absent setting")
        let notifications = NotificationCount()
        let token = NotificationCenter.default.addObserver(forName: NagramiXTabSettings.changedNotification, object: nil, queue: nil) { _ in notifications.increment() }
        defer { NotificationCenter.default.removeObserver(token) }
        for enabled in [false,true,false,true] {
            NagramiXRecordingSettings.setViewOnceEnabled(enabled)
            check(NagramiXRecordingSettings.viewOnceEnabled == enabled, "explicit ON/OFF retained")
            for available in [false,true] { check(NagramiXRecordingSettings.initialViewOnce(available: available) == (enabled && available), "default respects native availability") }
        }
        check(notifications.value == 4, "one settings-change notification per update")
        let panel = InputPanel()
        var states: [(String, InterfaceState?, Bool)] = [("private",InterfaceState(),true),("missing state",nil,false)]
        var state = InterfaceState(); state.chatLocation.peerId = nil; states.append(("custom",state,false))
        for namespace in [Namespaces.Peer.SecretChat, Namespaces.Peer.CloudGroup, Namespaces.Peer.CloudChannel] { var s = InterfaceState(); s.chatLocation.peerId?.namespace = namespace; states.append(("unsupported peer",s,false)) }
        state = InterfaceState(); state.chatLocation.peerId = state.accountPeerId; states.append(("saved messages",state,false))
        state = InterfaceState(); state.renderedPeer = RenderedPeer(peer: TelegramUser(botInfo:1)); states.append(("bot",state,false))
        state = InterfaceState(); state.renderedPeer = nil; states.append(("missing user",state,false))
        state = InterfaceState(); state.renderedPeer = RenderedPeer(peer: OtherPeer()); states.append(("non-user",state,false))
        state = InterfaceState(); state.subject = .scheduledMessages; states.append(("scheduled",state,false))
        state = InterfaceState(); state.sendPaidMessageStars = 1; states.append(("paid",state,false))
        for enabled in [false,true] {
            NagramiXRecordingSettings.setViewOnceEnabled(enabled)
            for (name,state,available) in states {
                panel.presentationInterfaceState = state; panel.viewOnce = true
                panel.nagramiXPrepareAudioViewOnce(resuming:false)
                check(panel.viewOnce == (enabled && available), "actual audio initialization: " + name)
                check(panel.viewOnceButton.selected == panel.viewOnce, "native button reflects audio state")
            }
            for available in [false,true] {
                let video = VideoController(controller: AvailabilityController(viewOnceAvailable:available))
                check(video.cameraState.isViewOnceEnabled == (enabled && available), "actual camera initializer respects checkbox and availability")
            }
        }
        NagramiXRecordingSettings.setViewOnceEnabled(true)
        panel.presentationInterfaceState = InterfaceState(); panel.nagramiXPrepareAudioViewOnce(resuming:false)
        panel.viewOncePressed()
        check(!panel.viewOnce && !panel.viewOnceButton.selected && NagramiXRecordingSettings.viewOnceEnabled, "manual audio OFF affects this recording only")
        panel.nagramiXPrepareAudioViewOnce(resuming:true)
        check(!panel.viewOnce, "resume/trim never resets manual audio OFF")
        panel.nagramiXPrepareAudioViewOnce(resuming:false)
        check(panel.viewOnce, "next fresh audio reads persisted ON again")
        panel.endRecording(sendMedia:true)
        check(panel.interfaceInteraction?.sent == [true] && !panel.viewOnce, "native hold-release sends one-shot snapshot then clears per-recording state")
        panel.nagramiXPrepareAudioViewOnce(resuming:false); panel.viewOncePressed(); panel.endRecording(sendMedia:true)
        check(panel.interfaceInteraction?.sent == [true,false], "manual OFF survives native direct send")
        panel.nagramiXPrepareAudioViewOnce(resuming:false); panel.endRecording(sendMedia:false)
        check(panel.interfaceInteraction?.cancelled == true && !panel.viewOnce, "native cancellation clears only this recording")
        panel.nagramiXPrepareAudioViewOnce(resuming:false)
        check(panel.viewOnce && NagramiXRecordingSettings.viewOnceEnabled, "cancel does not clear saved checkbox")
        let video = VideoController(controller: AvailabilityController(viewOnceAvailable:true))
        video.toggleViewOnce()
        check(!video.cameraState.isViewOnceEnabled && NagramiXRecordingSettings.viewOnceEnabled, "native round-video toggle turns off this recording only")
        video.cameraState = video.cameraState.updatedPosition(.front).updatedRecording(.holding).updatedDuration(2).updatedRecording(.none).updatedRecording(.handsFree).updatedFlashMode(.on).updatedFlashTint(.blue).updatedFlashTintSize(0.5)
        check(!video.cameraState.isViewOnceEnabled, "native camera switch/pause/resume updates preserve manual OFF")
        check(VideoController(controller:AvailabilityController(viewOnceAvailable:true)).cameraState.isViewOnceEnabled, "next round video uses saved ON")
        for selected in [false,true] {
            let controller = AudioController(); controller.chatDisplayNode.textInputPanelNode?.viewOnce = selected
            let direct = directAudioAttributes(viewOnce:selected)
            check(direct.count == (selected ? 1 : 0), "direct voice uses actual native one-shot attribute")
            if let attribute = direct.first as? AutoremoveTimeoutMessageAttribute { check(attribute.timeout == viewOnceTimeout && attribute.countdownBeginTime == nil, "native consumption timeout, no custom timer") }
            for explicit in [nil,false,true] as [Bool?] {
                for scheduled in [false,true] {
                    let attributes = controller.previewAttributes(viewOnce:explicit,scheduleTime:scheduled ? 1 : nil)
                    check(attributes.count == (!scheduled && (explicit ?? selected) ? 1 : 0), "preview/silent/effect sends preserve explicit choice, scheduled does not use one-shot")
                }
                check(controller.previewAttributes(viewOnce:explicit,repeatPeriod:1).isEmpty, "repeated send stays ordinary")
            }
            video.cameraState = video.cameraState.updatedIsViewOnceEnabled(selected)
            check(video.attributes().count == (selected ? 1 : 0), "actual camera send uses per-recording state")
            check(video.attributes(scheduleTime:1).isEmpty && video.attributes(repeatPeriod:1).isEmpty, "scheduled/repeated round video stays ordinary")
        }
        NagramiXRecordingSettings.setViewOnceEnabled(false)
        panel.viewOnce = true; panel.nagramiXPrepareAudioViewOnce(resuming:true)
        check(panel.viewOnce, "changing global default does not override an existing recording")
        panel.nagramiXPrepareAudioViewOnce(resuming:false)
        check(!panel.viewOnce, "next fresh recording follows saved OFF")
        panel.viewOncePressed()
        check(panel.viewOnce && !NagramiXRecordingSettings.viewOnceEnabled, "native manual audio ON still works when global default is OFF")
        let ordinaryVideo = VideoController(controller:AvailabilityController(viewOnceAvailable:true))
        ordinaryVideo.toggleViewOnce()
        check(ordinaryVideo.cameraState.isViewOnceEnabled && !NagramiXRecordingSettings.viewOnceEnabled, "native manual video ON still works when default is OFF")
        print("PASS: \(count) actual settings/composer/camera/send checks")
    }
}
