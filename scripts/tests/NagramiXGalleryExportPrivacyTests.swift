import Foundation

struct EngineRawMessage {
    var paidContent: Bool?
    var protected = false
    var nagramiXAllowsContentCopy = true
    func isCopyProtected() -> Bool { self.protected }
}
struct NagramiXPrivacySettings {
    var bypassScreenshots = false
    static var current = Self()
}
struct NagramiXTabSettings {
    var showForwardWithoutAuthor = false
    var showBroadcastMessages = false
    static var current = Self()
}

@main struct GalleryExportPrivacyTests {
    static func main() {
        let protected = EngineRawMessage(protected: true)
        let ordinary = EngineRawMessage()
        NagramiXTabSettings.current.showForwardWithoutAuthor = true
        precondition(!nagramiXCanSaveGalleryMedia(protected, peerIsCopyProtected: false), "Free Screenshot OFF blocks protected export even with Forward enabled")
        precondition(!nagramiXCanSaveGalleryMedia(ordinary, peerIsCopyProtected: true), "the chat's protection requires the same permission")
        precondition(nagramiXCanSaveGalleryMedia(ordinary, peerIsCopyProtected: false), "ordinary saving remains available with Free Screenshot OFF")

        NagramiXPrivacySettings.current.bypassScreenshots = true
        precondition(nagramiXCanSaveGalleryMedia(protected, peerIsCopyProtected: false), "Free Screenshot and Forward allow eligible protected export")
        NagramiXTabSettings.current = .init(showBroadcastMessages: true)
        precondition(nagramiXCanSaveGalleryMedia(protected, peerIsCopyProtected: false), "Broadcast is the alternative existing export opt-in")
        NagramiXTabSettings.current = .init()
        precondition(!nagramiXCanSaveGalleryMedia(protected, peerIsCopyProtected: false), "Free Screenshot alone does not enable hidden copy actions")

        NagramiXTabSettings.current = .init(showForwardWithoutAuthor: true, showBroadcastMessages: true)
        precondition(!nagramiXCanSaveGalleryMedia(.init(paidContent: true, protected: true), peerIsCopyProtected: true), "paid media remains excluded")
        precondition(!nagramiXCanSaveGalleryMedia(.init(protected: true, nagramiXAllowsContentCopy: false), peerIsCopyProtected: false), "unsupported protected content remains excluded")

        let displayedSaveAction = { nagramiXCanSaveGalleryMedia(protected, peerIsCopyProtected: false) }
        precondition(displayedSaveAction(), "save action is initially permitted")
        NagramiXPrivacySettings.current.bypassScreenshots = false
        precondition(!displayedSaveAction(), "an already displayed action rechecks Free Screenshot at invocation")
        NagramiXPrivacySettings.current.bypassScreenshots = true
        precondition(displayedSaveAction(), "reenabling restores eligibility without reopening the gallery")
        print("PASS: gallery export settings, exclusions and stale-action permission")
    }
}
