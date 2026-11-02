import Foundation

final class SaveProbe {
    private let lock = NSLock(); private var values: [Float] = []; private var errors: [NagramiXGalleryVideoSaveError] = []; private var done = false
    func next(_ value: Float) { lock.lock(); values.append(value); lock.unlock() }
    func error(_ error: NagramiXGalleryVideoSaveError) { lock.lock(); errors.append(error); done = true; lock.unlock() }
    func complete() { lock.lock(); done = true; lock.unlock() }
    var finished: Bool { lock.lock(); defer { lock.unlock() }; return done }
    var progress: [Float] { lock.lock(); defer { lock.unlock() }; return values }
    var errorValues: [NagramiXGalleryVideoSaveError] { lock.lock(); defer { lock.unlock() }; return errors }
}
@main struct VideoQualitySaveTests {
    static func wait(_ predicate: () -> Bool) async throws {
        for _ in 0..<500 { if predicate() { return }; try await Task.sleep(nanoseconds: 2_000_000) }
        preconditionFailure("async operation timed out")
    }
    static func main() async throws {
        var count = 0
        func check(_ value: @autoclosure () -> Bool, _ label: String) { precondition(value(), label); count += 1 }
        let folder = URL(fileURLWithPath: NSTemporaryDirectory()).appendingPathComponent(UUID().uuidString)
        try FileManager.default.createDirectory(at: folder, withIntermediateDirectories: true)
        defer { try? FileManager.default.removeItem(at: folder) }
        var identity = 0
        func file(_ movie: Movie = Movie(), codec: String = "h264") throws -> FileMediaReference {
            identity += 1; let url = folder.appendingPathComponent("source-\(identity).mp4"); try JSONEncoder().encode(movie).write(to: url)
            return FileMediaReference(media: TelegramMediaFile(fileId: identity, resource: MediaResource(id: ResourceId(value: identity), path: url.path), attributes: [.Video(movie.duration, PixelDimensions(width: Int32(movie.width), height: Int32(movie.height)), 0, nil, nil, codec)]))
        }
        let original = try file()
        for quality in [1080,720,480] { for (width,height) in [(1920.0,1080.0),(1080.0,1920.0),(1920.0,1920.0)] {
            let target = NagramiXVideoSavePolicy.targetSize(width: width, height: height, quality: quality)!
            check(min(target.width,target.height) == quality && target.width % 2 == 0 && target.height % 2 == 0, "requested shorter edge for landscape/portrait/square")
            check(target.width <= Int(width) && target.height <= Int(height), "no upscaling")
        } }
        for dimensions in [(Double.nan,1080.0),(Double.infinity,1080),(0,1080),(1920,1)] {
            check(NagramiXVideoSavePolicy.targetSize(width: dimensions.0, height: dimensions.1, quality: 720) == nil, "invalid source size rejected")
        }
        check(NagramiXVideoSavePolicy.codecPriority("AV1") == nil && NagramiXVideoSavePolicy.codecPriority("av01") == nil, "software playback AV1 is not selected for direct Photos export")
        check(NagramiXVideoSavePolicy.codecPriority("h264")! < NagramiXVideoSavePolicy.codecPriority("hevc")!, "prefer AVC then HEVC")
        let av1 = try file(Movie(width:1280,height:720),codec:"av1"), avc = try file(Movie(width:1280,height:720)), hevc = try file(Movie(width:1280,height:720),codec:"hevc")
        let base = original.withMedia(TelegramMediaFile(fileId: original.media.fileId, resource: original.media.resource, alternativeRepresentations: [av1.media,hevc.media,avc.media]))
        check(nagramiXVideoSaveSource(original: base, quality: 720).media.fileId == avc.media.fileId, "save selector chooses AVC even when playback selected AV1")
        check(nagramiXVideoSaveSource(original: base, quality: 480).media.fileId == base.media.fileId, "missing compatible quality uses original for conversion")
        check(NagramiXVideoSavePolicy.mayRetryFromOriginal(.download) && NagramiXVideoSavePolicy.mayRetryFromOriginal(.conversion), "fallback only for preparation failures")
        check(!NagramiXVideoSavePolicy.mayRetryFromOriginal(.permissionDenied) && !NagramiXVideoSavePolicy.mayRetryFromOriginal(.library), "no retry or duplicate write after Photos/permission failure")
        for quality in [1080,720,480] {
            let photos = PHPhotoLibrary.shared(); photos.reset(); DeviceAccess.allowed = true
            let context = AccountContext(), probe = SaveProbe()
            let operation = nagramiXSaveGalleryVideoQuality(context: context, userLocation: MediaResourceUserLocation(), source: original, original: original, quality: quality).start(next: probe.next, error: probe.error, completed: probe.complete)
            try await wait { probe.finished }
            check(probe.errorValues.isEmpty && probe.progress.last == 1, "selected quality completes after confirmed Photos save")
            let expectedWidth = Int(floor(Double(quality) * 16.0 / 9.0 / 2.0)) * 2
            check(photos.imported.count == 1 && Int(photos.imported[0].height) == quality && Int(photos.imported[0].width) == expectedWidth, "actual adapter passes requested MP4 dimensions to Photos")
            check(photos.imported[0].audio && photos.imported[0].duration == 3, "audio and duration survive native export configuration")
            check(zip(probe.progress,probe.progress.dropFirst()).allSatisfy { $0 <= $1 }, "visible progress stays monotonic")
            operation.dispose(); try await wait { EngineTempBox.shared.active.isEmpty && context.account.postbox.mediaBox.keeps == 0 }
            check(FileManager.default.fileExists(atPath: original.media.resource.path), "original cache bytes remain untouched")
        }
        for movie in [Movie(width:1920,height:1080,rotation:true), Movie(width:1080,height:1920), Movie(width:1080,height:1080)] {
            PHPhotoLibrary.shared().reset(); let source = try file(movie); let context = AccountContext(), probe = SaveProbe()
            let op = nagramiXSaveGalleryVideoQuality(context: context, userLocation: MediaResourceUserLocation(), source: source, original: source, quality: 480).start(next: probe.next,error:probe.error,completed:probe.complete)
            try await wait { probe.finished }
            let saved = PHPhotoLibrary.shared().imported[0]
            check(probe.errorValues.isEmpty && min(saved.width,saved.height) == 480, "portrait/rotated/square exported at correct shorter edge")
            if movie.rotation || movie.height > movie.width { check(saved.height > saved.width, "display orientation preserved") }
            op.dispose()
        }
        check(TestExports.transformsFit, "rotation translation and scale fill the target canvas without cropping")
        PHPhotoLibrary.shared().reset()
        let fragmented = try file(Movie(failPassthrough:true)); let context = AccountContext(), remuxProbe = SaveProbe()
        let remux = nagramiXSaveGalleryVideoQuality(context:context,userLocation:MediaResourceUserLocation(),source:fragmented,original:fragmented,quality:1080).start(next:remuxProbe.next,error:remuxProbe.error,completed:remuxProbe.complete)
        try await wait { remuxProbe.finished }
        check(remuxProbe.errorValues.isEmpty && PHPhotoLibrary.shared().imported.count == 1, "failed passthrough retries compatible encoding before Photos")
        remux.dispose()
        PHPhotoLibrary.shared().reset()
        let broken = try file(Movie(width:1280,height:720,unreadable:true)); let fallbackContext = AccountContext(), fallbackProbe = SaveProbe()
        let fallback = nagramiXSaveGalleryVideoQuality(context:fallbackContext,userLocation:MediaResourceUserLocation(),source:broken,original:original,quality:720).start(next:fallbackProbe.next,error:fallbackProbe.error,completed:fallbackProbe.complete)
        try await wait { fallbackProbe.finished }
        check(fallbackProbe.errorValues.isEmpty && fallbackContext.account.postbox.mediaBox.reads == [broken.media.fileId,original.media.fileId], "unreadable variant fetches original once and converts to same requested quality")
        check(PHPhotoLibrary.shared().imported.count == 1 && PHPhotoLibrary.shared().imported[0].height == 720, "fallback does not import the original at wrong resolution")
        fallback.dispose()
        for (permission,library) in [(false,true),(true,false)] {
            let photos = PHPhotoLibrary.shared(); photos.reset(); photos.success = library; DeviceAccess.allowed = permission
            let c = AccountContext(), p = SaveProbe()
            let op = nagramiXSaveGalleryVideoQuality(context:c,userLocation:MediaResourceUserLocation(),source:avc,original:original,quality:720).start(next:p.next,error:p.error,completed:p.complete)
            try await wait { p.finished }
            check(p.errorValues.count == 1 && p.progress.last != 1, "denial and Photos error never announce saved")
            check(c.account.postbox.mediaBox.reads == [avc.media.fileId], "Photos error does not trigger another conversion/write")
            op.dispose()
        }
        DeviceAccess.allowed = true; PHPhotoLibrary.shared().reset(); PHPhotoLibrary.shared().hold = true
        let cancelContext = AccountContext(), cancelProbe = SaveProbe()
        let cancel = nagramiXSaveGalleryVideoQuality(context:cancelContext,userLocation:MediaResourceUserLocation(),source:original,original:original,quality:720).start(next:cancelProbe.next,error:cancelProbe.error,completed:cancelProbe.complete)
        try await wait { PHPhotoLibrary.shared().hasPending }
        let pendingPath = PHPhotoLibrary.shared().latestURL!.path; cancel.dispose()
        check(FileManager.default.fileExists(atPath: pendingPath), "cancel never deletes a file while Photos reads it")
        PHPhotoLibrary.shared().release(); try await wait { EngineTempBox.shared.active.isEmpty }
        check(!cancelProbe.finished && cancelProbe.progress.last != 1, "late Photos completion after cancel cannot show saved")
        check(cancelContext.account.postbox.mediaBox.keeps == 0, "cancel releases cache keep leases")
        print("PASS: \(count) actual selector/geometry/export/fallback/Photos/cancellation/lifetime checks")
    }
}
