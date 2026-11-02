import Foundation

@main struct SpacingTests {
    static func main() {
        var checks = 0
        for landscape in [false, true] {
            for width: CGFloat in (landscape ? [568, 667, 844, 932] : [320, 375, 393, 430]) {
                for height: CGFloat in (landscape ? [162, 180, 216] : [260, 291, 346]) {
                    for safe: CGFloat in (landscape ? [0, 21] : [0, 21, 34]) {
                        for gap: CGFloat in [0, 4, 8, 12] {
                            let bands = NagramiXFormattingBands.layout(composerGap: gap, safeBottom: safe,
                                landscape: landscape, referenceLineHeight: 20.5)
                            let grid = NagramiXFormattingGrid.layout(size: CGSize(width: width - 16,
                                height: height - bands.top - bands.bottom), count: 10,
                                minimumLabelWidth: 70, minimumKeyHeight: 44, accessibility: false,
                                footerMinimumLabelWidth: 90, landscape: landscape)
                            let first = grid.frames.map(\.minY).min()!
                            let last = grid.frames.map(\.maxY).max()!
                            // Координаты внешних краёв: поле выше начала панели на gap.
                            let upper = gap + bands.top + first
                            let lower = height - bands.top - last
                            precondition(abs(upper - lower) < 0.0001)
                            precondition(grid.frames.count == 12 && grid.columns == (landscape ? 6 : 4))
                            precondition(bands.bottom >= safe + 8 && bands.top >= 8)
                            precondition(last + bands.top <= height - bands.bottom + 0.0001)
                            checks += 1
                        }
                    }
                }
            }
        }
        let invalid = NagramiXFormattingBands.layout(composerGap: .nan, safeBottom: .infinity,
            landscape: false, referenceLineHeight: .nan)
        precondition(invalid.top.isFinite && invalid.bottom.isFinite)
        print("PASS: \(checks) outer-edge A/B spacing and complete-grid cases; UIKit/device pending")
    }
}
