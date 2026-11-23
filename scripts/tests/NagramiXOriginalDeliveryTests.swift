@main enum OriginalVideoDeliveryChecks {
    static func main() {
        DispatchQueue.global().async {
            do { try run(); exit(0) } catch { print("FAIL:", error); exit(96) }
        }
        dispatchMain()
    }

    static func run() throws {
        var count = 0
        func check(_ ok: Bool, _ reason: String) {
            guard ok else { print("FAIL:", reason); exit(96) }
            count += 1
        }
        func wait(_ ready: () -> Bool) {
            let deadline = Date().addingTimeInterval(5)
            while !ready() && Date() < deadline {
                PHAssetResourceManager.default().finish()
                nagramiXOriginalVideoQueue.sync {}
                Thread.sleep(forTimeInterval: 0.002)
            }
            check(ready(), "picker returned a result")
        }
        func setEnabled(_ enabled: Bool) {
            var settings = NagramiXMediaSettings.current
            settings.originalVideos = enabled
            NagramiXMediaSettings.update(settings)
        }
        let old = UserDefaults.standard.object(forKey: "nagramix.videos.original")
        defer { UserDefaults.standard.set(old, forKey: "nagramix.videos.original") }
        let mp4 = Data(base64Encoded: "H264_60_BASE64")!
        let mov = Data(base64Encoded: "HEVC_60_BASE64")!
        let folder = FileManager.default.temporaryDirectory.appendingPathComponent(UUID().uuidString)
        try FileManager.default.createDirectory(at: folder, withIntermediateDirectories: true)
        defer { try? FileManager.default.removeItem(at: folder) }

        func verify(_ file: TelegramMediaFile, account: Account, bytes: Data, document: Bool) throws {
            check(file.isVideo == !document && !file.isInstantVideo, "message representation")
            check((nativeUploadFlags(file) & (1 << 4) != 0) == document, "force_file on the wire")
            check(file.resource is LocalFileMediaResource && file.size == Int64(bytes.count), "original resource and size")
            if !document {
                let hasOriginalMetadata = file.attributes.contains { attribute in
                    guard case let .Video(duration, dimensions, _, _, _, _) = attribute else { return false }
                    return dimensions.width == 96 && dimensions.height == 64 && duration == 0.5
                }
                check(hasOriginalMetadata, "source resolution and duration on playable messages")
            }
            account.resources.flushMoves()
            let data = try Data(contentsOf: URL(fileURLWithPath: account.resources.paths[file.resource.id]!))
            check(data == bytes, "every original byte reaches the deferred upload")
        }

        for (name, bytes, mime) in [("h264.mp4", mp4, "video/mp4"), ("hevc.mov", mov, "video/quicktime")] {
            let url = folder.appendingPathComponent(name)
            let resource = PHAssetResource(name, mime: mime, bytes: bytes)
            let asset = PHAsset([PHAssetResource("rendered.mp4", mime: mime, bytes: Data([1]), full: true), resource])
            PHAsset.registry["library"] = asset
            for enabled in [false, true] {
                setEnabled(enabled)
                for camera in [false, true] {
                    for document in [false, true] {
                        try bytes.write(to: url)
                        let context = AccountContext()
                        let source: LegacyAssetVideoData = camera ? .tempFile(path: url.absoluteString, dimensions: .zero, duration: 0.1) : .asset(TGMediaAsset(asset))
                        let item = LegacyAssetItemWrapper(item: .video(data: source, thumbnail: nil, cover: nil, adjustments: nil, caption: NSAttributedString(string: "caption"), asFile: document, asAnimation: false, stickers: []), timer: 10, spoiler: true, price: nil, groupedId: 42, uniqueId: name)
                        let result = LegacyGalleryResult()
                        let d = nagramiXOriginalVideoPickerValues(account: context.account, signals: [NSDictionary(dictionary: ["item": item])], enabled: enabled).start(next: { result.next($0[0]) })
                        wait { result.value != nil }
                        let output = (result.value as! NSDictionary)["item"] as! LegacyAssetItemWrapper
                        if document || enabled {
                            guard case let .originalVideo(file, caption) = output.item else { fatalError("wrong legacy route") }
                            check(caption?.string == "caption" && output.timer == 10 && output.spoiler == true && output.groupedId == 42, "retain send metadata")
                            if camera { try FileManager.default.removeItem(at: url) }
                            try verify(file, account: context.account, bytes: bytes, document: document)
                        } else {
                            check(output === item && context.account.resources.moves.isEmpty, "stock legacy media when disabled")
                        }
                        d.dispose()
                    }
                    try bytes.write(to: url)
                    let source: ChatMediaSendItem.Source = camera ? .tempVideo(path: url.path, dimensions: PixelDimensions(width: 2, height: 3), duration: 0.5) : .libraryAsset(identifier: "library", pixelSize: .zero, isVideo: true, duration: 0.5)
                    let context = AccountContext()
                    let item = ChatMediaSendItem(uniqueId: name, source: source, options: ChatMediaSendItemOptions())
                    let result = GalleryResult()
                    let d = chatMediaSendMessages(context: context, items: [item], global: ChatMediaSendGlobalOptions(grouping: true), renderer: Renderer()).start(next: result.next)
                    wait { result.value != nil }
                    let file = result.value!.files[0]!
                    if enabled {
                        if camera { try FileManager.default.removeItem(at: url) }
                        try verify(file, account: context.account, bytes: bytes, document: false)
                        check(result.value!.global.grouping && result.value!.items[0].uniqueId == name, "retain album and order")
                    } else {
                        check(camera ? file.resource is LocalFileVideoMediaResource : file.resource is VideoLibraryMediaResource, "stock modern video converter")
                    }
                    d.dispose()
                }
                try bytes.write(to: url)
                let context = AccountContext()
                let clip = ChatMediaEditorResult(media: .video(path: url.path, values: MediaEditorValues(), duration: 0.5), thumbnail: nil, caption: NSAttributedString(string: "caption"), stickers: [])
                let semaphore = DispatchSemaphore(value: 0)
                var messages: [LegacyAssetPickerEnqueueMessage] = []
                let d = chatMediaEditorEnqueueMessages(context: context, result: clip, forceHd: true).start(next: { messages = $0 }, completed: { semaphore.signal() })
                check(semaphore.wait(timeout: .now() + 5) == .success && messages.count == 1, "direct editor completion")
                if enabled {
                    check(messages[0].caption == "caption", "editor caption")
                    try verify(messages[0].media!, account: context.account, bytes: bytes, document: false)
                } else { check(messages[0].caption == "native editor", "stock direct editor") }
                d.dispose()
            }
        }

        setEnabled(true)
        let url = folder.appendingPathComponent("capture")
        try mov.write(to: url)
        check(nagramiXCameraVideoName(url) == "video.mov", "extensionless QuickTime capture")
        for end in [0.2, 0.5] {
            let adjustment = TGVideoEditAdjustments()
            adjustment.trimEndValue = end
            let wrapper = LegacyAssetItemWrapper(item: .video(data: .tempFile(path: url.path, dimensions: .zero, duration: end), thumbnail: nil, cover: nil, adjustments: adjustment, caption: nil, asFile: false, asAnimation: false, stickers: []), timer: nil, spoiler: false, price: nil, groupedId: nil, uniqueId: nil)
            let output = LegacyGalleryResult(), context = AccountContext()
            let d = nagramiXPrepareOriginalVideoValue(account: context.account, value: NSDictionary(dictionary: ["item": wrapper]), enabled: true).start(next: output.next)
            wait { output.value != nil }
            let item = (output.value as! NSDictionary)["item"] as! LegacyAssetItemWrapper
            if end < 0.5 { check(item === wrapper, "real camera end trim uses native editor") }
            else if case let .originalVideo(file, _) = item.item { try verify(file, account: context.account, bytes: mov, document: false) }
            else { fatalError("full duration should preserve original") }
            d.dispose()
        }
        do {
            let context = AccountContext(), result = GalleryResult()
            let asset = PHAsset([PHAssetResource("cancel.mov", mime: "video/quicktime", bytes: mov)])
            PHAsset.registry["cancel"] = asset
            let clip = ChatMediaSendItem(uniqueId: "cancel", source: .libraryAsset(identifier: "cancel", pixelSize: .zero, isVideo: true, duration: 0.5), options: ChatMediaSendItemOptions())
            let manager = PHAssetResourceManager.default()
            let previous = manager.cancelled
            let d = chatMediaSendMessages(context: context, items: [clip], global: ChatMediaSendGlobalOptions(grouping: false), renderer: Renderer()).start(next: result.next)
            d.dispose()
            manager.finish()
            nagramiXOriginalVideoQueue.sync {}
            check(manager.cancelled > previous && result.value == nil && context.account.resources.moves.isEmpty, "dismissing the picker cancels an unfinished Photos export")
        }
        var values = MediaEditorValues()
        values.videoIsMuted = true
        check(!nagramiXOriginalVideoPreservesContent(values, duration: 0.5), "mute is an edit")
        values = MediaEditorValues()
        values.qualityPreset = .videoMessage
        check(!nagramiXOriginalVideoPreservesContent(values, duration: 0.5), "round video keeps its encoder")

        try FileManager.default.removeItem(at: url)
        let context = AccountContext(), result = GalleryResult()
        let missing = ChatMediaSendItem(uniqueId: "gone", source: .tempVideo(path: url.path, dimensions: PixelDimensions(), duration: 1), options: ChatMediaSendItemOptions())
        let d = chatMediaSendMessages(context: context, items: [missing], global: ChatMediaSendGlobalOptions(grouping: false), renderer: Renderer()).start(next: result.next)
        wait { result.value != nil }
        check(result.value!.files[0] == nil && context.account.resources.moves.isEmpty, "missing original cannot become a partial or compressed upload")
        d.dispose()
        print("PASS", count, "video delivery checks")
    }
}
