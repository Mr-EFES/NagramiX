#import "RMIntroViewController.h"

UIColor *NagramiXOnboardingBackground(UIColor *nativeColor) {
    CGFloat red = 0.0, green = 0.0, blue = 0.0, alpha = 1.0;
    UIColor *resolved = [nativeColor resolvedColorWithTraitCollection:UITraitCollection.currentTraitCollection];
    if ([resolved getRed:&red green:&green blue:&blue alpha:&alpha] && red * 0.2126 + green * 0.7152 + blue * 0.0722 < 0.35) {
        return [UIColor colorWithRed:8.0 / 255.0 green:25.0 / 255.0 blue:46.0 / 255.0 alpha:1.0];
    }
    return nativeColor;
}

UIImage *NagramiXOnboardingSymbol(NSInteger index) {
    if (index < 0 || index >= 6) {
        return nil;
    }
    static NSArray *images;
    static dispatch_once_t onceToken;
    dispatch_once(&onceToken, ^{
        UIImage *atlas = [UIImage imageNamed:@"NagramiXOnboardingAtlas" inBundle:[NSBundle mainBundle] compatibleWithTraitCollection:nil];
        NSMutableArray *result = [[NSMutableArray alloc] initWithCapacity:6];
        for (NSInteger item = 0; item < 6; item++) {
            UIImage *image = nil;
            if (atlas.CGImage != NULL) {
                size_t width = CGImageGetWidth(atlas.CGImage);
                size_t height = CGImageGetHeight(atlas.CGImage);
                if (width % 3 == 0 && height % 2 == 0) {
                    CGRect rect = CGRectMake((item % 3) * (width / 3), (item / 3) * (height / 2), width / 3, height / 2);
                    CGImageRef cropped = CGImageCreateWithImageInRect(atlas.CGImage, rect);
                    if (cropped != NULL) {
                        image = [UIImage imageWithCGImage:cropped scale:2.0 orientation:UIImageOrientationUp];
                        CGImageRelease(cropped);
                    }
                }
            }
            [result addObject:image ?: (id)[NSNull null]];
        }
        images = [result copy];
    });
    id image = images[index];
    return [image isKindOfClass:[UIImage class]] ? image : nil;
}

UIImage *NagramiXOnboardingImage(NSInteger index) {
    if (index < 0 || index > 6) {
        return nil;
    }
    if (index == 0 || index == 6) {
        NSString *name = index == 0 ? @"NagramiXOnboardingLogo" : @"NagramiXOnboardingPhone";
        return [UIImage imageNamed:name inBundle:[NSBundle mainBundle] compatibleWithTraitCollection:nil];
    }
    return NagramiXOnboardingSymbol(index - 1);
}
