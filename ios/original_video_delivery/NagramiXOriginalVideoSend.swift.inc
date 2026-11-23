import Foundation
import UIKit
import Photos
import SwiftSignalKit
import TelegramCore
import AccountContext
import LegacyMediaPickerUI
import MediaEditor

func nagramiXOriginalVideoPreservesContent(_ values: MediaEditorValues?, duration: Double) -> Bool {
    if let values {
        let comparisonValues: MediaEditorValues
        if let trimRange = values.videoTrimRange {
            guard duration.isFinite, duration > 0.0,
                  abs(trimRange.lowerBound) < 0.001, abs(trimRange.upperBound - duration) < 0.001 else { return false }
            comparisonValues = values.withUpdatedVideoTrimRange(nil)
        } else {
            comparisonValues = values
        }
        guard !chatMediaEditorValuesHaveVisualEdits(comparisonValues),
              !values.videoBounce, !values.videoIsMuted, !values.videoIsMirrored, !values.cropMirroring,
              values.videoVolume == nil || values.videoVolume == 1.0,
              values.additionalVideoPath == nil, !values.additionalVideoIsDual,
              values.collage.isEmpty, values.maskDrawing == nil else { return false }
        switch values.qualityPreset {
        case nil, .compressedDefault?, .compressedVeryLow?, .compressedLow?, .compressedMedium?, .compressedHigh?, .compressedVeryHigh?, .passthrough?, .quality?: break
        default: return false
        }
    }
    return true
}

private func nagramiXOriginalItemVideo(context: AccountContext, item: ChatMediaSendItem) -> Signal<TelegramMediaFile, Void>? {
    guard item.stickers.isEmpty, !item.options.isAnimation, !item.options.isMuted,
          !item.options.hasAnimatedPainting, !item.options.isLivePhoto,
          !item.options.livePhotoLoopOrBounce, !item.options.nagramiXRoundVideo else { return nil }
    switch item.source {
    case let .libraryAsset(identifier, _, true, duration):
        guard nagramiXOriginalVideoPreservesContent(item.values, duration: duration) else { return nil }
        let assets = PHAsset.fetchAssets(withLocalIdentifiers: [identifier], options: nil)
        guard let asset = assets.firstObject, asset.mediaType == .video else { return .fail(Void()) }
        return nagramiXOriginalVideoFile(account: context.account, asset: asset, thumbnail: item.thumbnail, cover: item.coverImage)
    case let .tempVideo(path, _, duration):
        guard nagramiXOriginalVideoPreservesContent(item.values, duration: duration) else { return nil }
        return nagramiXOriginalCameraVideoFile(account: context.account, path: path, thumbnail: item.thumbnail, cover: item.coverImage)
    default:
        return nil
    }
}

private func nagramiXOriginalVideoFailedItem(_ item: ChatMediaSendItem) -> ChatMediaSendItem {
    var result = item
    result.source = .prebuilt(media: nil)
    result.values = nil
    return result
}

func nagramiXPrepareOriginalGalleryVideos(context: AccountContext, items: [ChatMediaSendItem], global: ChatMediaSendGlobalOptions, enabled: Bool) -> Signal<(items: [ChatMediaSendItem], global: ChatMediaSendGlobalOptions), NoError> {
    guard enabled else { return .single((items, global)) }
    let signals = items.map { item -> Signal<ChatMediaSendItem, NoError> in
        guard let original = nagramiXOriginalItemVideo(context: context, item: item) else { return .single(item) }
        return original
        |> map { file -> ChatMediaSendItem in
            var result = item
            result.source = .prebuilt(media: file)
            result.values = nil
            return result
        }
        |> `catch` { _ -> Signal<ChatMediaSendItem, NoError> in
            return .single(nagramiXOriginalVideoFailedItem(item))
        }
    }
    return chatMediaSendBoundedCombine(signals, maxConcurrent: 1)
    |> map { results in
        let prepared = items.enumerated().map { index, item in
            results.indices.contains(index) ? (results[index] ?? nagramiXOriginalVideoFailedItem(item)) : nagramiXOriginalVideoFailedItem(item)
        }
        return (prepared, global)
    }
}
