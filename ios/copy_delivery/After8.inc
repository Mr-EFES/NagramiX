import Foundation
import Postbox
import SwiftSignalKit

public extension NagramiXArchivedMediaCopy {
    convenience init(account: Account) {
        self.init(mediaBox: account.postbox.mediaBox)
    }
}

public func nagramiXFetchContentCopyMedia(account: Account, messages: [EngineRawMessage], accountPeerId: EnginePeer.Id? = nil) -> Signal<Bool, NoError> {
    return nagramiXFetchContentCopyMedia(mediaBox: account.postbox.mediaBox, messages: messages, accountPeerId: accountPeerId)
}

public func nagramiXKeepMediaResource(account: Account, resource: TelegramMediaResource) -> Disposable {
    return account.postbox.mediaBox.keepResource(id: resource.id).start()
}

public func nagramiXMediaResourceData(account: Account, resource: TelegramMediaResource) -> Signal<EngineRawMediaResourceData, NoError> {
    return account.postbox.mediaBox.resourceData(resource)
}

public func nagramiXEnsureDownloadedNotificationSounds(account: Account) -> Signal<Never, NoError> {
    return ensureDownloadedNotificationSoundList(postbox: account.postbox)
}

public func nagramiXRefreshNotificationSounds(account: Account) -> Signal<Never, NoError> {
    return refreshNotificationSoundList(postbox: account.postbox, network: account.network)
}


public func nagramiXPrepareCopyMedia(account: Account, messages: [EngineRawMessage]) -> Signal<NagramiXCopyMediaPreparationEvent, NoError> {
    return nagramiXPrepareCopyMedia(mediaBox: account.postbox.mediaBox, messages: messages)
}
