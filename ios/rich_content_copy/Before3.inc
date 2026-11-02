import Foundation
import TelegramCore
import SwiftSignalKit
import Display
import AccountContext
import ChatInterfaceState
import OverlayStatusController
import PresentationDataUtils
import NagramiXCore
import NagramiXMediaSettings
import SaveToCameraRoll
import LegacyMediaPickerUI

func nagramiXAllowsProtectedContentExport(_ message: EngineRawMessage) -> Bool {
    let settings = NagramiXTabSettings.current
    return NagramiXPrivacySettings.current.bypassScreenshots && (settings.showForwardWithoutAuthor || settings.showBroadcastMessages) && message.nagramiXAllowsContentCopy
}

private final class NagramiXProtectedExportLease {
    private var cleanup: (() -> Void)?
    init(_ cleanup: @escaping () -> Void) { self.cleanup = cleanup }
    func dispose() { let cleanup = self.cleanup; self.cleanup = nil; cleanup?() }
    deinit { self.dispose() }
}

private func nagramiXProtectedExportFileName(_ file: TelegramMediaFile) -> String {
    if let name = file.fileName {
        let component = (name as NSString).lastPathComponent.replacingOccurrences(of: "/", with: "_")
        if !component.isEmpty && component != "." && component != ".." { return component }
    }
    switch file.mimeType.lowercased() {
    case "video/mp4": return "Video.mp4"
    case "video/quicktime": return "Video.mov"
    case "application/pdf": return "Document.pdf"
    case "audio/ogg": return "Audio.ogg"
    default: return "File"
    }
}

private func nagramiXProtectedSaveAlert(context: AccountContext) -> ViewController {
    let strings = context.sharedContext.currentPresentationData.with { $0 }.strings
    return textAlertController(context: context, title: nil, text: strings.nagramiXArchiveSaveFailed, actions: [TextAlertAction(type: .defaultAction, title: strings.Common_OK, action: {})])
}

func nagramiXSaveCopiedMediaToFiles(context: AccountContext, fileReference: FileMediaReference, present: @escaping (ViewController, Any?) -> Void) -> Disposable {
    if fileReference.media.isMusic {
        return saveMediaToFiles(context: context, fileReference: fileReference, present: present)
    }
    // The native music exporter assumes an mp3 file. Other protected documents
    // use the same native fetch/picker with a pinned, correctly named full file.
    let cancelled = Atomic<Bool>(value: false)
    let started = Atomic<Bool>(value: false)
    let finished = Atomic<Bool>(value: false)
    let disposable = MetaDisposable()
    let progress = OverlayStatusController(theme: context.sharedContext.currentPresentationData.with { $0 }.theme, type: .loading(cancelled: {
        _ = cancelled.swap(true)
        disposable.set(nil)
    }))
    Queue.mainQueue().after(0.15) { [weak progress] in
        guard !finished.with({ $0 }), let progress else { return }
        present(progress, nil)
    }
    disposable.set((fetchMediaData(context: context, userLocation: .other, mediaReference: fileReference.abstract)
    |> deliverOnMainQueue
    |> afterDisposed { [progress] in
        _ = finished.swap(true)
        Queue.mainQueue().async { progress.dismiss() }
    }).startStrict(next: { state, _ in
        guard case let .data(data) = state, data.isComplete, !started.swap(true), !cancelled.with({ $0 }) else { return }
        _ = finished.swap(true)
        progress.dismiss()
        Queue.concurrentDefaultQueue().async {
            guard !cancelled.with({ $0 }) else { return }
            let tempFile = EngineTempBox.shared.tempFile(fileName: nagramiXProtectedExportFileName(fileReference.media))
            let lease = NagramiXProtectedExportLease { EngineTempBox.shared.dispose(tempFile) }
            do {
                do { try FileManager.default.linkItem(atPath: data.path, toPath: tempFile.path) }
                catch { try FileManager.default.copyItem(atPath: data.path, toPath: tempFile.path) }
            } catch {
                lease.dispose()
                Queue.mainQueue().async {
                    if !cancelled.with({ $0 }) { present(nagramiXProtectedSaveAlert(context: context), nil) }
                }
                return
            }
            Queue.mainQueue().async {
                guard !cancelled.with({ $0 }) else { lease.dispose(); return }
                let picker = legacyICloudFilePicker(theme: context.sharedContext.currentPresentationData.with { $0 }.theme, mode: .export, url: URL(fileURLWithPath: tempFile.path), documentTypes: [], forceDarkTheme: false, dismissed: { lease.dispose() }, completion: { _ in lease.dispose() })
                present(picker, nil)
            }
        }
    }, completed: {
        if !started.with({ $0 }) && !cancelled.with({ $0 }) {
            present(nagramiXProtectedSaveAlert(context: context), nil)
        }
    }))
    return ActionDisposable {
        _ = cancelled.swap(true)
        disposable.dispose()
    }
}

extension ChatControllerImpl {
    func nagramiXPrepareProtectedCopy(messages: [EngineRawMessage], completion: @escaping () -> Void) {
        let finished = Atomic<Bool>(value: false)
        let progress = OverlayStatusController(theme: self.presentationData.theme, type: .loading(cancelled: { [weak self] in
            _ = finished.swap(true)
            self?.nagramiXContentCopyDisposable.set(nil)
        }))
        // Cached media and text must not flash a loading screen.
        Queue.mainQueue().after(0.15) { [weak self, weak progress] in
            guard !finished.with({ $0 }), let self, let progress else { return }
            self.present(progress, in: .window(.root))
        }
        self.nagramiXContentCopyDisposable.set((nagramiXFetchContentCopyMedia(account: self.context.account, messages: messages, accountPeerId: self.context.account.peerId)
        |> deliverOnMainQueue
        |> afterDisposed { [progress] in
            _ = finished.swap(true)
            Queue.mainQueue().async { progress.dismiss() }
        }).startStrict(next: { [weak self, weak progress] available in
            _ = finished.swap(true)
            guard let self else { return }
            progress?.dismiss()
            if available {
                completion()
            } else {
                self.present(nagramiXArchivedCopyAlert(context: self.context), in: .window(.root))
            }
        }))
    }
}
