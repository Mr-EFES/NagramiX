// Legacy ObjC model boundary. Native header/getter are pinned, the new Swift decision is verbatim.
private struct FileMediaReference {}
private enum LegacyAssetImageData {case fixture}
private final class TGMediaAsset {let backingAsset:PHAsset?;init(_ value:PHAsset){backingAsset=value}}
private final class TGVideoEditAdjustments {
 var trimStartValue:Double=0,trimEndValue:Double=0
 var cropOrientation:MediaCropOrientation = .up
 var cropMirrored=false,cropRotation:Double=0,sendAsGif=false,bounce=false
 func cropApplied(forAvatar:Bool)->Bool{false}
 func trimApplied()->Bool{trimStartValue>Double.ulpOfOne || trimEndValue>Double.ulpOfOne}
 func toolsApplied()->Bool{false}
 func hasPainting()->Bool{false}
}
private final class LegacyGalleryResult {
 private let lock=NSLock();private var stored:Any?
 func next(_ value:Any){lock.lock();stored=value;lock.unlock()}
 var value:Any?{lock.lock();defer{lock.unlock()};return stored}
}
