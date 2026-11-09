#import <Foundation/Foundation.h>

@class MTSignal;

NS_ASSUME_NONNULL_BEGIN

@interface NagramiXDNSResolver : NSObject

+ (BOOL)usesSystemResolver;
+ (MTSignal *)resolveHostname:(NSString *)hostname;
+ (MTSignal *)resolveHostname:(NSString *)hostname preferIPv6:(BOOL)preferIPv6;
+ (MTSignal *)testEndpoint:(NSString *)endpoint hostname:(NSString *)hostname;

@end

NS_ASSUME_NONNULL_END
