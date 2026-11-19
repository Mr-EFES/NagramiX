func exerciseRepeatedEntry() {
    for embedded in [false, true] {
        let gallery = GalleryLifecycleBoundary()
        let node = gallery.videoNode!
        gallery.item!.embedded = embedded
        gallery.validLayout = nil
        node.ownsContentNode = false
        node.view.window = nil
        gallery.pictureInPictureButtonPressed()
        advance(0.05)
        precondition(gallery.nagramiXPiPVisualState.phase == .waiting)
        node.ownsContentNode = true
        gallery.validLayout = 1
        advance(0.05)
        precondition(gallery.nagramiXPiPVisualState.phase == .waiting)
        node.view.window = NSObject()
        node.accepts = false
        advance(0.05)
        if embedded {
            precondition(node.enters == 1 && gallery.nagramiXPiPVisualState.phase == .starting)
            node.accepts = true
            advance(0.05)
            let accepted = node.enters
            advance(0.05)
            precondition(accepted == 2 && node.enters == accepted)
        }
        finish(gallery)
        precondition(gallery.nagramiXPiPVisualState.phase == .active)
        stop(gallery)
        precondition(gallery.nagramiXPiPVisualState.phase == .idle)
        precondition(gallery.controller!.galleryNode.nagramiXNativePictureInPictureDistance == nil)
    }

    let native = GalleryLifecycleBoundary()
    native.pictureInPictureButtonPressed()
    finish(native)
    let web = GalleryLifecycleBoundary()
    web.context = native.context
    web.item!.embedded = true
    web.pictureInPictureButtonPressed()
    advance(0.05)
    precondition(web.videoNode!.enters == 0 && native.nagramiXPiPVisualState.phase == .active)
    stop(native)
    advance(0.05)
    precondition(web.videoNode!.enters == 1)
    finish(web)
    stop(web)
    native.pictureInPictureButtonPressed()
    finish(native)
    stop(native)

    let gallery = GalleryLifecycleBoundary()
    gallery.pictureInPictureButtonPressed()
    let old = gallery.nativePictureInPictureContent as! NativePictureInPictureContentImpl
    old.finish()
    old.isActive = false  // AVKit ended before the gallery received DidStop.
    gallery.pictureInPictureButtonPressed()
    let next = gallery.nativePictureInPictureContent as! NativePictureInPictureContentImpl
    precondition(next !== old && next.starts == 1)
    old.stop()
    next.finish()
    precondition(gallery.nagramiXPiPVisualState.phase == .active)
    stop(gallery)
}
