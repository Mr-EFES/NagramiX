#import "RMIntroViewController.h"

UIColor *NagramiXOnboardingBackground(UIColor *nativeColor) {
    // Keep Telegram's selected theme color, including custom/dynamic colors.
    return nativeColor;
}

// Every welcome page uses the exact same transparent logo. The phone is an
// independent cutout for phone entry, never a screenshot of the complete page.
UIImage *NagramiXOnboardingImage(NSInteger index) {
    if (index < 0 || index >= 7) {
        return nil;
    }
    static NSArray *images;
    static dispatch_once_t onceToken;
    dispatch_once(&onceToken, ^{
        NSArray<NSString *> *names = @[
            @"NagramiXOnboardingLogo", @"NagramiXOnboardingPhone"
        ];
        NSMutableArray *result = [[NSMutableArray alloc] initWithCapacity:names.count];
        for (NSString *name in names) {
            UIImage *image = [UIImage imageNamed:name inBundle:[NSBundle mainBundle] compatibleWithTraitCollection:nil];
            [result addObject:image ?: (id)[NSNull null]];
        }
        images = [result copy];
    });
    id image = images[index == 6 ? 1 : 0];
    return [image isKindOfClass:[UIImage class]] ? image : nil;
}

UIImage *NagramiXOnboardingSymbol(NSInteger index) {
    return index >= 0 && index < 6 ? NagramiXOnboardingImage(0) : nil;
}
