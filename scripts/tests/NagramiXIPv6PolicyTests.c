#include "NagramiXIPv6Policy.h"
#include <assert.h>
#include <limits.h>
#include <stdio.h>

static unsigned int checks = 0;
#define CHECK(value) do { assert(value); checks++; } while (0)

int main(void) {
    // Both available: preference chooses IPv6; no preference keeps IPv4.
    CHECK(NagramiXIPv6DNSFamily(false, true, true) == 4);
    CHECK(NagramiXIPv6DNSFamily(true, true, true) == 6);
    for (int prefer = 0; prefer <= 1; prefer++) {
        CHECK(NagramiXIPv6DNSFamily(prefer, true, false) == 4);
        CHECK(NagramiXIPv6DNSFamily(prefer, false, true) == 6);
        CHECK(NagramiXIPv6DNSFamily(prefer, false, false) == 0);
    }
    const uint16_t stock[] = {1, 28, 1, 28}, ipv6[] = {28, 1, 28, 1};
    for (unsigned int i = 0; i < 4; i++) {
        CHECK(NagramiXIPv6DNSQueryType(false,i) == stock[i]);
        CHECK(NagramiXIPv6DNSQueryType(true,i) == ipv6[i]);
    }
    CHECK(NagramiXIPv6DNSQueryType(false,4) == 0);
    CHECK(NagramiXIPv6DNSQueryType(true,UINT_MAX) == 0);
    // Probe IPv6 before first success, rather than requiring a past IPv6 session.
    CHECK(NagramiXIPv6ShouldReplaceScheme(true,0,0,false,0,0,100));
    CHECK(!NagramiXIPv6ShouldReplaceScheme(false,0,0,true,0,0,100));
    // Failed IPv6 yields to healthy IPv4. A new success makes it preferred again.
    CHECK(NagramiXIPv6ShouldReplaceScheme(false,0,0,true,99,0,100));
    CHECK(!NagramiXIPv6ShouldReplaceScheme(true,99,0,false,0,0,100));
    CHECK(NagramiXIPv6ShouldReplaceScheme(true,99,100,false,0,0,100));
    // Retry after the cooldown, including the exact boundary.
    CHECK(!NagramiXIPv6ShouldReplaceScheme(true,99,0,false,0,0,158));
    CHECK(NagramiXIPv6ShouldReplaceScheme(true,99,0,false,0,0,159));
    // When both routes failed recently keep the native oldest-failure strategy.
    CHECK(NagramiXIPv6ShouldReplaceScheme(false,90,0,true,99,0,100));
    CHECK(!NagramiXIPv6ShouldReplaceScheme(true,99,0,false,90,0,100));
    CHECK(!NagramiXIPv6ShouldReplaceScheme(true,99,0,true,99,0,100));
    // Same-family healthy choices preserve native failure ordering and ties.
    CHECK(NagramiXIPv6ShouldReplaceScheme(false,70,100,false,80,100,100));
    CHECK(!NagramiXIPv6ShouldReplaceScheme(true,80,100,true,70,100,100));
    CHECK(!NagramiXIPv6RecentFailure(100,0,0));
    CHECK(NagramiXIPv6RecentFailure(100,99,0));
    CHECK(!NagramiXIPv6RecentFailure(100,99,100));
    CHECK(!NagramiXIPv6RecentFailure(100,40,0));
    CHECK(!NagramiXIPv6RecentFailure(100,101,0));
    CHECK(!NagramiXIPv6RecentFailure(NAN,99,0));
    CHECK(!NagramiXIPv6RecentFailure(INFINITY,99,0));
    CHECK(!NagramiXIPv6RecentFailure(100,NAN,0));
    CHECK(!NagramiXIPv6RecentFailure(100,99,INFINITY));
    CHECK(NagramiXIPv6SchemeRank(true,INT32_MAX,0,INT32_MIN) == 0);
    CHECK(NagramiXIPv6SchemeRank(false,INT32_MIN,0,INT32_MAX) == 1);
    // Only failed IPv6 TCP establishment from a hostname changes host backoff.
    CHECK(NagramiXIPv6ShouldRecordFailure(true,true,false,true,true));
    CHECK(!NagramiXIPv6ShouldRecordFailure(true,false,false,true,true)); // cancel/reconfigure
    CHECK(!NagramiXIPv6ShouldRecordFailure(true,true,true,true,true)); // connected/auth/protocol error
    CHECK(!NagramiXIPv6ShouldRecordFailure(true,true,false,false,true)); // IPv4 error
    CHECK(!NagramiXIPv6ShouldRecordFailure(true,true,false,true,false)); // literal IP
    CHECK(!NagramiXIPv6ShouldRecordFailure(false,true,false,true,true)); // default OFF
    printf("PASS: %u actual C IPv6/fallback/backoff/DNS policy checks\n",checks);
    return 0;
}
