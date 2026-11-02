import Foundation
import UIKit
import Photos
import Postbox
import SwiftSignalKit
import TelegramCore
import AccountContext
import DeviceAccess
import Display
import AppBundle
import ContextUI
import ChatControllerInteraction
import TelegramPresentationData
import TelegramStringFormatting
import PresentationDataUtils
import NagramiXCore
import UndoUI
import SettingsUI

private enum NagramiXArchivedVideoSaveResult {
    case saved
    case denied
    case unavailable
    case failed
}

/// Photos keeps its own copy. Pin an export URL before asking for permission so
/// clearing the archive cannot remove bytes from an already requested save.
private func nagramiXSaveArchivedVideo(context: AccountContext, file: TelegramMediaFile) -> Signal<NagramiXArchivedVideoSaveResult, NoError> {
    return Signal { subscriber in
        let cancelled = Atomic<Bool>(value: false)
        Queue.concurrentDefaultQueue().async {
            guard !cancelled.with({ $0 }) else { return }
            let builder = NagramiXArchivedMediaCopy(mediaBox: context.account.postbox.mediaBox)
            guard let retained = builder.prepare(file) as? TelegramMediaFile, let resource = retained.resource as? LocalFileReferenceMediaResource else {
                subscriber.putNext(.unavailable)
                subscriber.putCompletion()
                return
            }
            let tempFile = EngineTempBox.shared.tempFile(fileName: file.mimeType.lowercased() == "video/quicktime" ? "video.mov" : "video.mp4")
            do {
                do {
                    try FileManager.default.linkItem(atPath: resource.localFilePath, toPath: tempFile.path)
                } catch {
                    try FileManager.default.copyItem(atPath: resource.localFilePath, toPath: tempFile.path)
                }
            } catch {
                EngineTempBox.shared.dispose(tempFile)
                subscriber.putNext(.failed)
                subscriber.putCompletion()
                return
            }
            Queue.mainQueue().async {
                guard !cancelled.with({ $0 }) else {
                    EngineTempBox.shared.dispose(tempFile)
                    return
                }
                DeviceAccess.authorizeAccess(to: .mediaLibrary(.save), presentationData: context.sharedContext.currentPresentationData.with { $0 }, present: { controller, arguments in
                    context.sharedContext.presentGlobalController(controller, arguments)
                }, openSettings: context.sharedContext.applicationBindings.openSettings, { authorized in
                    guard authorized, !cancelled.with({ $0 }) else {
                        EngineTempBox.shared.dispose(tempFile)
                        if !cancelled.with({ $0 }) {
                            subscriber.putNext(.denied)
                            subscriber.putCompletion()
                        }
                        return
                    }
                    PHPhotoLibrary.shared().performChanges({
                        PHAssetCreationRequest.forAsset().addResource(with: .video, fileURL: URL(fileURLWithPath: tempFile.path), options: nil)
                    }, completionHandler: { success, _ in
                        EngineTempBox.shared.dispose(tempFile)
                        if !cancelled.with({ $0 }) {
                            subscriber.putNext(success ? .saved : .failed)
                            subscriber.putCompletion()
                        }
                    })
                })
            }
        }
        return ActionDisposable {
            // A Photos write already submitted cannot be cancelled; its own
            // completion still disposes the pinned URL, without a stale toast.
            _ = cancelled.swap(true)
        }
    }
}

func nagramiXArchivedSaveMediaActions(context: AccountContext, message: Message, isCopyProtected: Bool, notificationSoundList: NotificationSoundList?, controllerInteraction: ChatControllerInteraction, strings: PresentationStrings) -> [ContextMenuItem] {
    guard !isCopyProtected, !message.containsSecretMedia else { return [] }
    for media in message.effectiveMedia {
        guard let file = media as? TelegramMediaFile else { continue }
        if file.isVideo || file.isInstantVideo {
            return [.action(ContextMenuActionItem(text: strings.Gallery_SaveVideo, icon: { theme in
                generateTintedImage(image: UIImage(bundleImageName: "Chat/Context Menu/Save"), color: theme.actionSheet.primaryTextColor)
            }, action: { _, dismiss in
                dismiss(.default)
                let _ = (nagramiXSaveArchivedVideo(context: context, file: file)
                |> deliverOnMainQueue).startStandalone(next: { result in
                    switch result {
                    case .saved:
                        controllerInteraction.displayUndo(.mediaSaved(text: strings.Gallery_VideoSaved))
                    case .unavailable:
                        controllerInteraction.displayUndo(.info(title: nil, text: strings.nagramiXArchiveSaveUnavailable, timeout: nil, customUndoText: nil))
                    case .failed:
                        controllerInteraction.displayUndo(.info(title: nil, text: strings.nagramiXArchiveSaveFailed, timeout: nil, customUndoText: nil))
                    case .denied:
                        break // DeviceAccess presents the native settings prompt.
                    }
                })
            })), .separator]
        }
        // Match the native Save Sound eligibility and server-configured limits.
        if let size = file.size, size < 1 * 1024 * 1024,
           let duration = file.duration, duration < 60,
           ["audio/mpeg", "audio/mp3", "audio/mpeg3", "audio/ogg"].contains(file.mimeType.lowercased()),
           !(notificationSoundList?.sounds.contains(where: { $0.file.fileId == file.fileId }) ?? false) {
            return [.action(ContextMenuActionItem(text: strings.Chat_SaveForNotifications, icon: { theme in
                generateTintedImage(image: UIImage(bundleImageName: "Chat/Context Menu/DownloadTone"), color: theme.actionSheet.primaryTextColor)
            }, action: { _, dismiss in
                dismiss(.default)
                let presentationData = context.sharedContext.currentPresentationData.with { $0 }
                let settings = NotificationSoundSettings.extract(from: context.currentAppConfiguration.with { $0 })
                if size > settings.maxSize {
                    controllerInteraction.displayUndo(.info(title: strings.Notifications_UploadError_TooLarge_Title, text: strings.Notifications_UploadError_TooLarge_Text(dataSizeString(Int64(settings.maxSize), formatting: DataSizeStringFormatting(presentationData: presentationData))).string, timeout: nil, customUndoText: nil))
                } else if Double(duration) > Double(settings.maxDuration) {
                    controllerInteraction.displayUndo(.info(title: strings.Notifications_UploadError_TooLong_Title(file.fileName ?? "Tone").string, text: strings.Notifications_UploadError_TooLong_Text(stringForDuration(Int32(settings.maxDuration))).string, timeout: nil, customUndoText: nil))
                } else {
                    let _ = (nagramiXUploadArchivedNotificationSound(account: context.account, file: file, maxSize: Int64(settings.maxSize))
                    |> deliverOnMainQueue).startStandalone(next: { _ in
                        controllerInteraction.displayUndo(.notificationSoundAdded(title: strings.Notifications_UploadSuccess_Title, text: strings.Notifications_SaveSuccess_Text, action: {
                            controllerInteraction.navigationController()?.pushViewController(notificationsAndSoundsController(context: context, exceptionsList: nil))
                        }))
                    }, error: { error in
                        let text: String
                        switch error {
                        case .unavailable: text = strings.nagramiXArchiveSaveUnavailable
                        case .upload: text = strings.nagramiXArchiveSaveFailed
                        }
                        controllerInteraction.displayUndo(.info(title: nil, text: text, timeout: nil, customUndoText: nil))
                    })
                }
            })), .separator]
        }
    }
    return []
}
