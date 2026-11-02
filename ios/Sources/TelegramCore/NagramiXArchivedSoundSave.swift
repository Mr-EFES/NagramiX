import Foundation
import Postbox
import SwiftSignalKit

public enum NagramiXArchivedSoundSaveError {
    case unavailable
    case upload
}

/// Saved notification sounds require a real upload, not the deleted message's
/// cloud document/reference. Read only a bounded complete, independently pinned
/// copy on a worker queue. The native upload updates the existing sounds cache.
public func nagramiXUploadArchivedNotificationSound(account: Account, file: TelegramMediaFile, maxSize: Int64) -> Signal<NotificationSoundList.NotificationSound, NagramiXArchivedSoundSaveError> {
    return Signal { subscriber in
        let disposable = MetaDisposable()
        let cancelled = Atomic<Bool>(value: false)
        Queue.concurrentDefaultQueue().async {
            guard !cancelled.with({ $0 }) else { return }
            let builder = NagramiXArchivedMediaCopy(mediaBox: account.postbox.mediaBox)
            let mimeType = file.mimeType.lowercased()
            guard ["audio/mpeg", "audio/mp3", "audio/mpeg3", "audio/ogg"].contains(mimeType),
                  let retained = builder.prepare(file) as? TelegramMediaFile,
                  let resource = retained.resource as? LocalFileReferenceMediaResource,
                  let size = resource.size, size > 0, size <= min(maxSize, 1 * 1024 * 1024),
                  let data = try? Data(contentsOf: URL(fileURLWithPath: resource.localFilePath), options: .mappedIfSafe),
                  Int64(data.count) == size else {
                subscriber.putError(.unavailable)
                return
            }
            guard !cancelled.with({ $0 }) else { return }
            let title = file.fileName ?? (mimeType == "audio/ogg" ? "voice.ogg" : "sound.mp3")
            disposable.set(_internal_uploadNotificationSound(account: account, title: title, data: data, mimeType: mimeType == "audio/ogg" ? "audio/ogg" : "audio/mpeg").start(next: { sound in
                subscriber.putNext(sound)
            }, error: { _ in
                subscriber.putError(.upload)
            }, completed: {
                subscriber.putCompletion()
            }))
        }
        return ActionDisposable {
            _ = cancelled.swap(true)
            disposable.dispose()
        }
    }
}
