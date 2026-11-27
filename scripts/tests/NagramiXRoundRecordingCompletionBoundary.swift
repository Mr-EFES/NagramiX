// Camera/file completion and UI rendering are explicit test boundaries.
// Stop/send entry points, result waiting and the touch callback are injected unchanged.
public final class UIImage {}
public struct ChatSendMessageEffect {}
enum TestClock { static var now = 100.0 }
func CACurrentMediaTime() -> Double { TestClock.now }
enum Transition { case spring(duration: Double) }
final class Logger {
    static let shared = Logger()
    func log(_ scope: String, _ message: String) {}
}
final class ActionSlot<T> {
    var action: (T) -> Void = { _ in }
    func invoke(_ value: T) { action(value) }
}
struct CameraState {
    // PRODUCTION_RECORDING_STATE
    var recording: Recording = .holding
    var duration = 60.0
}
struct PreviewState { var trimRange: Range<Double>? }
struct AVAsset {}
func nagramiXRecordingComposition(with results: [VideoMessageCameraScreen.CaptureResult]) -> Signal<AVAsset, NoError> {
    .single(AVAsset())
}
func videoFrames(asset: AVAsset?, count: Int, initialPlaceholder: UIImage? = nil, initialTimestamp: Double? = nil) -> Signal<([UIImage], Double), NoError> {
    .single(([], 0))
}
final class Camera {
    var transitionImage: Signal<UIImage?, NoError> = .single(nil)
}
public final class VideoMessageCameraScreen {
    public struct Video {
        var videoPath: String
        var duration: Double
        var thumbnail = UIImage()
    }
    public enum CaptureResult { case video(Video) }
    final class Node {
        var nagramiXCountdownPending = false
        var nagramiXCameraSwitchPending = false
        var transitioningToPreview = false
        var results: [CaptureResult] = []
        var nagramiXCompletedRevision = 0
        let nagramiXCompletedResults = Promise<(revision: Int, results: [CaptureResult])>()
        let previewStatePromise = Promise<PreviewState?>(nil)
        let nagramiXCompositionDisposable = MetaDisposable()
        let stopRecording = ActionSlot<Void>()
        let cancelRecording = ActionSlot<Void>()
        func dismissAllTooltips() {}
        func requestUpdateLayout(transition: Transition) {}
    }
    var node = Node()
    var camera: Camera? = Camera()
    var cameraState = CameraState()
    var didSend = false
    var isSendingImmediately = false
    var lastActionTimestamp: Double?
    var recordingStartTime: Double?
    private var nagramiXExpectedCompletedRevision = 0
    var stopCalls = 0
    var discarded = false
    var failed = false
    var sentPaths: [String] = []
    var sentOptions: [(Bool?, Int32?, Int32?)] = []
    var completion: (String?, Bool?, Int32?, Int32?) -> Void = { _, _, _, _ in }
    init() {
        node.stopRecording.action = { [weak self] _ in
            guard let self else { return }
            self.stopCalls += 1
            self.lastActionTimestamp = TestClock.now
        }
    }
    func discardVideo() { discarded = true }
    func finish(path: String = "round.mp4") {
        cameraState.recording = .none
        node.results.append(.video(Video(videoPath: path, duration: cameraState.duration)))
        node.nagramiXCompletedRevision += 1
        node.nagramiXCompletedResults.set(.single((node.nagramiXCompletedRevision, node.results)))
        node.transitioningToPreview = false
        node.previewStatePromise.set(.single(PreviewState()))
    }
    // PRODUCTION_RECORDED_DATA
    // PRODUCTION_RESULTS
    // PRODUCTION_WAITING
    // PRODUCTION_TAKEN_DATA
    // PRODUCTION_STOP
    // PRODUCTION_SEND
}
enum ChatInterfaceMediaDraftState {
    struct Video {
        var duration: Double
        var frames: [UIImage]
        var framesUpdateTimestamp: Double
        var trimRange: Range<Double>?
    }
    case video(Video)
    case audio
}
enum RecordingMode { case video, audio }
enum MediaRecordingState {
    case video(status: Int, isLocked: Bool)
    case audio
    case waitingForPreview
}
struct InputPanelState {
    var mediaRecordingState: MediaRecordingState?
    func withUpdatedMediaRecordingState(_ value: MediaRecordingState?) -> InputPanelState { InputPanelState(mediaRecordingState: value) }
}
struct ChatInterface {
    var mediaRecordingMode: RecordingMode = .video
    var mediaDraftState: ChatInterfaceMediaDraftState?
    func withUpdatedMediaDraftState(_ value: ChatInterfaceMediaDraftState?) -> ChatInterface {
        var copy = self
        copy.mediaDraftState = value
        return copy
    }
}
final class InterfaceState {
    var interfaceState = ChatInterface()
    var inputTextPanelState = InputPanelState(mediaRecordingState: .video(status: 1, isLocked: false))
    func updatedInputTextPanelState(_ update: (InputPanelState) -> InputPanelState) -> InterfaceState {
        inputTextPanelState = update(inputTextPanelState)
        return self
    }
    func updatedInterfaceState(_ update: (ChatInterface) -> ChatInterface) -> InterfaceState {
        interfaceState = update(interfaceState)
        return self
    }
}
enum Action: Equatable { case send(viewOnce: Bool), dismiss, preview, pause }
enum RemoveAnimation { case recordingToAttachButton }
final class MicButton { var endRecording: (Bool) -> Void = { _ in } }
final class Buttons { let micButton = MicButton() }
final class Tooltip { func dismiss() {} }
final class Interaction {
    var finish: (Action) -> Void = { _ in }
    var actions: [Action] = []
    func finishMediaRecording(_ action: Action) { actions.append(action); finish(action) }
}
final class Panel {
    let mediaActionButtons = Buttons()
    var presentationInterfaceState: InterfaceState?
    var interfaceInteraction: Interaction?
    var viewOnce = false
    var audioRecordingRemoveAnimationState: RemoveAnimation?
    var tooltipController: Tooltip?
    init(state: InterfaceState, interaction: Interaction) {
        presentationInterfaceState = state
        interfaceInteraction = interaction
        // PRODUCTION_END_RECORDING
    }
}
final class DisplayNode {
    func updateRecordedMediaDeleted(_ value: Bool) {}
}
final class Feedback { func error() {} }
final class Chat {
    let presentationInterfaceState = InterfaceState()
    let chatDisplayNode = DisplayNode()
    let interaction = Interaction()
    var panel: Panel!
    var videoRecorderValue: VideoMessageCameraScreen?
    let videoRecorder = Promise<VideoMessageCameraScreen?>()
    let recorderDataDisposable = MetaDisposable()
    var recorderFeedback: Feedback?
    var recordings: Disposable?
    init(_ recorder: VideoMessageCameraScreen) {
        videoRecorderValue = recorder
        recordings = videoRecorder.get().startStandalone(next: { [weak self] in self?.videoRecorderValue = $0 })
        panel = Panel(state: presentationInterfaceState, interaction: interaction)
        interaction.finish = { [weak self] in self?.dismissVideo($0) }
    }
    func updateDownButtonVisibility() {}
    func updateChatPresentationInterfaceState(animated: Bool, interactive: Bool, _ update: (InterfaceState) -> InterfaceState) {
        _ = update(presentationInterfaceState)
    }
    func dismissVideo(_ updatedAction: Action) {
        guard let videoRecorderValue else { return }
        // PRODUCTION_VIDEO_DISMISS
    }
}
