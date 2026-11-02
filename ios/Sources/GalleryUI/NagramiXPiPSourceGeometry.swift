import Foundation

// Geometry of the inline source only. AVKit owns the separate system window.
// Keep the complete source on screen while AVKit evaluates PiP eligibility.
struct NagramiXPiPSourceGeometry {
    let frame: CGRect
    let scale: CGFloat
    let progress: CGFloat

    static func resolve(source: CGRect, viewport: CGRect, safeArea: CGRect,
                        translation: CGPoint, release _: NagramiXPiPReleaseKind? = nil) -> Self? {
        let values = [source.minX, source.minY, source.width, source.height,
                      viewport.minX, viewport.minY, viewport.width, viewport.height,
                      safeArea.minX, safeArea.minY, safeArea.width, safeArea.height,
                      translation.x, translation.y]
        guard values.allSatisfy({ $0.isFinite }), source.width > 0, source.height > 0,
              viewport.width > 0, viewport.height > 0, safeArea.width > 0, safeArea.height > 0 else { return nil }
        let safe = viewport.intersection(safeArea)
        guard !safe.isNull, safe.width > 0, safe.height > 0 else { return nil }
        let distance = hypot(translation.x, translation.y)
        guard distance.isFinite else { return nil }
        let fraction = min(1, distance / max(1, min(viewport.width, viewport.height) * 0.65))
        // The derivative reaches zero at the minimum size, rather than changing
        // abruptly when a long drag crosses the end of the shrinking range.
        let progress = fraction * (2 - fraction)
        let minimumScale = min(1, min(safe.width * 0.52 / source.width, safe.height * 0.32 / source.height))
        let scale = 1 - (1 - minimumScale) * progress
        let width = source.width * scale, height = source.height * scale
        // Safe-area margins enter continuously. A full-screen portrait starts
        // at its original size/position rather than jumping on the first delta.
        let area = CGRect(x: viewport.minX + (safe.minX - viewport.minX) * progress,
                          y: viewport.minY + (safe.minY - viewport.minY) * progress,
                          width: viewport.width + (safe.width - viewport.width) * progress,
                          height: viewport.height + (safe.height - viewport.height) * progress)
        let minX = area.minX + width / 2, maxX = area.maxX - width / 2
        let minY = area.minY + height / 2, maxY = area.maxY - height / 2
        func bound(_ value: CGFloat, _ lower: CGFloat, _ upper: CGFloat) -> CGFloat {
            lower <= upper ? min(upper, max(lower, value)) : (lower + upper) / 2
        }
        // Releasing never substitutes an edge target or a different size.
        // AVKit continues from the exact final interactive source rectangle.
        let x = bound(source.midX + translation.x, minX, maxX)
        let y = bound(source.midY + translation.y, minY, maxY)
        let frame = CGRect(x: x - width / 2, y: y - height / 2, width: width, height: height)
        guard [frame.minX, frame.minY, frame.maxX, frame.maxY, scale].allSatisfy({ $0.isFinite }), scale > 0 else { return nil }
        return Self(frame: frame, scale: scale, progress: progress)
    }
}
