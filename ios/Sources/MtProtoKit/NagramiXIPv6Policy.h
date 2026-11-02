#ifndef NagramiXIPv6Policy_h
#define NagramiXIPv6Policy_h

#include <stdbool.h>
#include <stdint.h>
#include <math.h>

// The preference must never permanently strand a connection on broken IPv6.
static inline bool NagramiXIPv6RecentFailure(double now, double failure, double response) {
    return isfinite(now) && isfinite(failure) && isfinite(response)
        && failure > 0.0 && failure > response && now >= failure && now - failure < 60.0;
}

static inline int NagramiXIPv6SchemeRank(bool ipv6, int32_t failure, int32_t response, int32_t now) {
    return NagramiXIPv6RecentFailure(now, failure, response) ? 2 : (ipv6 ? 0 : 1);
}

static inline bool NagramiXIPv6ShouldReplaceScheme(bool candidateIPv6, int32_t candidateFailure, int32_t candidateResponse, bool currentIPv6, int32_t currentFailure, int32_t currentResponse, int32_t now) {
    int candidateRank = NagramiXIPv6SchemeRank(candidateIPv6, candidateFailure, candidateResponse, now);
    int currentRank = NagramiXIPv6SchemeRank(currentIPv6, currentFailure, currentResponse, now);
    return candidateRank < currentRank || (candidateRank == currentRank && candidateFailure < currentFailure);
}

static inline int NagramiXIPv6DNSFamily(bool preferIPv6, bool hasIPv4, bool hasIPv6) {
    if (hasIPv6 && (preferIPv6 || !hasIPv4)) { return 6; }
    return hasIPv4 ? 4 : 0;
}

static inline uint16_t NagramiXIPv6DNSQueryType(bool preferIPv6, unsigned int attempt) {
    if (attempt >= 4) { return 0; }
    return ((attempt % 2 == 0) == preferIPv6) ? 28 : 1;
}

static inline bool NagramiXIPv6ShouldRecordFailure(bool enabled, bool error, bool tcpConnected, bool ipv6, bool hasHostname) {
    return enabled && error && !tcpConnected && ipv6 && hasHostname;
}

#endif
