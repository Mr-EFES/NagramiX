import Foundation

@main struct PiPSourceGeometryTests {
    static func main() {
        var checks = 0
        func check(_ value: @autoclosure () -> Bool, _ name: String) {
            precondition(value(), name); checks += 1
        }
        func close(_ a: CGFloat, _ b: CGFloat) -> Bool { abs(a - b) < 0.000001 }
        func contains(_ outer: CGRect, _ inner: CGRect) -> Bool {
            inner.minX >= outer.minX - 0.000001 && inner.maxX <= outer.maxX + 0.000001
                && inner.minY >= outer.minY - 0.000001 && inner.maxY <= outer.maxY + 0.000001
        }
        let directions: [CGPoint] = [.init(x: 0, y: -1), .init(x: 0, y: 1),
            .init(x: -1, y: 0), .init(x: 1, y: 0), .init(x: -1, y: -1),
            .init(x: 1, y: -1), .init(x: -1, y: 1), .init(x: 1, y: 1)]
        for size in [CGSize(width: 390, height: 844), CGSize(width: 844, height: 390), CGSize(width: 320, height: 568)] {
            let viewport = CGRect(origin: .zero, size: size)
            let safe = viewport.insetBy(dx: 20, dy: 64)
            for aspect: CGFloat in [16 / 9, 9 / 16, 1, 0.1, 10] {
                let width = min(size.width, size.height * aspect)
                let height = width / aspect
                let source = CGRect(x: (size.width - width) / 2, y: (size.height - height) / 2, width: width, height: height)
                let origin = NagramiXPiPSourceGeometry.resolve(source: source, viewport: viewport, safeArea: safe, translation: .zero)!
                check(close(origin.scale, 1) && origin.frame == source, "no initial jump")
                for direction in directions {
                    for distance: CGFloat in [1, 12, 48, 100, 300, 900, 2000, 100000] {
                        let delta = CGPoint(x: direction.x * distance, y: direction.y * distance)
                        let pose = NagramiXPiPSourceGeometry.resolve(source: source, viewport: viewport, safeArea: safe, translation: delta)!
                        check(contains(viewport, pose.frame), "entire real layer stays visible even after a long drag")
                        check(pose.scale > 0 && pose.scale <= 1, "valid scale")
                        check(close(pose.frame.width / pose.frame.height, aspect), "preserve aspect ratio")
                        check((pose.frame.midX - source.midX) * direction.x >= -0.000001
                            && (pose.frame.midY - source.midY) * direction.y >= -0.000001, "follow finger direction")
                        if direction.x == 0 { check(close(pose.frame.midX, source.midX), "vertical has no lateral drift") }
                        if direction.y == 0 { check(close(pose.frame.midY, source.midY), "horizontal has no vertical drift") }
                        let drag = NagramiXPiPSourceGeometry.resolve(source: source, viewport: viewport, safeArea: safe, translation: delta, release: .drag)!
                        check(drag.frame == pose.frame && drag.scale == pose.scale, "held drag has no release jump")
                        let flick = NagramiXPiPSourceGeometry.resolve(source: source, viewport: viewport, safeArea: safe, translation: delta, release: .swipe)!
                        check(flick.frame == pose.frame && flick.scale == pose.scale, "swipe handoff keeps exact last interactive frame")
                        check(close(flick.frame.width / flick.frame.height, aspect), "flick keeps aspect")
                        if direction.x == 0 {
                            check(close(flick.frame.midX, source.midX), "pure vertical stays vertical")
                            let mirrored = NagramiXPiPSourceGeometry.resolve(source: source, viewport: viewport, safeArea: safe,
                                translation: CGPoint(x: delta.x, y: -delta.y))!
                            check(close(flick.frame.midY + mirrored.frame.midY, 2 * source.midY), "symmetric up/down motion")
                        }
                        if direction.y == 0 {
                            check(close(flick.frame.midY, source.midY), "pure horizontal stays horizontal")
                            let mirrored = NagramiXPiPSourceGeometry.resolve(source: source, viewport: viewport, safeArea: safe,
                                translation: CGPoint(x: -delta.x, y: delta.y))!
                            check(close(flick.frame.midX + mirrored.frame.midX, 2 * source.midX), "symmetric left/right motion")
                        }
                        check(flick.progress == pose.progress && (0...1).contains(pose.progress), "background has no release discontinuity")
                    }
                }
                // Adjacent tracking samples remain continuous, including the
                // point where shrinking stops and the edge clamp takes over.
                var previous = origin
                for n in 1...600 {
                    let next = NagramiXPiPSourceGeometry.resolve(source: source, viewport: viewport, safeArea: safe,
                        translation: CGPoint(x: CGFloat(n), y: CGFloat(n) * 0.3))!
                    check(abs(next.frame.midX - previous.frame.midX) < 3
                        && abs(next.frame.midY - previous.frame.midY) < 3
                        && abs(next.scale - previous.scale) < 0.02, "no discontinuities")
                    previous = next
                }
                // Nested gallery coordinates and an interrupted return have an
                // offset source/viewport, rather than screen-origin coordinates.
                let offset = CGPoint(x: -410, y: 844)
                let shifted = NagramiXPiPSourceGeometry.resolve(source: source.offsetBy(dx: offset.x, dy: offset.y),
                    viewport: viewport.offsetBy(dx: offset.x, dy: offset.y), safeArea: safe.offsetBy(dx: offset.x, dy: offset.y),
                    translation: CGPoint(x: 50, y: -150), release: .swipe)!
                let standard = NagramiXPiPSourceGeometry.resolve(source: source, viewport: viewport, safeArea: safe,
                    translation: CGPoint(x: 50, y: -150), release: .swipe)!
                check(close(shifted.frame.minX, standard.frame.minX + offset.x)
                    && close(shifted.frame.minY, standard.frame.minY + offset.y), "stable parent coordinate space")
                let limit = min(size.width, size.height) * 0.65
                let nearLimit = NagramiXPiPSourceGeometry.resolve(source: source, viewport: viewport, safeArea: safe,
                    translation: CGPoint(x: 0, y: limit - 0.01))!
                let atLimit = NagramiXPiPSourceGeometry.resolve(source: source, viewport: viewport, safeArea: safe,
                    translation: CGPoint(x: 0, y: limit))!
                let pastLimit = NagramiXPiPSourceGeometry.resolve(source: source, viewport: viewport, safeArea: safe,
                    translation: CGPoint(x: 0, y: limit + 0.01))!
                check(abs(atLimit.scale - nearLimit.scale) / 0.01 < 0.000001,
                    "shrink velocity approaches zero at the minimum size")
                check(atLimit.scale == pastLimit.scale && atLimit.progress == 1,
                    "no size bounce after shrink finishes")
            }
        }
        let rect = CGRect(x: 0, y: 0, width: 390, height: 844)
        for delta in [CGPoint(x: CGFloat.nan, y: 0), CGPoint(x: 0, y: CGFloat.infinity)] {
            check(NagramiXPiPSourceGeometry.resolve(source: rect, viewport: rect, safeArea: rect, translation: delta) == nil, "reject nonfinite input")
        }
        for invalid in [CGRect.zero, CGRect(x: 0, y: 0, width: CGFloat.infinity, height: 20), CGRect.null] {
            check(NagramiXPiPSourceGeometry.resolve(source: invalid, viewport: rect, safeArea: rect, translation: .zero) == nil, "reject invalid source")
        }
        check(NagramiXPiPSourceGeometry.resolve(source: rect, viewport: rect, safeArea: rect.offsetBy(dx: 400, dy: 0), translation: .zero) == nil, "reject absent safe area")
        print("PASS: \(checks) source geometry checks")
    }
}
