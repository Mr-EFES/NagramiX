import TelegramCore

func nagramiXCanSaveGalleryMedia(_ message: EngineRawMessage, peerIsCopyProtected: Bool) -> Bool {
    guard message.paidContent == nil else { return false }
    if !message.isCopyProtected() && !peerIsCopyProtected {
        return true
    }
    return nagramiXAllowsProtectedContentExport(message)
}
