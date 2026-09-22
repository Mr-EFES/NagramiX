import Foundation

public enum NagramiXPeerMetadata {
    /// Telegram doesn't expose a user registration timestamp.
    /// This deliberately returns a broad, explicitly approximate year based on
    /// historically observed numeric user-id ranges instead of pretending to
    /// provide an exact date.
    public static func approximateRegistrationYear(peerId: Int64) -> Int {
        let value = abs(peerId)
        switch value {
        case ..<10_000_000: return 2013
        case ..<50_000_000: return 2014
        case ..<150_000_000: return 2015
        case ..<300_000_000: return 2016
        case ..<500_000_000: return 2017
        case ..<800_000_000: return 2018
        case ..<1_100_000_000: return 2019
        case ..<1_400_000_000: return 2020
        case ..<1_700_000_000: return 2021
        case ..<2_100_000_000: return 2022
        case ..<4_000_000_000: return 2023
        case ..<7_000_000_000: return 2024
        case ..<10_000_000_000: return 2025
        default: return Calendar.current.component(.year, from: Date())
        }
    }
}
