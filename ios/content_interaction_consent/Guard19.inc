import TelegramCore
import NagramiXCore
import NagramiXMediaSettings

// Use the same existing opt-ins and message eligibility as protected export
// from the chat context menu, including the current Free Screenshot switch.
func nagramiXCanSaveGalleryMedia(_ message: EngineRawMessage, peerIsCopyProtected: Bool) -> Bool {
    guard message.paidContent == nil else { return false }
    if !message.isCopyProtected() && !peerIsCopyProtected {
        return true
    }
    let settings = NagramiXTabSettings.current
    return NagramiXPrivacySettings.current.bypassScreenshots
        && (settings.showForwardWithoutAuthor || settings.showBroadcastMessages)
        && message.nagramiXAllowsContentCopy
}
