import Foundation
import UIKit
import Photos
import SwiftSignalKit
import TelegramCore
import AccountContext
import LegacyMediaPickerUI
import MediaEditor

func nagramiXOriginalGalleryVideoIdentifier(_ item: ChatMediaSendItem) -> String? {
    guard case let .libraryAsset(identifier, _, isVideo, duration) = item.source, isVideo,
          item.stickers.isEmpty,
          item.options.timer == nil || item.options.timer == 0,
          item.options.price == nil,
          !item.options.isAnimation, !item.options.isMuted,
          !item.options.hasAnimatedPainting, !item.options.isLivePhoto,
          !item.options.livePhotoLoopOrBounce, !item.options.nagramiXRoundVideo else { return nil }
    if let values = item.values {
        let comparisonValues: MediaEditorValues
        if let trimRange = values.videoTrimRange {
            guard duration.isFinite, duration > 0.0,
                  abs(trimRange.lowerBound) < 0.001, abs(trimRange.upperBound - duration) < 0.001 else { return nil }
            comparisonValues = values.withUpdatedVideoTrimRange(nil)
        } else {
            comparisonValues = values
        }
        guard !chatMediaEditorValuesHaveVisualEdits(comparisonValues),
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
        guard let identifier = nagramiXOriginalGalleryVideoIdentifier(item) else {
            return .single(NagramiXOriginalVideoPreparation(item: item, isOriginalDocument: false))
        }
        let assets = PHAsset.fetchAssets(withLocalIdentifiers: [identifier], options: nil)
        guard let asset = assets.firstObject, asset.mediaType == .video else {
            return .single(NagramiXOriginalVideoPreparation(item: nagramiXOriginalVideoFailedItem(item), isOriginalDocument: false))
        }
        return nagramiXOriginalVideoFile(account: context.account, asset: asset, thumbnail: item.thumbnail, cover: item.coverImage)
        |> map { file -> NagramiXOriginalVideoPreparation in
            guard file.isVideo else {
                return NagramiXOriginalVideoPreparation(item: nagramiXOriginalVideoFailedItem(item), isOriginalDocument: false)
            }
            var result = item
            result.source = .prebuilt(media: file)
            result.values = nil
            return NagramiXOriginalVideoPreparation(item: result, isOriginalDocument: false)
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
        // Original preparation must keep ordinary video metadata, never a document fallback.
        // Preserve the incoming photo/video album semantics and item order.
        if results.contains(where: { $0?.isOriginalDocument == true }) { sendGlobal.grouping = false }
        let prepared = items.enumerated().map { index, item in
            return results.indices.contains(index) ? (results[index]?.item ?? nagramiXOriginalVideoFailedItem(item)) : nagramiXOriginalVideoFailedItem(item)
        }
        return (prepared, sendGlobal)
    }
}
