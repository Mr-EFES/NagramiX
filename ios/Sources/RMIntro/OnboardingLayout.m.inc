- (void)updateLayout {
    if (!_loadedView || _pageScrollView == nil) {
        return;
    }
    CGSize size = self.view.bounds.size;
    if (size.width <= 0.0 || size.height <= 0.0) {
        return;
    }
    UIEdgeInsets safe = self.view.safeAreaInsets;
    CGFloat width = size.width;
    CGFloat top = MAX(safe.top, 20.0) + 12.0;
    CGFloat buttonWidth = MIN(430.0, width - 48.0);
    CGFloat languageHeight = _alternativeLanguageButton.isHidden ? 0.0 : MAX(32.0, _alternativeLanguageButton.bounds.size.height);
    CGFloat buttonY = size.height - MAX(safe.bottom, 12.0) - 20.0 - 50.0 - (languageHeight > 0.0 ? languageHeight + 8.0 : 0.0);
    UIView *button = self.createStartButton(buttonWidth);
    if (button != nil) {
        _startButton = button;
        if (button.superview != self.view) {
            [self.view addSubview:button];
        }
        button.frame = CGRectMake(floor((width - buttonWidth) / 2.0), buttonY, buttonWidth, 50.0);
    }
    _alternativeLanguageButton.frame = CGRectMake(24.0, buttonY + 58.0, width - 48.0, languageHeight);
    UIScrollView *body = (UIScrollView *)_wrapperView;
    body.frame = CGRectMake(0.0, top, width, MAX(0.0, buttonY - top - 24.0));
    body.contentInsetAdjustmentBehavior = UIScrollViewContentInsetAdjustmentNever;
    body.showsVerticalScrollIndicator = NO;
    body.alwaysBounceVertical = NO;
    body.directionalLockEnabled = YES;
    if (_nagramiXArtworkView != nil && _nagramiXArtworkView.superview != body) {
        [body insertSubview:_nagramiXArtworkView atIndex:0];
    }
    CGFloat referenceScale = MIN(1.3, MAX(0.9, width / 360.0));
    CGFloat extraHeight = MAX(0.0, size.height - 640.0 * referenceScale);
    CGFloat artworkSide = MIN(360.0, width * 0.82);
    CGFloat artworkY = MAX(0.0, 42.0 * referenceScale + extraHeight * 0.50 - top);
    CGFloat textWidth = MAX(1.0, MIN(540.0, width - 40.0));
    UIFont *bodyFont = [[UIFontMetrics metricsForTextStyle:UIFontTextStyleBody] scaledFontForFont:[UIFont systemFontOfSize:MAX(15.0, 15.0 * referenceScale)]];
    CGFloat contentHeight = 0.0;
    CGFloat selectedTextBottom = 0.0;
    NSInteger pageIndex = 0;
    for (RMIntroPageView *page in _pageViews) {
        NSInteger index = pageIndex++;
        page.frame = CGRectMake(index * width, 0.0, width, page.bounds.size.height);
        UIFont *headlineFont = [[UIFontMetrics metricsForTextStyle:UIFontTextStyleLargeTitle] scaledFontForFont:[UIFont boldSystemFontOfSize:35.0 * referenceScale]];
        UILabel *title = page.headerLabel;
        UILabel *description = page.descriptionLabel;
        title.font = headlineFont;
        title.numberOfLines = 0;
        title.lineBreakMode = NSLineBreakByWordWrapping;
        title.adjustsFontForContentSizeCategory = YES;
        title.accessibilityTraits = UIAccessibilityTraitHeader;
        description.font = bodyFont;
        description.numberOfLines = 0;
        description.adjustsFontForContentSizeCategory = YES;
        CGFloat titleHeight = ceil([title sizeThatFits:CGSizeMake(textWidth, CGFLOAT_MAX)].height);
        CGFloat descriptionHeight = ceil([description sizeThatFits:CGSizeMake(textWidth, CGFLOAT_MAX)].height);
        CGFloat preferredTextY = 358.0 * referenceScale + extraHeight * 0.50 - top;
        CGFloat artBottom = artworkY + artworkSide * 0.90;
        CGFloat textY = MAX(preferredTextY, artBottom + 20.0);
        title.frame = CGRectMake((width - textWidth) / 2.0, textY, textWidth, titleHeight);
        description.frame = CGRectMake((width - textWidth) / 2.0, textY + titleHeight + 12.0 * referenceScale, textWidth, descriptionHeight);
        CGFloat textBottom = CGRectGetMaxY(description.frame);
        contentHeight = MAX(contentHeight, textBottom + 24.0 + 24.0);
        if (index == _currentPage) {
            selectedTextBottom = textBottom;
        }
        page.opaque = NO;
    }
    // Keep the reference hierarchy without clipping at large text sizes.
    // The fixed CTA and vertically scrolling body remain separate.
    _nagramiXArtworkView.frame = CGRectMake((width - artworkSide) / 2.0, artworkY, artworkSide, artworkSide);
    [self nagramiXLayoutArtwork];
    BOOL scrolling = _pageScrollView.isDragging || _pageScrollView.isDecelerating;
    CGFloat previousWidth = _pageScrollView.bounds.size.width;
    CGFloat progress = previousWidth > 0.0 ? _pageScrollView.contentOffset.x / previousWidth : _currentPage;
    _pageScrollView.frame = CGRectMake(0.0, 0.0, width, contentHeight);
    _pageScrollView.directionalLockEnabled = YES;
    _pageScrollView.alwaysBounceVertical = NO;
    _pageScrollView.opaque = NO;
    _pageScrollView.contentSize = CGSizeMake(_headlines.count * width, contentHeight);
    if (!scrolling || fabs(previousWidth - width) > 0.5) {
        _pageScrollView.contentOffset = CGPointMake((scrolling ? progress : _currentPage) * width, 0.0);
    }
    [_pageViews enumerateObjectsUsingBlock:^(RMIntroPageView *page, NSUInteger index, __unused BOOL *stop) {
        page.frame = CGRectMake(index * width, 0.0, width, contentHeight);
    }];
    _pageControl.frame = CGRectMake(0.0, selectedTextBottom + 24.0, width, 24.0);
    body.contentSize = CGSizeMake(width, contentHeight);
    body.scrollEnabled = body.contentSize.height > body.bounds.size.height + 0.5;
    [self nagramiXUpdateArtwork];
}

- (void)traitCollectionDidChange:(UITraitCollection *)previousTraitCollection {
    [super traitCollectionDidChange:previousTraitCollection];
    if (![previousTraitCollection.preferredContentSizeCategory isEqual:self.traitCollection.preferredContentSizeCategory]) {
        [self.view setNeedsLayout];
    }
}
