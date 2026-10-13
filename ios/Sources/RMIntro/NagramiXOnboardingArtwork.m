#import "RMIntroViewController.h"

// Shared by the carousel and the phone entry screen. The atlas remains a
// single production resource; UIKit slices its six square cells at runtime.
UIImage *NagramiXOnboardingImage(NSInteger index) {
    if (index < 0 || index > 6) {
        return nil;
    }
    static NSArray *images;
    static dispatch_once_t onceToken;
    dispatch_once(&onceToken, ^{
        NSMutableArray *result = [[NSMutableArray alloc] initWithCapacity:7];
        NSBundle *bundle = [NSBundle mainBundle];
        UIImage *logo = [UIImage imageNamed:@"NagramiXOnboardingLogo" inBundle:bundle compatibleWithTraitCollection:nil];
        UIImage *atlas = [UIImage imageNamed:@"NagramiXOnboardingAtlas" inBundle:bundle compatibleWithTraitCollection:nil];
        NSArray<NSString *> *fallbackSymbols = @[@"bubble.left.fill", @"bolt.horizontal.circle.fill", @"gift.fill", @"slider.horizontal.3", @"hand.raised.fill", @"icloud.fill", @"iphone"];
        for (NSInteger item = 0; item < 7; item++) {
            UIImage *image = item == 0 ? logo : nil;
            if (item > 0 && atlas.CGImage != NULL) {
                size_t width = CGImageGetWidth(atlas.CGImage);
                size_t height = CGImageGetHeight(atlas.CGImage);
                if (width % 3 == 0 && height % 2 == 0 && width / 3 == height / 2) {
                    size_t side = width / 3;
                    NSInteger cell = item - 1;
                    CGRect rect = CGRectMake((cell % 3) * side, (cell / 3) * side, side, side);
                    CGImageRef cropped = CGImageCreateWithImageInRect(atlas.CGImage, rect);
                    if (cropped != NULL) {
                        image = [UIImage imageWithCGImage:cropped scale:2.0 orientation:UIImageOrientationUp];
                        CGImageRelease(cropped);
                    }
                }
            }
            if (image == nil) {
                UIImageSymbolConfiguration *configuration = [UIImageSymbolConfiguration configurationWithPointSize:160.0 weight:UIImageSymbolWeightMedium];
                image = [[UIImage systemImageNamed:fallbackSymbols[item] withConfiguration:configuration] imageWithTintColor:[UIColor colorWithRed:0.18 green:0.66 blue:1.0 alpha:1.0] renderingMode:UIImageRenderingModeAlwaysOriginal];
            }
            [result addObject:image ?: (id)[NSNull null]];
        }
        images = [result copy];
    });
    id image = images[index];
    return [image isKindOfClass:[UIImage class]] ? image : nil;
}
