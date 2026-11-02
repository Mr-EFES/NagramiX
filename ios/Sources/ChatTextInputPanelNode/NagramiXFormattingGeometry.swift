import Foundation

/// Cache only full, stable system-keyboard heights. The custom input view must
/// never feed its own size (or a dragged/hidden keyboard) back into this cache.
struct NagramiXFormattingKeyboardGeometry {
    private var heights: [Int: CGFloat] = [:]
    private var recentWidths: [Int] = []
    private(set) var height: CGFloat?
    var cachedWidthCount: Int { self.heights.count }

    mutating func update(container: CGSize, keyboardHeight: CGFloat?, standardHeight: CGFloat,
                         canMeasureSystem: Bool, interactive: Bool) {
        guard container.width.isFinite, container.height.isFinite,
              container.width > 0, container.width <= 4096, container.height > 0, container.height <= 8192 else {
            self.height = nil
            return
        }
        let key = Int(container.width.rounded())
        func usable(_ value: CGFloat) -> Bool {
            return value.isFinite && value >= 120 && value <= container.height * 0.85
        }
        if canMeasureSystem && !interactive, let keyboardHeight, usable(keyboardHeight) {
            self.heights[key] = keyboardHeight
            self.recentWidths.removeAll(where: { $0 == key })
            self.recentWidths.append(key)
            if self.recentWidths.count > 4 {
                self.heights.removeValue(forKey: self.recentWidths.removeFirst())
            }
        }
        if let measured = self.heights[key], usable(measured) {
            self.height = measured
        } else {
            self.height = usable(standardHeight) ? standardHeight : nil
        }
    }
}

struct NagramiXFormattingGrid {
    let columns: Int
    let frames: [CGRect]
    let contentSize: CGSize

    static func layout(size: CGSize, count: Int, minimumLabelWidth: CGFloat,
                       minimumKeyHeight: CGFloat, accessibility: Bool) -> NagramiXFormattingGrid {
        guard size.width.isFinite, size.height.isFinite, size.width > 0, size.height >= 0,
              minimumLabelWidth.isFinite, minimumKeyHeight.isFinite, count > 0, count <= 100 else {
            return NagramiXFormattingGrid(columns: 0, frames: [], contentSize: .zero)
        }
        let gap: CGFloat = 6
        let labelInset: CGFloat = 4
        var columns = min(count, size.width >= 344 ? 5 : 4)
        let minimumColumns = accessibility ? 1 : min(2, count)
        while columns > minimumColumns {
            let width = (size.width - CGFloat(columns - 1) * gap) / CGFloat(columns)
            if width - labelInset >= minimumLabelWidth { break }
            columns -= 1
        }
        let rows = (count + columns - 1) / columns
        let width = max(0, (size.width - CGFloat(columns - 1) * gap) / CGFloat(columns))
        let height = max(60, minimumKeyHeight, (size.height - CGFloat(rows - 1) * gap) / CGFloat(rows))
        let frames = (0 ..< count).map { index in
            CGRect(x: CGFloat(index % columns) * (width + gap), y: CGFloat(index / columns) * (height + gap), width: width, height: height)
        }
        return NagramiXFormattingGrid(columns: columns, frames: frames,
            contentSize: CGSize(width: size.width, height: CGFloat(rows) * height + CGFloat(rows - 1) * gap))
    }
}
