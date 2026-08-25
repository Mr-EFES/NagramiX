#import "NagramiXDNSResolver.h"

#import <arpa/inet.h>
#import <stdint.h>
#import <MtProtoKit/MTSignal.h>

static NSString * const NagramiXDnsProviderKey = @"nagramix.network.dnsProvider";
static NSString * const NagramiXCustomDohUrlKey = @"nagramix.network.customDohUrl";

typedef NS_ENUM(NSInteger, NagramiXDnsProvider) {
    NagramiXDnsProviderSystem = 0,
    NagramiXDnsProviderGoogle = 1,
    NagramiXDnsProviderQuad9 = 2,
    NagramiXDnsProviderAdGuard = 3,
    NagramiXDnsProviderMullvad = 4,
    NagramiXDnsProviderCloudflare = 5,
    NagramiXDnsProviderCustom = 6
};

static void NagramiXAppendUInt16(NSMutableData *data, uint16_t value) {
    uint16_t networkValue = CFSwapInt16HostToBig(value);
    [data appendBytes:&networkValue length:sizeof(networkValue)];
}

static BOOL NagramiXReadUInt16(NSData *data, NSUInteger offset, uint16_t *value) {
    if (offset + 2 > data.length) {
        return NO;
    }
    uint16_t raw = 0;
    [data getBytes:&raw range:NSMakeRange(offset, 2)];
    *value = CFSwapInt16BigToHost(raw);
    return YES;
}

static BOOL NagramiXReadUInt32(NSData *data, NSUInteger offset, uint32_t *value) {
    if (offset + 4 > data.length) {
        return NO;
    }
    uint32_t raw = 0;
    [data getBytes:&raw range:NSMakeRange(offset, 4)];
    *value = CFSwapInt32BigToHost(raw);
    return YES;
}

static BOOL NagramiXSkipDnsName(NSData *data, NSUInteger *offset) {
    NSUInteger cursor = *offset;
    NSUInteger labels = 0;
    while (cursor < data.length && labels < 128) {
        uint8_t length = 0;
        [data getBytes:&length range:NSMakeRange(cursor, 1)];
        cursor += 1;
        if (length == 0) {
            *offset = cursor;
            return YES;
        }
        if ((length & 0xc0) == 0xc0) {
            if (cursor >= data.length) {
                return NO;
            }
            *offset = cursor + 1;
            return YES;
        }
        if ((length & 0xc0) != 0 || length > 63 || cursor + length > data.length) {
            return NO;
        }
        cursor += length;
        labels += 1;
    }
    return NO;
}

static NSData * _Nullable NagramiXMakeDnsQuery(NSString *hostname, uint16_t type, uint16_t identifier) {
    NSString *normalized = [hostname stringByTrimmingCharactersInSet:[NSCharacterSet characterSetWithCharactersInString:@"."]];
    if (normalized.length == 0) {
        return nil;
    }
    NSMutableData *data = [[NSMutableData alloc] init];
    NagramiXAppendUInt16(data, identifier);
    NagramiXAppendUInt16(data, 0x0100);
    NagramiXAppendUInt16(data, 1);
    NagramiXAppendUInt16(data, 0);
    NagramiXAppendUInt16(data, 0);
    NagramiXAppendUInt16(data, 0);
    for (NSString *label in [normalized componentsSeparatedByString:@"."]) {
        NSData *labelData = [label dataUsingEncoding:NSUTF8StringEncoding];
        if (labelData.length == 0 || labelData.length > 63) {
            return nil;
        }
        uint8_t length = (uint8_t)labelData.length;
        [data appendBytes:&length length:1];
        [data appendData:labelData];
    }
    uint8_t zero = 0;
    [data appendBytes:&zero length:1];
    NagramiXAppendUInt16(data, type);
    NagramiXAppendUInt16(data, 1);
    return data;
}

static NSString * _Nullable NagramiXParseDnsResponse(NSData *data, uint16_t identifier, uint16_t expectedType) {
    if (data.length < 12) {
        return nil;
    }
    uint16_t responseId = 0, flags = 0, questionCount = 0, answerCount = 0;
    if (!NagramiXReadUInt16(data, 0, &responseId) || !NagramiXReadUInt16(data, 2, &flags) || !NagramiXReadUInt16(data, 4, &questionCount) || !NagramiXReadUInt16(data, 6, &answerCount)) {
        return nil;
    }
    if (responseId != identifier || (flags & 0x8000) == 0 || (flags & 0x000f) != 0) {
        return nil;
    }
    NSUInteger offset = 12;
    for (NSUInteger i = 0; i < questionCount; i++) {
        if (!NagramiXSkipDnsName(data, &offset) || offset + 4 > data.length) {
            return nil;
        }
        offset += 4;
    }
    for (NSUInteger i = 0; i < answerCount; i++) {
        if (!NagramiXSkipDnsName(data, &offset) || offset + 10 > data.length) {
            return nil;
        }
        uint16_t type = 0, dnsClass = 0, dataLength = 0;
        uint32_t ttl = 0;
        if (!NagramiXReadUInt16(data, offset, &type) || !NagramiXReadUInt16(data, offset + 2, &dnsClass) || !NagramiXReadUInt32(data, offset + 4, &ttl) || !NagramiXReadUInt16(data, offset + 8, &dataLength)) {
            return nil;
        }
        (void)ttl;
        offset += 10;
        if (offset + dataLength > data.length) {
            return nil;
        }
        if (dnsClass == 1 && type == expectedType && ((type == 1 && dataLength == 4) || (type == 28 && dataLength == 16))) {
            char buffer[INET6_ADDRSTRLEN] = {0};
            const void *bytes = ((const uint8_t *)data.bytes) + offset;
            if (inet_ntop(type == 1 ? AF_INET : AF_INET6, bytes, buffer, sizeof(buffer)) != NULL) {
                return [NSString stringWithUTF8String:buffer];
            }
        }
        offset += dataLength;
    }
    return nil;
}

@implementation NagramiXDNSResolver

+ (NagramiXDnsProvider)provider {
    NSInteger rawValue = [[NSUserDefaults standardUserDefaults] integerForKey:NagramiXDnsProviderKey];
    if (rawValue < NagramiXDnsProviderSystem || rawValue > NagramiXDnsProviderCustom) {
        return NagramiXDnsProviderSystem;
    }
    return (NagramiXDnsProvider)rawValue;
}

+ (BOOL)usesSystemResolver {
    return [self provider] == NagramiXDnsProviderSystem;
}

+ (NSString * _Nullable)configuredEndpoint {
    switch ([self provider]) {
        case NagramiXDnsProviderSystem:
            return nil;
        case NagramiXDnsProviderGoogle:
            return @"https://dns.google/dns-query";
        case NagramiXDnsProviderQuad9:
            return @"https://dns.quad9.net/dns-query";
        case NagramiXDnsProviderAdGuard:
            return @"https://dns.adguard-dns.com/dns-query";
        case NagramiXDnsProviderMullvad:
            return @"https://dns.mullvad.net/dns-query";
        case NagramiXDnsProviderCloudflare:
            return @"https://cloudflare-dns.com/dns-query";
        case NagramiXDnsProviderCustom:
            return [[NSUserDefaults standardUserDefaults] stringForKey:NagramiXCustomDohUrlKey];
    }
}

+ (MTSignal *)resolveHostname:(NSString *)hostname {
    NSString *endpoint = [self configuredEndpoint];
    if (endpoint.length == 0) {
        return [MTSignal fail:nil];
    }
    return [self resolveHostname:hostname endpoint:endpoint];
}

+ (MTSignal *)testEndpoint:(NSString *)endpoint hostname:(NSString *)hostname {
    return [self resolveHostname:hostname endpoint:endpoint];
}

+ (MTSignal *)resolveHostname:(NSString *)hostname endpoint:(NSString *)endpoint {
    return [[MTSignal alloc] initWithGenerator:^id<MTDisposable>(MTSubscriber *subscriber) {
        NSURL *url = [NSURL URLWithString:endpoint];
        if (url == nil || ![url.scheme.lowercaseString isEqualToString:@"https"] || url.host.length == 0) {
            [subscriber putError:nil];
            return nil;
        }

        NSURLSessionConfiguration *configuration = [NSURLSessionConfiguration ephemeralSessionConfiguration];
        configuration.timeoutIntervalForRequest = 8.0;
        configuration.timeoutIntervalForResource = 12.0;
        configuration.requestCachePolicy = NSURLRequestReloadIgnoringLocalCacheData;
        NSURLSession *session = [NSURLSession sessionWithConfiguration:configuration];
        NSObject *cancellationLock = [[NSObject alloc] init];
        __block BOOL cancelled = NO;
        __block NSURLSessionDataTask *currentTask = nil;
        __block void (^attempt)(NSUInteger) = nil;
        NSArray<NSNumber *> *types = @[@1, @28];

        attempt = ^(NSUInteger index) {
            @synchronized (cancellationLock) {
                if (cancelled) {
                    return;
                }
            }
            if (index >= types.count) {
                [session finishTasksAndInvalidate];
                [subscriber putError:nil];
                attempt = nil;
                return;
            }
            uint16_t type = (uint16_t)types[index].unsignedIntegerValue;
            uint16_t identifier = (uint16_t)arc4random_uniform(UINT16_MAX);
            NSData *query = NagramiXMakeDnsQuery(hostname, type, identifier);
            if (query == nil) {
                [session invalidateAndCancel];
                [subscriber putError:nil];
                attempt = nil;
                return;
            }
            NSMutableURLRequest *request = [NSMutableURLRequest requestWithURL:url cachePolicy:NSURLRequestReloadIgnoringLocalCacheData timeoutInterval:8.0];
            request.HTTPMethod = @"POST";
            request.HTTPBody = query;
            [request setValue:@"application/dns-message" forHTTPHeaderField:@"Content-Type"];
            [request setValue:@"application/dns-message" forHTTPHeaderField:@"Accept"];

            currentTask = [session dataTaskWithRequest:request completionHandler:^(NSData *data, NSURLResponse *response, NSError *error) {
                @synchronized (cancellationLock) {
                    if (cancelled) {
                        return;
                    }
                }
                NSHTTPURLResponse *httpResponse = [response isKindOfClass:[NSHTTPURLResponse class]] ? (NSHTTPURLResponse *)response : nil;
                NSString *address = error == nil && httpResponse.statusCode == 200 ? NagramiXParseDnsResponse(data, identifier, type) : nil;
                if (address.length != 0) {
                    [session finishTasksAndInvalidate];
                    [subscriber putNext:address];
                    [subscriber putCompletion];
                    attempt = nil;
                } else {
                    attempt(index + 1);
                }
            }];
            [currentTask resume];
        };
        attempt(0);

        return [[MTBlockDisposable alloc] initWithBlock:^{
            @synchronized (cancellationLock) {
                cancelled = YES;
            }
            [currentTask cancel];
            [session invalidateAndCancel];
            attempt = nil;
        }];
    }];
}

@end
