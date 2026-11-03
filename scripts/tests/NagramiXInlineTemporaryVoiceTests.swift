@main
private struct InlineVoiceTests {
    static func main() {
        var checks = 0
        func check(_ value: @autoclosure () -> Bool, _ label: String) {
            checks += 1
            if !value() { FileHandle.standardError.write(Data(("FAIL: " + label + "\n").utf8)); exit(1) }
        }
        let defaults = UserDefaults.standard
        let temporaryKey = "nagramix.messages.saveTemporaryMessages", replayKey = "nagramix.messages.replayViewOnce"
        func settings(_ temporary: Bool, _ replay: Bool = false) { defaults.set(temporary, forKey: temporaryKey); defaults.set(replay, forKey: replayKey) }
        for temporary in [false, true] {
            for replay in [false, true] {
                settings(temporary, replay)
                for incoming in [false, true] {
                    let message = Message(); message.flags = incoming ? [.Incoming] : []
                    check(nagramiXCanPlayTemporaryVoiceInline(message) == (temporary || replay), "only the active temporary setting enables inline voice in both directions")
                    check(nagramiXShouldSuppressViewOnceReceipt(message) == ((temporary || replay) && incoming), "existing consumed-receipt gate stays scoped to incoming temporary media")
                    let controller = ChatControllerImpl()
                    controller.openViewOnceMediaMessage(EngineMessage(raw: message))
                    check(controller.context.sharedContext.opened.count == 1, "one tap starts exactly one native voice playlist")
                    check(controller.overlays.count == ((temporary || replay) ? 0 : 1), "enabled temporary voice must not open a context overlay")
                    check(controller.currentContextController == nil || !(temporary || replay), "inline playback does not retain a modal controller")
                    let params = controller.context.sharedContext.opened[0]
                    check(params.message === message && !params.standalone, "live voice retains original identity and attributes")
                    if case let .singleMessage(id) = params.playlistLocation { check(id == message.id, "player observes only the requested voice") } else { check(false, "live voice must have a single-message playlist") }
                    check(!message.consumed && !message.deleted && message.minAutoremoveOrClearTimeout == viewOnceTimeout, "visual routing never mutates the original or adds a timer")
                }
            }
        }
        settings(true)
        for kind in ["round", "video", "music", "image", "paid", "expired", "empty", "multiple", "secret", "channel", "local", "failed", "sending", "codes", "ordinary", "short-ttl"] {
            let message = Message()
            let file = message.media[0] as! TelegramMediaFile
            switch kind {
            case "round": file.isVoice = false; file.isInstantVideo = true
            case "video": file.isVoice = false; file.isVideo = true
            case "music": file.isVoice = false; file.isMusic = true
            case "image": message.media = [TelegramMediaImage()]
            case "paid": message.media = [TelegramMediaPaidContent()]
            case "expired": message.media = [TelegramMediaExpiredContent()]
            case "empty": message.media = []
            case "multiple": message.media.append(TelegramMediaFile())
            case "secret": message.id.peerId.namespace = Namespaces.Peer.SecretChat
            case "channel": message.id.peerId.namespace = 2
            case "local": message.id.namespace = 1
            case "failed": message.flags.insert(.Failed)
            case "sending": message.flags.insert(.sending)
            case "codes": message.id.peerId.isVerificationCodes = true
            case "ordinary": message.minAutoremoveOrClearTimeout = nil
            case "short-ttl": message.minAutoremoveOrClearTimeout = 20
            default: break
            }
            check(!nagramiXCanPlayTemporaryVoiceInline(message), "unsupported/special content keeps native routing: \(kind)")
        }
        let round = Message(); (round.media[0] as! TelegramMediaFile).isVoice = false; (round.media[0] as! TelegramMediaFile).isInstantVideo = true
        let roundController = ChatControllerImpl(); roundController.openViewOnceMediaMessage(EngineMessage(raw: round))
        check(roundController.overlays.count == 1, "round video keeps native separate view")
        let recording = ChatControllerImpl(); recording.screenCaptureManager!.isRecordingActive = true
        recording.openViewOnceMediaMessage(EngineMessage(raw: Message()))
        check(recording.alerts == 1 && recording.overlays.isEmpty && recording.context.sharedContext.opened.isEmpty, "existing screen-recording permission check remains before playback")
        let archived = Message(); archived.minAutoremoveOrClearTimeout = nil; archived.attributes = [NagramiXArchivedMessageAttribute(true)]
        for incoming in [false, true] {
            archived.flags = incoming ? [.Incoming] : []
            check(nagramiXCanPlayTemporaryVoiceInline(archived), "retained temporary voice has inline burn appearance in either direction")
            let controller = ChatControllerImpl(); controller.openViewOnceMediaMessage(EngineMessage(raw: archived))
            let params = controller.context.sharedContext.opened[0]
            check(params.standalone && controller.overlays.isEmpty, "retained playback uses existing standalone path without an overlay")
            if case let .recentActions(message) = params.playlistLocation { check(message === archived, "retained playback never looks up a deleted server ID") } else { check(false, "retained voice must use its own local playlist") }
        }
        settings(false)
        check(!nagramiXCanPlayTemporaryVoiceInline(archived), "OFF removes extra burn behavior from retained voices")
        settings(true)
        let message = Message()
        let controller = ChatControllerImpl(), waveform = NativeWaveformHarness(), row = NativeVoiceRowHarness()
        for iteration in 0..<12 {
            controller.openViewOnceMediaMessage(EngineMessage(raw: message))
            for position in [0.0, 2.0, 4.0, 6.0, 8.0] {
                waveform.playbackStatus = PlaybackStatus(timestamp: position, duration: 8, generationTimestamp: 0, baseRate: 1, status: .playing)
                let progress = waveform.progress(viewOnce: row.isViewOnce(message))
                check(abs(progress - CGFloat(1.0 - position / 8.0)) < 0.00001, "native waveform burns from full to empty")
                let button = row.button(message, playbackStatus: .playing, position: position, duration: 8)
                if case let .secretTimeout(_, duration, _, _) = button { check(duration == 8, "native flame/countdown is used in the row") } else { check(false, "playing view-once voice must show native flame") }
            }
            waveform.playbackStatus = nil
            check(waveform.progress(viewOnce: row.isViewOnce(message)) == 1, "end restores full waveform for the next replay")
            check(row.button(message, playbackStatus: .paused, position: 0, duration: 8) == .play && !row.unreadIsHidden, "pause/end restores play and unconsumed marker")
            check(!message.consumed && !message.deleted && nagramiXShouldSuppressViewOnceReceipt(message), "replay \(iteration) keeps supported original unconsumed")
        }
        check(controller.overlays.isEmpty && controller.context.sharedContext.opened.count == 12, "repeated replay never accumulates modal windows or duplicate players")
        waveform.playbackStatus = PlaybackStatus(timestamp: 3, duration: 8, generationTimestamp: 0, baseRate: 1, status: .paused)
        check(waveform.progress(viewOnce: true) == 0.625, "pause holds native burn position")
        waveform.playbackStatus = PlaybackStatus(timestamp: 0, duration: 8, generationTimestamp: 8, baseRate: 2, status: .playing)
        check(waveform.progress(viewOnce: true) == 0.5, "native elapsed-time/rate calculation is preserved")
        waveform.playbackStatus = PlaybackStatus(timestamp: 100, duration: 8, generationTimestamp: 0, baseRate: 1, status: .playing)
        check(waveform.progress(viewOnce: true) == 0, "native progress clamps at the end")
        waveform.playbackStatus = nil
        check(waveform.progress(viewOnce: false) == 0, "ordinary waveform appearance is unchanged")
        let ordinary = Message(); ordinary.minAutoremoveOrClearTimeout = nil
        check(!row.isViewOnce(ordinary), "reused ordinary row never inherits temporary burn mode")
        _ = row.button(message, playbackStatus: .playing, position: 3, duration: 8)
        check(row.unreadIsHidden, "native flame temporarily hides the incoming unread dot")
        _ = row.button(ordinary, playbackStatus: .paused, position: 0, duration: 8)
        check(!row.unreadIsHidden, "recycling a playing voice row restores the next message's unread marker")
        settings(false)
        let native = ChatControllerImpl(); native.openViewOnceMediaMessage(EngineMessage(raw: message))
        check(native.overlays.count == 1, "OFF returns subsequent opens to stock modal behavior")
        native.overlays[0].configuration.sources[0].closeAction()
        check(native.context.sharedContext.mediaManager.stops == 1, "stock close action remains intact")
        print("PASS: \(checks) actual inline voice routing, receipt policy, native burn progress and replay checks; UIKit/player boundaries")
    }
}
