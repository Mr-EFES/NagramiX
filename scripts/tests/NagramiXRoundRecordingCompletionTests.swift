@main struct RoundRecordingCompletionTests {
    static var checks = 0
    static func check(_ value: Bool, _ description: String) {
        checks += 1
        if !value { print("FAIL: " + description); exit(96) }
    }

    static func lateTouch() {
        for locked in [false, true] {
            for lateSend in [false, true] {
                for delayPlaceholder in [false, true] {
                    let recorder = VideoMessageCameraScreen()
                    let placeholder = Promise<UIImage?>()
                    if delayPlaceholder { recorder.camera?.transitionImage = placeholder.get() }
                    let chat = Chat(recorder)
                    chat.panel.viewOnce = true
                    chat.presentationInterfaceState.inputTextPanelState.mediaRecordingState = .video(status: 1, isLocked: locked)
                    chat.dismissVideo(.pause)
                    chat.panel.mediaActionButtons.micButton.endRecording(lateSend)
                    check(chat.interaction.actions.isEmpty, "late touch preserves the video at the limit")
                    check(chat.videoRecorderValue === recorder, "limit keeps the owning recorder")
                    check(chat.panel.viewOnce, "late touch preserves the once-only choice")
                    if delayPlaceholder { placeholder.set(.single(nil)) }
                    chat.panel.mediaActionButtons.micButton.endRecording(lateSend)
                    check(chat.interaction.actions.isEmpty, "late touch preserves the completed preview")
                    recorder.finish()
                    check(chat.videoRecorderValue === recorder, "finished preview is still sendable")
                    recorder.sendVideoRecording()
                    check(recorder.sentPaths == ["round.mp4"], "limit preview sends the finished file")
                }
            }
        }
    }

    static func singleStop() {
        let recorder = VideoMessageCameraScreen()
        check(recorder.stopVideoRecording(), "first stop accepted")
        var results = 0
        let disposable = recorder.takenRecordedData().startStandalone(next: { _ in results += 1 })
        check(!recorder.stopVideoRecording(), "repeated stop is ignored while finalizing")
        check(recorder.stopCalls == 1, "writer stopped once")
        recorder.finish()
        check(!recorder.stopVideoRecording(), "completed preview cannot request another result")
        recorder.sendVideoRecording()
        check(recorder.sentPaths.count == 1, "completed preview sends without a second recording")
        check(results >= 2, "the final recording reaches the preview")
        disposable.dispose()
    }

    static func immediateSend() {
        for completeBeforeSend in [false, true] {
            let recorder = VideoMessageCameraScreen()
            check(recorder.stopVideoRecording(), "preview stop accepted")
            let disposable = recorder.takenRecordedData().startStandalone(next: { _ in })
            if completeBeforeSend { recorder.finish() }
            recorder.sendVideoRecording(silentPosting: true, scheduleTime: 123, repeatPeriod: 9)
            check(recorder.didSend, "Send immediately after stop is accepted")
            if !completeBeforeSend {
                check(recorder.sentPaths.isEmpty, "Send awaits the finished file")
                recorder.finish()
            }
            check(recorder.sentPaths == ["round.mp4"], "one finished file delivered")
            check(recorder.sentOptions.first?.0 == true && recorder.sentOptions.first?.1 == 123 && recorder.sentOptions.first?.2 == 9,
                  "send options reach the export boundary")
            recorder.sendVideoRecording()
            check(recorder.sentPaths.count == 1, "repeated Send produces one message")
            check(recorder.stopCalls == 1, "Send joins the existing stop")
            disposable.dispose()
        }
    }

    static func ordinaryRecording() {
        for duration in [1.2, 12.0, 59.0] {
            let recorder = VideoMessageCameraScreen()
            recorder.cameraState.duration = duration
            let chat = Chat(recorder)
            chat.panel.mediaActionButtons.micButton.endRecording(true)
            check(chat.interaction.actions == [.send(viewOnce: false)], "short hold release sends")
            recorder.finish()
            check(recorder.sentPaths.count == 1 && !recorder.discarded, "short recording result delivered")
        }
        let cancelled = VideoMessageCameraScreen()
        let chat = Chat(cancelled)
        chat.panel.mediaActionButtons.micButton.endRecording(false)
        check(chat.videoRecorderValue == nil, "cancel during an active hold still discards")

        let audio = Chat(VideoMessageCameraScreen())
        audio.presentationInterfaceState.interfaceState.mediaRecordingMode = .audio
        audio.presentationInterfaceState.inputTextPanelState.mediaRecordingState = .audio
        audio.panel.mediaActionButtons.micButton.endRecording(true)
        check(audio.interaction.actions == [.send(viewOnce: false)], "audio release still routes Send")
    }

    static func resumedRecording() {
        let recorder = VideoMessageCameraScreen()
        check(recorder.stopVideoRecording(), "first segment stop")
        let preview = recorder.takenRecordedData().startStandalone(next: { _ in })
        recorder.finish(path: "first.mp4")
        recorder.cameraState.recording = .handsFree
        recorder.cameraState.duration = 60
        check(recorder.stopVideoRecording(), "resumed segment stop")
        let resumed = recorder.takenRecordedData().startStandalone(next: { _ in })
        recorder.sendVideoRecording()
        check(recorder.sentPaths.isEmpty, "a resumed recording waits beyond the previous revision")
        recorder.finish(path: "second.mp4")
        check(recorder.sentPaths == ["first.mp4"] && recorder.node.results.count == 2, "resumed result retains both segments")
        check(recorder.stopCalls == 2, "each segment stops once")
        preview.dispose()
        resumed.dispose()
    }

    static func main() {
        let group = "__TEST_GROUP__"
        if group == "all" || group == "release" { lateTouch() }
        if group == "all" || group == "stop" { singleStop() }
        if group == "all" || group == "send" { immediateSend() }
        if group == "all" {
            ordinaryRecording()
            resumedRecording()
        }
        print("Round recording completion checks: " + String(checks))
    }
}
