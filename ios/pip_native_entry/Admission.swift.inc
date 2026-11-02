    private var nagramiXPiPCurrentGallery: GalleryControllerNode? {
        guard let gallery = self.galleryController()?.displayNode as? GalleryControllerNode,
              gallery.pager.centralItemNode() === self,
              gallery.nagramiXAllowsSystemPiPTransition else { return nil }
        return gallery
    }

    private var nagramiXPiPUnavailableReason: String? {
        guard self.nagramiXPiPCurrentGallery != nil else { return "not_current_gallery" }
        guard self.hasPictureInPicture, !self.isLivePhoto, let item = self.item else { return "unsupported_content" }
        guard !item.isSecret else { return "secret_content" }
        guard self.videoNode != nil else { return "missing_video_node" }
        guard self.galleryController()?.view.windowHost != nil else { return "missing_window_host" }
        guard AVPictureInPictureController.isPictureInPictureSupported() else { return "unsupported_device" }
        if let data = self.context.currentAppConfiguration.with({ $0 }).data,
           data["ios_killswitch_disable_native_pip_v2"] != nil { return "server_disabled" }
        if case let .message(message, _) = item.contentInfo, message.adAttribute != nil { return "advertisement" }
        if let content = item.content as? NativeVideoContent, content.fileReference.media.isAnimated { return "animated_content" }
        if let content = item.content as? HLSVideoContent, content.fileReference.media.isAnimated { return "animated_content" }
        return nil
    }

    private var nagramiXCanUseSystemPiP: Bool { return self.nagramiXPiPUnavailableReason == nil }
