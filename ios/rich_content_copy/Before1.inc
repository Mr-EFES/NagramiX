import Foundation
import Postbox
import SwiftSignalKit

public extension Message {
    /// Only the account's own, already-sent recording may be uploaded again.
    /// Keep this separate from general export: incoming view-once media stays
    /// excluded, and this exception does not enable saving or server forwards.
    func nagramiXAllowsOwnViewOnceCopy(accountPeerId: PeerId?) -> Bool {
        guard let accountPeerId,
              self.author?.id == accountPeerId,
              !self.flags.contains(.Incoming), !self.flags.isSending, !self.flags.contains(.Failed),
              self.forwardInfo == nil,
              self.id.namespace == Namespaces.Message.Cloud,
              self.id.peerId.namespace == Namespaces.Peer.CloudUser,
              self.id.peerId != accountPeerId, !self.id.peerId.isVerificationCodes,
              self.minAutoremoveOrClearTimeout == viewOnceTimeout,
              self.media.count == 1, let file = self.media.first as? TelegramMediaFile else {
            return false
        }
        return file.isVoice || file.isInstantVideo
    }

    func nagramiXHasLocalViewOnceRecording(mediaBox: MediaBox) -> Bool {
        guard self.media.count == 1, let file = self.media.first as? TelegramMediaFile,
              let path = (file.resource as? LocalFileReferenceMediaResource)?.localFilePath ?? mediaBox.completedResourcePath(file.resource),
              let attributes = try? FileManager.default.attributesOfItem(atPath: path),
              attributes[.type] as? FileAttributeType == .typeRegular,
              let size = (attributes[.size] as? NSNumber)?.int64Value else { return false }
        return size > 0 && (file.size == nil || file.size == size)
    }

    var nagramiXAllowsContentCopy: Bool {
        return self.id.peerId.namespace != Namespaces.Peer.SecretChat
            && !self.id.peerId.isVerificationCodes
            && !self.containsSecretMedia
            && self.minAutoremoveOrClearTimeout != viewOnceTimeout
            && !self.flags.isSending && !self.flags.contains(.Failed)
            && !self.media.contains(where: { $0 is TelegramMediaPaidContent || $0 is TelegramMediaExpiredContent || $0 is TelegramMediaAction })
    }
}

private enum NagramiXContentCopyFetchError: Error { case unavailable }

/// Fetch only primary attachments explicitly selected by the user. This does
/// not consume media, mark history read, or create outgoing messages.
public func nagramiXFetchContentCopyMedia(mediaBox: MediaBox, messages: [Message], accountPeerId: PeerId? = nil) -> Signal<Bool, NoError> {
    var references: [String: (PeerId, MediaResourceReference)] = [:]
    for message in messages {
        if message.nagramiXAllowsOwnViewOnceCopy(accountPeerId: accountPeerId) {
            // Do not open, consume or remotely fetch a view-once original.
            // A new upload is possible only while its full local bytes exist.
            guard message.nagramiXHasLocalViewOnceRecording(mediaBox: mediaBox) else { return .single(false) }
            continue
        }
        guard message.nagramiXAllowsContentCopy else { return .single(false) }
        for media in message.media {
            let resource: TelegramMediaResource
            if let image = media as? TelegramMediaImage {
                guard let largest = image.representations.max(by: { lhs, rhs in
                    Int64(lhs.dimensions.width) * Int64(lhs.dimensions.height) < Int64(rhs.dimensions.width) * Int64(rhs.dimensions.height)
                }) else { return .single(false) }
                resource = largest.resource
            } else if let file = media as? TelegramMediaFile {
                resource = file.resource
            } else {
                continue
            }
            let reference = AnyMediaReference.message(message: MessageReference(message), media: media).resourceReference(resource)
            references[resource.id.stringRepresentation] = (message.id.peerId, reference)
        }
    }
    guard !references.isEmpty else { return .single(true) }
    let signals: [Signal<Bool, NagramiXContentCopyFetchError>] = references.values.map { peerId, reference in
        Signal { subscriber in
            let finished = Atomic<Bool>(value: false)
            let disposables = DisposableSet()
            disposables.add(mediaBox.keepResource(id: reference.resource.id).start())
            disposables.add((mediaBox.resourceData(reference.resource)
            |> filter { $0.complete }
            |> take(1)).start(next: { data in
                guard !finished.swap(true) else { return }
                if data.offset == 0 && data.size > 0 {
                    subscriber.putNext(true)
                    subscriber.putCompletion()
                } else {
                    subscriber.putError(.unavailable)
                }
            }))
            if !finished.with({ $0 }) {
                disposables.add(fetchedMediaResource(mediaBox: mediaBox, userLocation: .peer(peerId), userContentType: .other, reference: reference, reportResultStatus: true).start(error: { _ in
                    guard !finished.swap(true) else { return }
                    subscriber.putError(.unavailable)
                }))
            }
            return ActionDisposable {
                _ = finished.swap(true)
                disposables.dispose()
            }
        }
    }
    return combineLatest(signals)
    |> take(1)
    |> map { $0.allSatisfy { $0 } }
    |> `catch` { _ -> Signal<Bool, NoError> in .single(false) }
}
