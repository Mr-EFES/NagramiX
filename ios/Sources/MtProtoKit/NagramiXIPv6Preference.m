#import "NagramiXIPv6Preference.h"
#import <dispatch/dispatch.h>

@implementation NagramiXIPv6Preference

+ (BOOL)enabled {
    id value = [[NSUserDefaults standardUserDefaults] objectForKey:@"nagramix.network.preferIPv6"];
    return [value isKindOfClass:[NSNumber class]] && [value boolValue];
}

+ (NSMutableDictionary<NSString *, NSNumber *> *)failures {
    static NSMutableDictionary<NSString *, NSNumber *> *values;
    static dispatch_once_t once;
    dispatch_once(&once, ^{ values = [[NSMutableDictionary alloc] init]; });
    return values;
}

+ (NSString *)keyForHost:(NSString *)host port:(int32_t)port {
    return [NSString stringWithFormat:@"%@:%d", host.lowercaseString, port];
}

+ (BOOL)preferForHost:(NSString *)host port:(int32_t)port {
    if (![self enabled]) { return NO; }
    @synchronized (self) {
        NSString *key = [self keyForHost:host port:port];
        NSNumber *failure = [self failures][key];
        if (failure != nil && NagramiXIPv6RecentFailure([NSProcessInfo processInfo].systemUptime, failure.doubleValue, 0.0)) {
            return NO;
        }
        [[self failures] removeObjectForKey:key];
        return YES;
    }
}

+ (void)recordFailureForHost:(NSString *)host port:(int32_t)port {
    if (![self enabled] || host.length == 0) { return; }
    @synchronized (self) {
        // Process-local, bounded state. Never persist failed routes or alter
        // the user's checkbox, DNS provider, proxy list or failover interval.
        NSMutableDictionary<NSString *, NSNumber *> *values = [self failures];
        NSString *key = [self keyForHost:host port:port];
        if (values.count >= 256 && values[key] == nil) {
            NSString *oldest = nil;
            for (NSString *candidate in values) {
                if (oldest == nil || values[candidate].doubleValue < values[oldest].doubleValue) { oldest = candidate; }
            }
            if (oldest != nil) { [values removeObjectForKey:oldest]; }
        }
        values[key] = @([NSProcessInfo processInfo].systemUptime);
    }
}

+ (void)recordSuccessForHost:(NSString *)host port:(int32_t)port {
    @synchronized (self) { [[self failures] removeObjectForKey:[self keyForHost:host port:port]]; }
}

@end
