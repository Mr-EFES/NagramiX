import TelegramCore
import NagramiXCore

// Use the same existing opt-ins and message eligibility as protected export
// from the chat context menu; screenshot capture stays an independent option.
func nagramiXCanSaveGalleryMedia(_ message: EngineRawMessage, peerIsCopyProtected: Bool) -> Bool {
    guard message.paidContent == nil else { return false }
    if !message.isCopyProtected() && !peerIsCopyProtected {
        return true
    }
    let settings = NagramiXTabSettings.current
    return (settings.showForwardWithoutAuthor || settings.showBroadcastMessages) && message.nagramiXAllowsContentCopy
}
