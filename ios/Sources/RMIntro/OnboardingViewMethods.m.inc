- (void)loadGL {
    if (_isOpenGLLoaded) {
        return;
    }
    CGFloat side = [UIDevice currentDevice].userInterfaceIdiom == UIUserInterfaceIdiomPad ? 240.0 : 200.0;
    _nagramiXArtworkView = [[UIView alloc] initWithFrame:CGRectMake((self.view.bounds.size.width - side) / 2.0, 0.0, side, side)];
    _nagramiXArtworkView.autoresizingMask = UIViewAutoresizingFlexibleLeftMargin | UIViewAutoresizingFlexibleRightMargin;
    _nagramiXArtworkView.userInteractionEnabled = NO;
    _nagramiXArtworkView.isAccessibilityElement = NO;
    _nagramiXArtworkView.accessibilityElementsHidden = YES;
    // The logo stays fixed while native headlines/descriptions page beneath it.
    // One UIImageView means no scene swaps, cross-fades or size changes.
    UIImageView *logo = [[UIImageView alloc] initWithImage:NagramiXOnboardingImage(0)];
    logo.contentMode = UIViewContentModeScaleAspectFit;
    [_nagramiXArtworkView addSubview:logo];
    _nagramiXArtworkImages = @[logo];
    [self.view addSubview:_nagramiXArtworkView];
    _isOpenGLLoaded = YES;
    [self nagramiXLayoutArtwork];
    [self nagramiXUpdateArtwork];
    [self.view setNeedsLayout];
}

- (void)nagramiXLayoutArtwork {
    for (UIView *page in _nagramiXArtworkImages) {
        page.frame = _nagramiXArtworkView.bounds;
    }
}

- (void)freeGL {
    [_nagramiXArtworkView removeFromSuperview];
    _nagramiXArtworkView = nil;
    _nagramiXArtworkImages = nil;
    _isOpenGLLoaded = NO;
}

- (void)nagramiXUpdateArtwork {
    // A single image is shared by every native welcome page. Paging updates
    // only the native dots/text; do not relayout or snap an in-flight swipe.
}
