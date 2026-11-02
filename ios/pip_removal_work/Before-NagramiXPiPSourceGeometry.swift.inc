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
        // Zero shrink/fade velocity at both ends avoids the abrupt initial
        // size change of ease-out. Direction and final AVKit handoff stay exact.
        let progress = fraction * fraction * (3 - 2 * fraction)
        let minimumScale = min(1, min(safe.width * 0.52 / source.width, safe.height * 0.32 / source.height))
        let scale = 1 - (1 - minimumScale) * progress
        let width = source.width * scale, height = source.height * scale
        // Grow travel bounds as the surface shrinks, stopping at the final
        // safe-area limits. Interpolating the viewport itself can pull a wide
        // video back against the finger near the top/bottom edge.
        // Include the initial center so an interrupted return does not jump.
        let finalHalfWidth = source.width * minimumScale / 2
        let finalHalfHeight = source.height * minimumScale / 2
        let minX = max(viewport.minX + width / 2, min(source.midX, safe.minX + finalHalfWidth))
        let maxX = min(viewport.maxX - width / 2, max(source.midX, safe.maxX - finalHalfWidth))
        let minY = max(viewport.minY + height / 2, min(source.midY, safe.minY + finalHalfHeight))
        let maxY = min(viewport.maxY - height / 2, max(source.midY, safe.maxY - finalHalfHeight))
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
