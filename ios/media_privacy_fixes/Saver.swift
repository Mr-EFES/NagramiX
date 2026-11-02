import Foundation
import Photos
import SwiftSignalKit
import TelegramCore
import AccountContext
import DeviceAccess

public enum NagramiXStorySaveError: Error, Equatable {
    case unavailable
    case permissionDenied
    case library
}

// Saving a viewable story fetches its resource only: no read, reaction or repost
// operation is issued. Success means Photos committed the asset, not just that
// a fetch signal completed or a permission dialog was dismissed.
public func nagramiXSaveStoryToCameraRoll(context: AccountContext, userLocation: MediaResourceUserLocation, mediaReference: AnyMediaReference) -> Signal<Float, NagramiXStorySaveError> {
    guard case let .story(peer, id, _) = mediaReference else { return .fail(.unavailable) }
    let resource: TelegramMediaResource
    if let image = mediaReference.media as? TelegramMediaImage, let representation = largestImageRepresentation(image.representations) {
        resource = representation.resource
    } else if let file = mediaReference.media as? TelegramMediaFile, file.isVideo || file.mimeType.hasPrefix("video/") {
        resource = file.resource
    } else {
        return .fail(.unavailable)
    }
    let key = "\(context.account.peerId.toInt64()):\(peer.id.toInt64()):\(id):\(resource.id.stringRepresentation)"
    return Signal { subscriber in
        let active = Atomic<Bool>(value: true)
        let subscription = MetaDisposable()
        Queue.mainQueue().async {
            guard active.with({ $0 }) else { return }
            let job: NagramiXStorySaveJob
            let isNew: Bool
            if let current = NagramiXStorySaveJob.jobs[key] {
                job = current
                isNew = false
            } else {
                job = NagramiXStorySaveJob(key: key)
                NagramiXStorySaveJob.jobs[key] = job
                isNew = true
            }
            subscription.set(job.subscribe { event in
                guard active.with({ $0 }) else { return }
                switch event {
                case let .progress(value): subscriber.putNext(value)
                case .saved:
                    subscriber.putNext(1.0)
                    subscriber.putCompletion()
                case let .failed(error): subscriber.putError(error)
                }
            })
            if isNew {
                job.start { beginCommit in
                    nagramiXPerformStorySave(context: context, userLocation: userLocation, mediaReference: mediaReference, beginCommit: beginCommit)
                }
            }
        }
        return ActionDisposable {
            _ = active.swap(false)
            subscription.dispose()
        }
    }
}

private func nagramiXPerformStorySave(context: AccountContext, userLocation: MediaResourceUserLocation, mediaReference: AnyMediaReference, beginCommit: @escaping () -> Void) -> Signal<Float, NagramiXStorySaveError> {
    let resource: TelegramMediaResource
    let isImage: Bool
    if let image = mediaReference.media as? TelegramMediaImage, let representation = largestImageRepresentation(image.representations) {
        resource = representation.resource
        isImage = true
    } else if let file = mediaReference.media as? TelegramMediaFile, file.isVideo || file.mimeType.hasPrefix("video/") {
        resource = file.resource
        isImage = false
    } else {
        return .fail(.unavailable)
    }

    return Signal { subscriber in
        let active = Atomic<Bool>(value: true)
        let saving = Atomic<Bool>(value: false)
        let disposables = DisposableSet()
        let fail: (NagramiXStorySaveError) -> Void = { error in
            if active.swap(false) {
                disposables.dispose()
                subscriber.putError(error)
            }
        }
        DeviceAccess.authorizeAccess(to: .mediaLibrary(.save), presentationData: context.sharedContext.currentPresentationData.with { $0 }, present: { controller, arguments in
            context.sharedContext.presentGlobalController(controller, arguments)
        }, openSettings: context.sharedContext.applicationBindings.openSettings, { authorized in
            guard active.with({ $0 }) else { return }
            guard authorized else {
                fail(.permissionDenied)
                return
            }
            disposables.add(nagramiXKeepMediaResource(account: context.account, resource: resource))
            disposables.add(context.engine.resources.fetch(reference: mediaReference.resourceReference(resource), userLocation: userLocation, userContentType: .story, reportResultStatus: true).start(error: { _ in
                if !saving.with({ $0 }) { fail(.unavailable) }
            }))
            disposables.add(context.engine.resources.status(resource: EngineMediaResource(resource)).start(next: { status in
                guard active.with({ $0 }) else { return }
                if case let .Fetching(_, progress) = status, progress.isFinite {
                    subscriber.putNext(min(0.9, max(0, progress * 0.9)))
                }
            }))
            disposables.add((context.engine.resources.data(resource: EngineMediaResource(resource), pathExtension: isImage ? "jpg" : "mp4", waitUntilFetchStatus: true)
            |> filter { $0.isComplete }
            |> take(1)).start(next: { data in
                guard active.with({ $0 }), !saving.swap(true) else { return }
                Queue.concurrentDefaultQueue().async {
                    guard active.with({ $0 }) else { return }
                    let temporary = EngineTempBox.shared.tempFile(fileName: isImage ? "story.jpg" : "story.mp4")
                    do {
                        do { try FileManager.default.linkItem(atPath: data.path, toPath: temporary.path) }
                        catch { try FileManager.default.copyItem(atPath: data.path, toPath: temporary.path) }
                    } catch {
                        EngineTempBox.shared.dispose(temporary)
                        fail(.unavailable)
                        return
                    }
                    guard active.with({ $0 }) else {
                        EngineTempBox.shared.dispose(temporary)
                        return
                    }
                    // Keep the pinned local file until Photos finishes, even if
                    // the user cancels while its transaction is in flight.
                    Queue.mainQueue().async {
                        guard active.with({ $0 }) else {
                            EngineTempBox.shared.dispose(temporary)
                            return
                        }
                        beginCommit()
                        PHPhotoLibrary.shared().performChanges({
                            PHAssetCreationRequest.forAsset().addResource(with: isImage ? .photo : .video, fileURL: URL(fileURLWithPath: temporary.path), options: nil)
                        }, completionHandler: { success, error in
                            EngineTempBox.shared.dispose(temporary)
                            guard active.swap(false) else { return }
                            disposables.dispose()
                            if success && error == nil {
                                subscriber.putNext(1.0)
                                subscriber.putCompletion()
                            } else {
                                subscriber.putError(.library)
                            }
                        })
                    }
                }
            }))
        })
        return ActionDisposable {
            _ = active.swap(false)
            disposables.dispose()
        }
    }
}
