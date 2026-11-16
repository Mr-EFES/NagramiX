import Foundation
import UIKit
import Photos
import SwiftSignalKit
import TelegramCore
import AccountContext
import LegacyMediaPickerUI
import MediaEditor

func nagramiXOriginalGalleryVideoIdentifier(_ item: ChatMediaSendItem) -> String? {
    guard case let .libraryAsset(identifier, _, isVideo, _) = item.source, isVideo,
          item.thumbnail != nil, item.stickers.isEmpty,
          item.options.timer == nil || item.options.timer == 0,
          item.options.price == nil,
          !item.options.isAnimation, !item.options.isMuted,
          !item.options.hasAnimatedPainting, !item.options.isLivePhoto,
          !item.options.livePhotoLoopOrBounce, !item.options.nagramiXRoundVideo else { return nil }
    if let values = item.values {
        guard !chatMediaEditorValuesHaveVisualEdits(values),
              !values.videoBounce, !values.videoIsMuted, !values.videoIsMirrored, !values.cropMirroring,
              values.videoVolume == nil || values.videoVolume == 1.0,
              values.additionalVideoPath == nil, !values.additionalVideoIsDual,
              values.collage.isEmpty, values.maskDrawing == nil else { return nil }
        switch values.qualityPreset {
        case nil, .compressedDefault?, .compressedVeryLow?, .compressedLow?, .compressedMedium?, .compressedHigh?, .compressedVeryHigh?, .passthrough?, .quality?: break
        default: return nil
        }
    }
    return identifier
}

private struct NagramiXOriginalVideoPreparation {
    let item: ChatMediaSendItem
    let isOriginalDocument: Bool
}

private func nagramiXOriginalVideoFailedItem(_ item: ChatMediaSendItem) -> ChatMediaSendItem {
    var result = item
    result.source = .prebuilt(media: nil)
    result.values = nil
    return result
}

func nagramiXPrepareOriginalGalleryVideos(context: AccountContext, items: [ChatMediaSendItem], global: ChatMediaSendGlobalOptions, enabled: Bool) -> Signal<(items: [ChatMediaSendItem], global: ChatMediaSendGlobalOptions), NoError> {
    guard enabled else { return .single((items, global)) }
    let signals: [Signal<NagramiXOriginalVideoPreparation, NoError>] = items.map { item in
        guard let identifier = nagramiXOriginalGalleryVideoIdentifier(item), let thumbnail = item.thumbnail else {
            return .single(NagramiXOriginalVideoPreparation(item: item, isOriginalDocument: false))
        }
        let assets = PHAsset.fetchAssets(withLocalIdentifiers: [identifier], options: nil)
        guard let asset = assets.firstObject, asset.mediaType == .video else {
            return .single(NagramiXOriginalVideoPreparation(item: nagramiXOriginalVideoFailedItem(item), isOriginalDocument: false))
        }
        guard !asset.mediaSubtypes.contains(.videoHighFrameRate) else {
            return .single(NagramiXOriginalVideoPreparation(item: item, isOriginalDocument: false))
        }
        return nagramiXOriginalVideoFile(account: context.account, asset: asset, thumbnail: thumbnail, cover: item.coverImage)
        |> map { file -> NagramiXOriginalVideoPreparation in
            var result = item
            result.source = .prebuilt(media: file)
            result.values = nil
            return NagramiXOriginalVideoPreparation(item: result, isOriginalDocument: !file.isVideo)
        }
        |> `catch` { _ -> Signal<NagramiXOriginalVideoPreparation, NoError> in
            // A failed original export is reported by the existing skipped-item
            // outcome; it must not silently change into a compressed upload.
            return .single(NagramiXOriginalVideoPreparation(item: nagramiXOriginalVideoFailedItem(item), isOriginalDocument: false))
        }
    }
    return chatMediaSendBoundedCombine(signals, maxConcurrent: 1)
    |> map { results -> (items: [ChatMediaSendItem], global: ChatMediaSendGlobalOptions) in
        var sendGlobal = global
        // Rare unsupported original containers stay documents. Avoid mixing
        // those documents with a photo/video album while retaining item order.
        if results.contains(where: { $0?.isOriginalDocument == true }) { sendGlobal.grouping = false }
        let prepared = items.enumerated().map { index, item in
            return results.indices.contains(index) ? (results[index]?.item ?? nagramiXOriginalVideoFailedItem(item)) : nagramiXOriginalVideoFailedItem(item)
        }
        return (prepared, sendGlobal)
    }
}
