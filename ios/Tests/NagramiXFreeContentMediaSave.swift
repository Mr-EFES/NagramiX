import Foundation
import NagramiXCore
import NagramiXMediaSettings

public struct EngineRawMessage {
    var protected = false
    var paidContent: Bool?
    var nagramiXAllowsContentCopy = true

    func isCopyProtected() -> Bool { self.protected }
}

@main private enum FreeContentMediaSaveTests {
    static func main() {
        let originalFreeContent = NagramiXPrivacySettings.current.allowsFreeContent
        let originalMenu = NagramiXTabSettings.current
        defer {
            NagramiXPrivacySettings.update { $0[.screenshotBypass] = originalFreeContent }
            NagramiXTabSettings.update {
                $0.showForwardWithoutAuthor = originalMenu.showForwardWithoutAuthor
                $0.showBroadcastMessages = originalMenu.showBroadcastMessages
            }
        }

        let ordinary = EngineRawMessage()
        let protected = EngineRawMessage(protected: true)
        let unsupported = EngineRawMessage(protected: true, nagramiXAllowsContentCopy: false)
        let saveFromOpenGallery = { nagramiXCanSaveGalleryMedia(protected, peerIsCopyProtected: false) }
        for forward in [false, true] {
            for broadcast in [false, true] {
                NagramiXTabSettings.update {
                    $0.showForwardWithoutAuthor = forward
                    $0.showBroadcastMessages = broadcast
                }
                precondition(NagramiXTabSettings.current.showForwardWithoutAuthor == forward)
                precondition(NagramiXTabSettings.current.showBroadcastMessages == broadcast)
                for freeContent in [true, false] {
                    NagramiXPrivacySettings.update { $0[.screenshotBypass] = freeContent }
                    precondition(nagramiXAllowsProtectedContentExport(protected) == freeContent)
                    precondition(saveFromOpenGallery() == freeContent)
                    precondition(nagramiXCanSaveGalleryMedia(ordinary, peerIsCopyProtected: true) == freeContent)
                    precondition(nagramiXCanSaveGalleryMedia(ordinary, peerIsCopyProtected: false))
                    precondition(!nagramiXAllowsProtectedContentExport(unsupported))
                    precondition(!nagramiXCanSaveGalleryMedia(unsupported, peerIsCopyProtected: false))
                    for peerProtected in [false, true] {
                        precondition(!nagramiXCanSaveGalleryMedia(.init(paidContent: true), peerIsCopyProtected: peerProtected))
                    }
                }
            }
        }
        print("PASS: chat and gallery saves for all eight setting combinations, exclusions and open-menu rechecks")
    }
}
