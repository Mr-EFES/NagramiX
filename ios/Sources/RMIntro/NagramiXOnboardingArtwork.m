#import "RMIntroViewController.h"

UIColor *NagramiXOnboardingBackground(UIColor *nativeColor) {
    CGFloat red = 0.0, green = 0.0, blue = 0.0, alpha = 1.0;
    UIColor *resolved = [nativeColor resolvedColorWithTraitCollection:UITraitCollection.currentTraitCollection];
    if ([resolved getRed:&red green:&green blue:&blue alpha:&alpha] && red * 0.2126 + green * 0.7152 + blue * 0.0722 < 0.35) {
        return [UIColor colorWithRed:8.0 / 255.0 green:25.0 / 255.0 blue:46.0 / 255.0 alpha:1.0];
    }
    return nativeColor;
}

// Each page owns a complete, equally padded image. No runtime sprite cuts:
// the selected source sheet has unequal gutters and is not a uniform 3×2 grid.
UIImage *NagramiXOnboardingImage(NSInteger index) {
    if (index < 0 || index >= 7) {
        return nil;
    }
    static NSArray *images;
    static dispatch_once_t onceToken;
    dispatch_once(&onceToken, ^{
        NSArray<NSString *> *names = @[
            @"NagramiXOnboardingLogo", @"NagramiXOnboardingCommunication",
            @"NagramiXOnboardingFree", @"NagramiXOnboardingPersonal",
            @"NagramiXOnboardingPrivacy", @"NagramiXOnboardingNearby",
            @"NagramiXOnboardingPhone"
        ];
        NSMutableArray *result = [[NSMutableArray alloc] initWithCapacity:names.count];
        for (NSString *name in names) {
            UIImage *image = [UIImage imageNamed:name inBundle:[NSBundle mainBundle] compatibleWithTraitCollection:nil];
            [result addObject:image ?: (id)[NSNull null]];
        }
        images = [result copy];
    });
    id image = images[index];
    return [image isKindOfClass:[UIImage class]] ? image : nil;
}

UIImage *NagramiXOnboardingSymbol(NSInteger index) {
    return index >= 0 && index < 6 ? NagramiXOnboardingImage(index + 1) : nil;
}
