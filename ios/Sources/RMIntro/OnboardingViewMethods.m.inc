- (void)loadGL {
    if (_isOpenGLLoaded) {
        return;
    }
    _nagramiXArtworkView = [[UIView alloc] initWithFrame:CGRectMake(0, 0, 200, 200)];
    _nagramiXArtworkView.userInteractionEnabled = NO;
    _nagramiXArtworkView.isAccessibilityElement = NO;
    _nagramiXArtworkView.accessibilityElementsHidden = YES;
    NSMutableArray<UIView *> *pages = [[NSMutableArray alloc] initWithCapacity:6];
    for (NSInteger page = 0; page < 6; page++) {
        UIView *container = [[UIView alloc] initWithFrame:_nagramiXArtworkView.bounds];
        container.autoresizingMask = UIViewAutoresizingFlexibleWidth | UIViewAutoresizingFlexibleHeight;
        UIImageView *main = [[UIImageView alloc] initWithImage:NagramiXOnboardingImage(page)];
        main.contentMode = UIViewContentModeScaleAspectFit;
        main.tag = 100;
        [container addSubview:main];
        [_nagramiXArtworkView addSubview:container];
        [pages addObject:container];
    }
    _nagramiXArtworkImages = [pages copy];
    [self.view addSubview:_nagramiXArtworkView];
    _isOpenGLLoaded = YES;
    [self nagramiXLayoutArtwork];
    [self nagramiXUpdateArtwork];
    [self.view setNeedsLayout];
}

- (void)nagramiXLayoutArtwork {
    CGFloat side = _nagramiXArtworkView.bounds.size.width;
    for (UIView *page in _nagramiXArtworkImages) {
        page.frame = _nagramiXArtworkView.bounds;
        UIView *main = [page viewWithTag:100];
        main.frame = CGRectInset(page.bounds, side * 0.02, side * 0.02);
    }
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
    // Only one composition is visible: neither a swipe nor Reduce Motion
    // can superimpose two logos. All decoration belongs to a single image.
    NSInteger visiblePage = (NSInteger)floor(progress + 0.5);
    if (_nagramiXArtworkView.tag != visiblePage) {
        _nagramiXArtworkView.tag = visiblePage;
        [self.view setNeedsLayout];
    }
    for (NSInteger page = 0; page < (NSInteger)_nagramiXArtworkImages.count; page++) {
        UIView *container = _nagramiXArtworkImages[page];
        container.alpha = page == visiblePage ? 1.0 : 0.0;
        container.transform = CGAffineTransformIdentity;
    }
}
