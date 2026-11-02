import Foundation

@main struct FormattingAdaptiveTests {
    static func main() {
        verifyFormattingBands()
        var checks = 0
        func check(_ value: Bool, _ label: String) {
            checks += 1
            precondition(value, label)
        }
        // Body sizes include matched upper/lower bands and horizontal safe areas.
        for (width, height, landscape) in [(304.0,144.0,false),(374,207,false),(414,260,false),
                                          (536,98,true),(690,120,true),(736,140,true),(828,152,true)] {
            let size = CGSize(width: width, height: height)
            let grid = NagramiXFormattingGrid.layout(size: size, count: 10, minimumLabelWidth: 75,
                minimumKeyHeight: 43, accessibility: false, footerMinimumLabelWidth: 80, landscape: landscape)
            check(grid.columns == (landscape ? 6 : 4), "orientation columns")
            check(grid.frames.count == 12, "all actions")
            check(abs(grid.contentSize.height - size.height) < 0.001, "no normal scrolling")
            for (index, rect) in grid.frames.enumerated() {
                check(rect.minX >= 0 && rect.minY >= 0 && rect.maxX <= size.width + 0.001 && rect.maxY <= size.height + 0.001, "no clipping")
                check(rect.height >= 44 && rect.width >= 44, "hit target")
                for other in grid.frames.dropFirst(index + 1) {
                    check(!rect.intersects(other), "no overlap")
                }
            }
            check(grid.frames[10].minX == grid.frames[6].minX && grid.frames[10].minY > grid.frames[6].minY, "pull quote below date")
            check(grid.frames[11].minX == grid.frames[7].minX && grid.frames[11].minY > grid.frames[7].minY, "select all below strike")
            if landscape {
                let visual = grid.frames.indices.sorted {
                    let a = grid.frames[$0], b = grid.frames[$1]
                    return a.minY == b.minY ? a.minX < b.minX : a.minY < b.minY
                }
                check(visual == [0,1,2,3,6,7,4,5,8,9,10,11], "approved landscape action order")
            }
        }
        let large = NagramiXFormattingGrid.layout(size: CGSize(width: 304, height: 100), count: 10,
            minimumLabelWidth: 150, minimumKeyHeight: 70, accessibility: true, footerMinimumLabelWidth: 170, landscape: true)
        check(large.columns == 1 && large.contentSize.height > 100, "large type remains accessible by scrolling")
        for size in [CGSize(width: 0,height: 1), CGSize(width: CGFloat.nan,height: 10), CGSize(width: 100,height: -1)] {
            check(NagramiXFormattingGrid.layout(size: size, count: 10, minimumLabelWidth: 0,
                minimumKeyHeight: 44, accessibility: false).frames.isEmpty, "invalid geometry")
        }
        print("PASS: \(checks) actual adaptive geometry checks; portrait/landscape, action identity, accessibility")
    }
}
