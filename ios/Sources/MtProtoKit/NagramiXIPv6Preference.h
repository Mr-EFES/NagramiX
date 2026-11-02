#import <Foundation/Foundation.h>
#import "NagramiXIPv6Policy.h"

NS_ASSUME_NONNULL_BEGIN

@interface NagramiXIPv6Preference : NSObject
+ (BOOL)enabled;
+ (BOOL)preferForHost:(NSString *)host port:(int32_t)port;
+ (void)recordFailureForHost:(NSString *)host port:(int32_t)port;
+ (void)recordSuccessForHost:(NSString *)host port:(int32_t)port;
@end

NS_ASSUME_NONNULL_END
