import Foundation
#if canImport(Glibc)
import Glibc
#else
import Darwin
#endif

// This contract also executes against the previous production geometry. It
// reproduces its release snap without depending on newly added model fields.
@main struct PiPHandoffContinuityTests {
    static func main() {
        let viewport = CGRect(x: 0, y: 0, width: 390, height: 844)
        let safe = viewport.insetBy(dx: 20, dy: 64)
        var checks = 0, failures = 0
        for aspect: CGFloat in [16 / 9, 9 / 16, 1] {
            let width = min(viewport.width, viewport.height * aspect), height = width / aspect
            let source = CGRect(x: (viewport.width - width) / 2, y: (viewport.height - height) / 2, width: width, height: height)
            for delta in [CGPoint(x: 0, y: -48), CGPoint(x: 0, y: 48), CGPoint(x: -48, y: 0), CGPoint(x: 48, y: 0),
                          CGPoint(x: 0, y: -120), CGPoint(x: 0, y: 120), CGPoint(x: -120, y: 0), CGPoint(x: 120, y: 0)] {
                let tracking = NagramiXPiPSourceGeometry.resolve(source: source, viewport: viewport, safeArea: safe, translation: delta)!
                for release in [NagramiXPiPReleaseKind.swipe, .drag] {
                    let handoff = NagramiXPiPSourceGeometry.resolve(source: source, viewport: viewport, safeArea: safe, translation: delta, release: release)!
                    checks += 1
                    if tracking.frame != handoff.frame || tracking.scale != handoff.scale { failures += 1 }
                }
            }
        }
        print("\(checks) release continuity checks; \(failures) frame/scale discontinuities")
        exit(failures == 0 ? 0 : 1)
    }
}
