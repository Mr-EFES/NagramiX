// Included in LegacyMediaPickers.swift; no second uploader or player is needed.
private let nagramiXOriginalVideoQueue = Queue(name: "NagramiXOriginalVideoExport")

private func nagramiXOriginalVideoSupportsStreaming(path: String, size: Int64) -> Bool {
    guard let handle = try? FileHandle(forReadingFrom: URL(fileURLWithPath: path)), size >= 8 else { return false }
    defer { try? handle.close() }
    var offset: UInt64 = 0
    let fileSize = UInt64(size)
    // Only inspect bounded top-level ISO BMFF headers. Never load an mdat into RAM.
    for _ in 0 ..< 1024 {
        guard offset <= fileSize, fileSize - offset >= 8 else { return false }
        do {
            try handle.seek(toOffset: offset)
            guard let header = try handle.read(upToCount: 8), header.count == 8 else { return false }
            let shortSize = header.prefix(4).reduce(UInt64(0)) { ($0 << 8) | UInt64($1) }
            let type = String(bytes: header.suffix(4), encoding: .ascii)
            var boxSize = shortSize
            var headerSize: UInt64 = 8
            if shortSize == 1 {
                guard let extended = try handle.read(upToCount: 8), extended.count == 8 else { return false }
                boxSize = extended.reduce(UInt64(0)) { ($0 << 8) | UInt64($1) }
                headerSize = 16
            } else if shortSize == 0 {
                boxSize = fileSize - offset
            }
            guard boxSize >= headerSize, boxSize <= fileSize - offset else { return false }
            if type == "moov" { return true }
            if type == "mdat" { return false }
            offset += boxSize
        } catch { return false }
    }
    return false
}

private func nagramiXOriginalVideoFile(account: Account, asset: PHAsset, thumbnail: UIImage, cover: UIImage?) -> Signal<TelegramMediaFile, Void> {
    let resources = PHAssetResource.assetResources(for: asset)
    guard let assetResource = resources.first(where: { $0.type == .fullSizeVideo }) ?? resources.first(where: { $0.type == .video }),
          asset.pixelWidth > 0, asset.pixelHeight > 0,
          asset.pixelWidth <= Int(Int32.max), asset.pixelHeight <= Int(Int32.max),
          asset.duration.isFinite, asset.duration > 0 else { return .fail(Void()) }
    let dimensions = PixelDimensions(width: Int32(asset.pixelWidth), height: Int32(asset.pixelHeight))
    let duration = asset.duration
    let name = (assetResource.originalFilename as NSString).lastPathComponent
    let mimeType = UTType(assetResource.uniformTypeIdentifier)?.preferredMIMEType ?? guessMimeTypeByFileExtension((name as NSString).pathExtension)
    return Signal { subscriber in
        let tempFile = EngineTempBox.shared.tempFile(fileName: "original-video")
        guard FileManager.default.createFile(atPath: tempFile.path, contents: nil),
              let handle = try? FileHandle(forWritingTo: URL(fileURLWithPath: tempFile.path)) else {
            EngineTempBox.shared.dispose(tempFile)
            subscriber.putError(Void())
            return EmptyDisposable
        }
        let lock = NSLock()
        var disposed = false
        var finishing = false
        var writeFailed = false
        let options = PHAssetResourceRequestOptions()
        options.isNetworkAccessAllowed = true
        let manager = PHAssetResourceManager.default()
        let requestId = manager.requestData(for: assetResource, options: options, dataReceivedHandler: { data in
            lock.lock()
            defer { lock.unlock() }
            guard !disposed, !finishing, !writeFailed else { return }
            do { try handle.write(contentsOf: data) } catch { writeFailed = true }
        }, completionHandler: { error in
            nagramiXOriginalVideoQueue.async {
                lock.lock()
                if disposed { lock.unlock(); return }
                finishing = true
                do { try handle.close() } catch { writeFailed = true }
                let failed = writeFailed || error != nil
                lock.unlock()
                // Once finishing, this worker owns cleanup even if the picker exits.
                defer { EngineTempBox.shared.dispose(tempFile) }
                let thumbnailSize = CGSize(width: CGFloat(dimensions.width), height: CGFloat(dimensions.height)).aspectFitted(CGSize(width: 320, height: 320))
                guard !failed, let size = engineFileSize(tempFile.path), size > 0,
                      let image = TGScaleImageToPixelSize(thumbnail, thumbnailSize),
                      let thumbnailData = image.jpegData(compressionQuality: 0.4) else {
                    subscriber.putError(Void())
                    return
                }
                var attributes: [TelegramMediaFileAttribute] = [.FileName(fileName: name)]
                // Keep the real MIME/container. Unsupported containers stay original
                // documents instead of silently transcoding or pretending to be MP4.
                if mimeType == "video/mp4" || mimeType == "video/quicktime" {
                    let flags: TelegramMediaVideoFlags = nagramiXOriginalVideoSupportsStreaming(path: tempFile.path, size: size) ? [.supportsStreaming] : []
                    attributes.append(.Video(duration: duration, size: dimensions, flags: flags, preloadSize: nil, coverTime: nil, videoCodec: nil))
                }
                if size > 10 * 1024 * 1024 { attributes.append(.hintFileIsLarge) }
                var videoCover: TelegramMediaImage?
                if let cover {
                    let coverSize = cover.size.aspectFittedOrSmaller(CGSize(width: 1280, height: 1280))
                    guard let coverImage = TGScaleImageToPixelSize(cover, coverSize),
                          let coverData = coverImage.jpegData(compressionQuality: 0.87) else {
                        subscriber.putError(Void())
                        return
                    }
                    let coverResource = LocalFileMediaResource(fileId: Int64.random(in: Int64.min ... Int64.max))
                    lock.lock()
                    guard !disposed else { lock.unlock(); return }
                    account.postbox.mediaBox.storeResourceData(coverResource.id, data: coverData)
                    lock.unlock()
                    let representation = TelegramMediaImageRepresentation(dimensions: PixelDimensions(coverSize), resource: coverResource, progressiveSizes: [], immediateThumbnailData: nil, hasVideo: false, isPersonal: false)
                    videoCover = TelegramMediaImage(imageId: EngineMedia.Id(namespace: 0, id: 0), representations: [representation], immediateThumbnailData: nil, reference: nil, partialReference: nil, flags: [])
                }
                let resource = LocalFileMediaResource(fileId: Int64.random(in: Int64.min ... Int64.max), size: size)
                let previewResource = LocalFileMediaResource(fileId: Int64.random(in: Int64.min ... Int64.max))
                lock.lock()
                guard !disposed else { lock.unlock(); return }
                account.postbox.mediaBox.moveResourceData(resource.id, fromTempPath: tempFile.path)
                account.postbox.mediaBox.storeResourceData(previewResource.id, data: thumbnailData)
                lock.unlock()
                let preview = TelegramMediaImageRepresentation(dimensions: PixelDimensions(thumbnailSize), resource: previewResource, progressiveSizes: [], immediateThumbnailData: nil, hasVideo: false, isPersonal: false)
                let file = TelegramMediaFile(fileId: EngineMedia.Id(namespace: Namespaces.Media.LocalFile, id: Int64.random(in: Int64.min ... Int64.max)), partialReference: nil, resource: resource, previewRepresentations: [preview], videoThumbnails: [], videoCover: videoCover, immediateThumbnailData: nil, mimeType: mimeType, size: size, attributes: attributes, alternativeRepresentations: [])
                subscriber.putNext(file)
                subscriber.putCompletion()
            }
        })
        return ActionDisposable {
            lock.lock()
            disposed = true
            let cleanup = !finishing
            if cleanup { try? handle.close() }
            lock.unlock()
            manager.cancelDataRequest(requestId)
            if cleanup { EngineTempBox.shared.dispose(tempFile) }
        }
    }
}

private func nagramiXPrepareOriginalVideoValue(account: Account, value: Any) -> Signal<Any, Void> {
    guard let dictionary = value as? NSDictionary, let item = dictionary["item"] as? LegacyAssetItemWrapper,
          case let .video(data, thumbnail, cover, adjustments, caption, asFile, asAnimation, stickers) = item.item,
          case let .asset(asset) = data, let photoAsset = asset.backingAsset, let thumbnail,
          !asFile, !asAnimation, stickers.isEmpty, item.timer == nil, item.price == nil,
          !photoAsset.mediaSubtypes.contains(.videoHighFrameRate) else { return .single(value) }
    if let adjustments {
        // A quality preset alone does not edit content. Explicit crop/trim/effects,
        // GIF/mute, drawing and slow-motion edits still use the native converter.
        guard !adjustments.cropApplied(forAvatar: false), adjustments.cropOrientation == .up, !adjustments.cropMirrored,
              abs(adjustments.cropRotation) < 0.0001, !adjustments.trimApplied(),
              !adjustments.toolsApplied(), !adjustments.hasPainting(),
              !adjustments.sendAsGif, !adjustments.bounce else { return .single(value) }
    }
    return nagramiXOriginalVideoFile(account: account, asset: photoAsset, thumbnail: thumbnail, cover: cover)
    |> map { file -> Any in
        let result = dictionary.mutableCopy() as! NSMutableDictionary
        result["item"] = LegacyAssetItemWrapper(item: .originalVideo(file: file, caption: caption), timer: item.timer, spoiler: item.spoiler, price: item.price, forceHd: item.forceHd, groupedId: item.groupedId, uniqueId: item.uniqueId)
        return result
    }
}

private func nagramiXOriginalVideoGroupedValues(_ values: [Any]) -> NSArray {
    func isDocument(_ item: LegacyAssetItem) -> Bool {
        switch item {
        case .file: return true
        case let .originalVideo(file, _): return !file.isVideo
        case let .video(_, _, _, _, _, asFile, _, _): return asFile
        case .image: return false
        }
    }
    var documents = Set<Int64>()
    var media = Set<Int64>()
    for value in values {
        guard let item = (value as? NSDictionary)?["item"] as? LegacyAssetItemWrapper, let group = item.groupedId else { continue }
        if isDocument(item.item) { documents.insert(group) } else { media.insert(group) }
    }
    let mixed = documents.intersection(media)
    guard !mixed.isEmpty else { return NSArray(array: values) }
    var previousGroup: Int64?
    var previousDocument = false
    var runGroup: Int64 = 0
    return NSArray(array: values.map { value -> Any in
        guard let dictionary = value as? NSDictionary, let item = dictionary["item"] as? LegacyAssetItemWrapper,
              let group = item.groupedId, mixed.contains(group) else { previousGroup = nil; return value }
        let document = isDocument(item.item)
        if previousGroup != group || previousDocument != document { runGroup = Int64.random(in: Int64.min ... Int64.max) }
        previousGroup = group
        previousDocument = document
        let result = dictionary.mutableCopy() as! NSMutableDictionary
        result["item"] = LegacyAssetItemWrapper(item: item.item, timer: item.timer, spoiler: item.spoiler, price: item.price, forceHd: item.forceHd, groupedId: runGroup, uniqueId: item.uniqueId)
        return result
    })
}

private func nagramiXOriginalVideoPickerValues(account: Account, signals: [Any], enabled: Bool) -> Signal<NSArray, Void> {
    let values = Signal<NSArray, Void> { subscriber in
        let disposable = SSignal.combineSignals(signals).start(next: { value in
            guard let value = value as? NSArray else { subscriber.putError(Void()); return }
            subscriber.putNext(value)
        }, error: { _ in subscriber.putError(Void()) }, completed: { subscriber.putCompletion() })
        return ActionDisposable { disposable?.dispose() }
    }
    guard enabled else { return values }
    return values |> take(1) |> mapToSignal { values -> Signal<NSArray, Void> in
        guard values.count > 0 else { return .single(values) }
        return combineLatest(values.map { nagramiXPrepareOriginalVideoValue(account: account, value: $0) })
        |> map { values -> NSArray in nagramiXOriginalVideoGroupedValues(values) }
    }
}
