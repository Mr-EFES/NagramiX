import Foundation

// Only boundary types are doubles. The validator extracts and compiles the
// actual native activity filter, request guard and view-increment expression.
enum PeerInputActivity: Equatable {
    case typingText, recordingVoice, playingGame, uploadingFile, uploadingPhoto
    case uploadingVideo, recordingInstantVideo, uploadingInstantVideo
    case choosingSticker, interactingWithEmoji, seeingEmojiInteraction
    case speakingInGroupCall, futureChatActivity
}
struct PeerInputActivityRecord { let activity: PeerInputActivity }
enum TestAdmission: Equatable {
    case send, suppressed
    static func complete() -> Self { .suppressed }
}
enum Api { enum Bool: Equatable { case boolTrue, boolFalse } }

@main struct ActivityPrivacyTests {
    static func main() {
        var checks = 0
        func check(_ condition: @autoclosure () -> Bool, _ name: String) { precondition(condition(), name); checks += 1 }
        let key = "nagramix.privacy.individual.v2"
        let saved = UserDefaults.standard.object(forKey: key)
        defer { if let saved { UserDefaults.standard.set(saved, forKey: key) } else { UserDefaults.standard.removeObject(forKey: key) } }
        let activities: [PeerInputActivity] = [.typingText, .recordingVoice, .playingGame, .uploadingFile, .uploadingPhoto, .uploadingVideo, .recordingInstantVideo, .uploadingInstantVideo, .choosingSticker, .interactingWithEmoji, .seeingEmojiInteraction, .futureChatActivity]
        let input = [1: activities.map { (1, PeerInputActivityRecord(activity: $0)) }, 2: [(1, PeerInputActivityRecord(activity: .speakingInGroupCall))]]
        for hidden in [false, true] {
            NagramiXPrivacySettings.update { $0[.typing] = hidden }
            for activity in activities {
                check(productionActivityAdmission(activity: activity) == (hidden ? .suppressed : .send), "actual request guard suppresses every chat activity, including future kinds")
            }
            check(productionActivityAdmission(activity: .speakingInGroupCall) == .send, "group call speaking signaling is preserved")
            check(productionActivityAdmission(activity: nil) == .send, "cancel/cleanup is allowed")
            let filtered = productionFilteredActivities(activities: input, settings: .current)
            check(filtered[1]?.count == (hidden ? 0 : activities.count), "current activities are removed from the real managed context")
            check(filtered[2]?.count == 1, "filter preserves call activity")
            check(input[1]?.count == activities.count, "filter does not mutate incoming/original state")
        }
        for local in [false, true] {
            for action in [false, true] {
                NagramiXPrivacySettings.update { $0.readMode = local ? .local : .standard; $0[.readOnAction] = action }
                check(productionViewIncrement() == (local || action ? .boolFalse : .boolTrue), "actual channel RPC does not increment views under either private read mode")
            }
        }
        print("PASS: \(checks) actual activity filter/request and channel view policy checks")
    }
}
