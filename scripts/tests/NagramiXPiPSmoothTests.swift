import Foundation

@main struct PiPSmoothTests {
    static func main() {
        var checks = 0
        func check(_ value: @autoclosure () -> Bool, _ label: String) {
            precondition(value(), label); checks += 1
        }
        for size in [CGSize(width: 320, height: 568), CGSize(width: 430, height: 932), CGSize(width: 932, height: 430)] {
            let viewport = CGRect(origin: .zero, size: size)
            let safe = viewport.insetBy(dx: 20, dy: 64)
            for aspect: CGFloat in [9 / 16, 16 / 9, 1, 0.1, 10] {
                let width = min(size.width, size.height * aspect), height = width / aspect
                let source = CGRect(x: (size.width - width) / 2, y: (size.height - height) / 2, width: width, height: height)
                let origin = NagramiXPiPSourceGeometry.resolve(source: source, viewport: viewport, safeArea: safe, translation: .zero)!
                let tiny = NagramiXPiPSourceGeometry.resolve(source: source, viewport: viewport, safeArea: safe, translation: CGPoint(x: 0, y: 0.01))!
                check(abs(origin.scale - tiny.scale) / 0.01 < 0.000001, "zero initial shrink velocity")
                check(tiny.progress / 0.01 < 0.000001, "zero initial fade velocity")
                let first = NagramiXPiPSourceGeometry.resolve(source: source, viewport: viewport, safeArea: safe, translation: CGPoint(x: 0, y: 1))!
                check(1 - first.scale < 0.0001, "one point drag has no abrupt shrink")
                var previous = origin
                for step in 1...100 {
                    let distance = min(size.width, size.height) * 0.65 * CGFloat(step) / 100
                    let down = NagramiXPiPSourceGeometry.resolve(source: source, viewport: viewport, safeArea: safe, translation: CGPoint(x: 0, y: distance))!
                    let up = NagramiXPiPSourceGeometry.resolve(source: source, viewport: viewport, safeArea: safe, translation: CGPoint(x: 0, y: -distance))!
                    check(down.scale <= previous.scale && down.progress >= previous.progress, "monotonic shrink and reveal")
                    check(down.frame.midY >= previous.frame.midY - 0.000001, "downward drag never reverses upward")
                    check(up.frame.midY <= source.midY && down.frame.midY >= source.midY, "both vertical directions respected inline")
                    check(abs(up.frame.midY + down.frame.midY - 2 * source.midY) < 0.000001, "symmetric vertical response")
                    previous = down
                }
                for direction in [CGPoint(x: -1, y: 0), CGPoint(x: 1, y: 0), CGPoint(x: -1, y: -1), CGPoint(x: 1, y: 1)] {
                    var previous = origin
                    for step in 1...100 {
                        let delta = CGPoint(x: CGFloat(step) * direction.x * 6, y: CGFloat(step) * direction.y * 6)
                        let next = NagramiXPiPSourceGeometry.resolve(source: source, viewport: viewport, safeArea: safe, translation: delta)!
                        check((next.frame.midX - previous.frame.midX) * direction.x >= -0.000001, "horizontal/diagonal source never reverses")
                        check((next.frame.midY - previous.frame.midY) * direction.y >= -0.000001, "diagonal source never reverses vertically")
                        previous = next
                    }
                }
                let shifted = source.offsetBy(dx: min(40, (size.width-source.width)/2), dy: min(40, (size.height-source.height)/2))
                for direction in [CGPoint(x: -1, y: -1), CGPoint(x: 1, y: 1)] {
                    let zero = NagramiXPiPSourceGeometry.resolve(source: shifted, viewport: viewport, safeArea: safe, translation: .zero)!
                    check(abs(zero.frame.minX-shifted.minX) < 0.000001
                        && abs(zero.frame.minY-shifted.minY) < 0.000001
                        && abs(zero.frame.width-shifted.width) < 0.000001
                        && abs(zero.frame.height-shifted.height) < 0.000001, "off-center interrupted return has no initial jump")
                    var previous = zero
                    for step in 1...100 {
                        let next = NagramiXPiPSourceGeometry.resolve(source: shifted, viewport: viewport, safeArea: safe,
                            translation: CGPoint(x: CGFloat(step)*direction.x*6, y: CGFloat(step)*direction.y*6))!
                        check((next.frame.midX-previous.frame.midX)*direction.x >= -0.000001, "off-center horizontal movement stays directional")
                        check((next.frame.midY-previous.frame.midY)*direction.y >= -0.000001, "off-center vertical movement stays directional")
                        previous = next
                    }
                }
            }
        }
        print("PASS: \(checks) smooth onset and directional source checks (AVKit window not exercised)")
    }
}
