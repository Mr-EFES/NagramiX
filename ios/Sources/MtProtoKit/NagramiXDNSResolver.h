#import <Foundation/Foundation.h>

@class MTSignal;

NS_ASSUME_NONNULL_BEGIN

@interface NagramiXDNSResolver : NSObject

+ (BOOL)usesSystemResolver;
+ (MTSignal *)resolveHostname:(NSString *)hostname;
+ (MTSignal *)testEndpoint:(NSString *)endpoint hostname:(NSString *)hostname;

@end

NS_ASSUME_NONNULL_END
