package com.mr_efes.nagramix;

import java.util.Calendar;

/** Platform-neutral estimate contract mirrored from the iOS 0.2.4 behavior. */
public final class NagramiXPeerMetadata {
    private NagramiXPeerMetadata() {}

    public static int approximateRegistrationYear(long peerId) {
        long value = peerId == Long.MIN_VALUE ? Long.MAX_VALUE : Math.abs(peerId);
        if (value < 10_000_000L) return 2013;
        if (value < 50_000_000L) return 2014;
        if (value < 150_000_000L) return 2015;
        if (value < 300_000_000L) return 2016;
        if (value < 500_000_000L) return 2017;
        if (value < 800_000_000L) return 2018;
        if (value < 1_100_000_000L) return 2019;
        if (value < 1_400_000_000L) return 2020;
        if (value < 1_700_000_000L) return 2021;
        if (value < 2_100_000_000L) return 2022;
        if (value < 4_000_000_000L) return 2023;
        if (value < 7_000_000_000L) return 2024;
        if (value < 10_000_000_000L) return 2025;
        return Calendar.getInstance().get(Calendar.YEAR);
    }
}
