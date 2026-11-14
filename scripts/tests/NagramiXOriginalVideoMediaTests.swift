@main struct OriginalVideoMediaTests {
    static func main() throws {
        var checks = 0
        func check(_ value: @autoclosure () -> Bool, _ reason: String) {
            if !value() { print("FAIL: " + reason); exit(96) }; checks += 1
        }
        let defaults = UserDefaults.standard
        let key = "nagramix.videos.original"
        let old = defaults.dictionaryRepresentation().filter { $0.key.hasPrefix("nagramix.") }
        defer {
            for k in defaults.dictionaryRepresentation().keys where k.hasPrefix("nagramix.") { defaults.removeObject(forKey: k) }
            for (k, v) in old { defaults.set(v, forKey: k) }
            _ = defaults.synchronize()
        }
        defaults.removeObject(forKey: key)
        check(!NagramiXMediaSettings.default.originalVideos, "fresh default is native compression OFF")
        check(!NagramiXMediaSettings(photoQuality: 80, sendLargePhotos: false, stickerSize: 90, showStickerTime: true).originalVideos, "legacy initializer also defaults OFF")
        check(!NagramiXMediaSettings.current.originalVideos, "absent persisted key uses OFF")
        for enabled in [true, false, true] {
            var settings = NagramiXMediaSettings.current
            settings.originalVideos = enabled
            NagramiXMediaSettings.update(settings)
            _ = defaults.synchronize()
            check(NagramiXMediaSettings.current.originalVideos == enabled, "saved explicit ON/OFF survives current reload")
        }
        let mp4 = Data(base64Encoded: "SYNTHETIC_MP4_BASE64")!
        let mov = Data(base64Encoded: "SYNTHETIC_MOV_BASE64")!
        // Same valid movie used under the native M4V fallback MIME reproduces
        // the whitelist error independently of the filename/UTI adapter.
        let cases: [(String, String, Data, Bool)] = [
            ("video.mp4", "video/mp4", mp4, true), ("video.mov", "video/quicktime", mov, false),
            ("video.m4v", "video/m4v", mp4, true), ("video.m4v", "video/x-m4v", mp4, true),
            ("video.m4v", "unknown", mp4, true), ("../../original.MOV", "VIDEO/QUICKTIME", mov, false),
        ]
        for (name, mime, bytes, streamable) in cases {
            for fullSize in [false, true] {
                let resource = PHAssetResource(name, mime: mime, bytes: bytes, full: fullSize)
                let asset = PHAsset(fullSize ? [PHAssetResource("fallback.mp4", mime: "video/mp4", bytes: mov), resource] : [resource])
                let account = Account(), outcome = ExportResult()
                let disposable = nagramiXOriginalVideoFile(account: account, asset: asset, thumbnail: UIImage(), cover: UIImage()).start(next: outcome.next, error: { _ in outcome.error() }, completed: outcome.done)
                PHAssetResourceManager.default().finish()
                check(outcome.completed.wait(timeout: .now() + 5) == .success, "original export completes")
                nagramiXOriginalVideoQueue.sync {}
                check(!outcome.hasError && outcome.value != nil, "valid source exports original media")
                let file = outcome.value!
                check(file.isVideo, "every Photos video retains native Video classification")
                check(!file.isInstantVideo, "ordinary original never becomes a video circle")
                check(nativeUploadFlags(file) & (1 << 4) == 0, "native upload never forces an original video into document mode")
                check(file.size == Int64(bytes.count) && file.resource.size == file.size, "resource and media sizes describe complete original")
                check(file.mimeType == (mime == "unknown" ? "video/m4v" : mime), "real MIME is preserved without fake MP4")
                check(file.previewRepresentations.count == 1 && file.videoCover != nil, "native thumbnail and selected cover survive")
                check(file.attributes.contains { if case let .FileName(value) = $0 { return value == (name as NSString).lastPathComponent }; return false }, "safe original filename is preserved")
                for attribute in file.attributes {
                    if case let .Video(duration, size, flags, preload, cover, codec) = attribute {
                        check(duration == asset.duration && size.width == 96 && size.height == 64, "native video dimensions/duration survive")
                        check(flags.contains(.supportsStreaming) == streamable, "fast-start is reported truthfully without rewriting movie")
                        check(preload == nil && cover == nil && codec == nil, "native metadata fields stay ordinary")
                    }
                }
                check(account.resources.moves.count == 1, "exactly one full resource is queued for native MediaBox")
                let pinned = account.resources.moves[0].1
                check((try? Data(contentsOf: URL(fileURLWithPath: pinned))) == bytes, "pinned source bytes are unchanged after Photos temp disposal")
                account.resources.flushMoves()
                let delivered = account.resources.paths[file.resource.id]!
                check((try? Data(contentsOf: URL(fileURLWithPath: delivered))) == bytes, "deferred native media move preserves every source byte")
                disposable.dispose()
                check((try? Data(contentsOf: URL(fileURLWithPath: delivered))) == bytes, "post-send cancellation does not erase delivered bytes")
            }
        }
        do {
            let account = Account(), outcome = ExportResult(), asset = PHAsset([PHAssetResource("cancel.m4v", mime: "video/m4v", bytes: mp4)])
            let d = nagramiXOriginalVideoFile(account: account, asset: asset, thumbnail: UIImage(), cover: nil).start(next: outcome.next, error: { _ in outcome.error() }, completed: outcome.done)
            d.dispose(); PHAssetResourceManager.default().finish(); nagramiXOriginalVideoQueue.sync {}
            check(outcome.value == nil && account.resources.moves.isEmpty, "cancelled Photos export never uploads partial media")
        }
        for nonVideo in [false, true] {
            let account = Account(), outcome = ExportResult(), asset = PHAsset([PHAssetResource("bad.mp4", mime: "video/mp4", bytes: Data())])
            if nonVideo { asset.mediaType = .image }
            let d = nagramiXOriginalVideoFile(account: account, asset: asset, thumbnail: UIImage(), cover: nil).start(next: outcome.next, error: { _ in outcome.error() }, completed: outcome.done)
            PHAssetResourceManager.default().finish()
            check(outcome.completed.wait(timeout: .now() + 5) == .success, "invalid original has a terminal error")
            nagramiXOriginalVideoQueue.sync {}
            check(outcome.hasError && outcome.value == nil && account.resources.moves.isEmpty, "non-video/empty resource never becomes fake video")
            d.dispose()
        }
        print("PASS \(checks) real-byte export/default/native media checks; Photos, UIKit and MediaBox edges explicit")
    }
}
