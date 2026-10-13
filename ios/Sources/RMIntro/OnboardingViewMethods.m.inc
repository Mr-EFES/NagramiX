- (void)loadGL {
    // Keep the native lifecycle entry point, without the old OpenGL renderer.
    if (_isOpenGLLoaded) {
        return;
    }
    BOOL isIpad = [UIDevice currentDevice].userInterfaceIdiom == UIUserInterfaceIdiomPad;
    CGFloat size = isIpad ? 240.0 : 200.0;
    CGFloat y = isIpad ? 119.0 : 50.0;
    _nagramiXArtworkView = [[UIView alloc] initWithFrame:CGRectMake((self.view.bounds.size.width - size) / 2.0, y, size, size)];
    _nagramiXArtworkView.autoresizingMask = UIViewAutoresizingFlexibleLeftMargin | UIViewAutoresizingFlexibleRightMargin;
    _nagramiXArtworkView.userInteractionEnabled = NO;
    _nagramiXArtworkView.isAccessibilityElement = NO;
    NSMutableArray<UIImageView *> *views = [[NSMutableArray alloc] initWithCapacity:6];
    for (NSInteger page = 0; page < 6; page++) {
        UIImageView *imageView = [[UIImageView alloc] initWithImage:NagramiXOnboardingImage(page)];
        imageView.frame = _nagramiXArtworkView.bounds;
        imageView.contentMode = UIViewContentModeScaleAspectFit;
        imageView.autoresizingMask = UIViewAutoresizingFlexibleWidth | UIViewAutoresizingFlexibleHeight;
        imageView.isAccessibilityElement = NO;
        [_nagramiXArtworkView addSubview:imageView];
        [views addObject:imageView];
    }
    _nagramiXArtworkImages = [views copy];
    [self.view addSubview:_nagramiXArtworkView];
    [self.view sendSubviewToBack:_nagramiXArtworkView];
    _isOpenGLLoaded = YES;
    [self nagramiXUpdateArtwork];
    [self.view setNeedsLayout];
}

- (void)freeGL {
    [_nagramiXArtworkView removeFromSuperview];
    _nagramiXArtworkView = nil;
    _nagramiXArtworkImages = nil;
    _isOpenGLLoaded = NO;
}

- (void)nagramiXUpdateArtwork {
    CGFloat width = _pageScrollView.bounds.size.width;
    CGFloat progress = width > 0.0 ? _pageScrollView.contentOffset.x / width : (CGFloat)_currentPage;
    progress = MAX(0.0, MIN(5.0, progress));
    BOOL reduceMotion = UIAccessibilityIsReduceMotionEnabled();
    for (NSInteger page = 0; page < (NSInteger)_nagramiXArtworkImages.count; page++) {
        UIImageView *imageView = _nagramiXArtworkImages[page];
        CGFloat distance = (CGFloat)page - progress;
        CGFloat alpha = reduceMotion ? (page == (NSInteger)floor(progress + 0.5) ? 1.0 : 0.0) : MAX(0.0, 1.0 - fabs(distance));
        imageView.alpha = alpha;
        if (reduceMotion || alpha == 0.0) {
            imageView.transform = CGAffineTransformIdentity;
        } else {
            CGFloat scale = 0.94 + 0.06 * alpha;
            imageView.transform = CGAffineTransformScale(CGAffineTransformMakeTranslation(distance * 18.0, 0.0), scale, scale);
        }
    }
}
