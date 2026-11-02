import Foundation

public enum NagramiXHybridPiPPlacement {
    /// Flick direction wins; a held drag uses the half where it was released.
    public static func half(deltaY: Double, releaseY: Double, midpointY: Double, swipe: Bool) -> Double? {
        guard deltaY.isFinite, releaseY.isFinite, midpointY.isFinite else { return nil }
        if swipe && deltaY != 0 { return deltaY < 0 ? 0 : 1 }
        return releaseY < midpointY ? 0 : 1
    }
}
