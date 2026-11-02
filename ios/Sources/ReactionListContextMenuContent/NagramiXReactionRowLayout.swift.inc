// Frames for measured names followed by the native, unloaded placeholder tail.
// Only loaded peers are measured; scrolling uses binary search over these frames.
private struct NagramiXReactionRowLayout {
    private let offsets: [CGFloat]
    let count: Int
    let placeholderHeight: CGFloat
    let topInset: CGFloat

    init(heights: [CGFloat] = [], count: Int = 0, placeholderHeight: CGFloat = 44.0, topInset: CGFloat = 5.0) {
        self.count = max(0, count)
        self.placeholderHeight = max(1.0, placeholderHeight)
        self.topInset = max(0.0, topInset)
        var offsets: [CGFloat] = [0.0]
        for height in heights.prefix(self.count) {
            offsets.append(offsets[offsets.count - 1] + max(self.placeholderHeight, height))
        }
        self.offsets = offsets
    }

    private func offset(_ index: Int) -> CGFloat {
        let loadedCount = self.offsets.count - 1
        if index <= loadedCount { return self.offsets[index] }
        return self.offsets[loadedCount] + CGFloat(index - loadedCount) * self.placeholderHeight
    }

    var contentHeight: CGFloat { self.topInset * 2.0 + self.offset(self.count) }

    func frame(at index: Int, width: CGFloat) -> CGRect {
        precondition(index >= 0 && index < self.count)
        let y = self.offset(index)
        return CGRect(x: 0.0, y: self.topInset + y, width: max(0.0, width), height: self.offset(index + 1) - y)
    }

    func visibleRange(in bounds: CGRect) -> Range<Int> {
        var low = 0
        var high = self.count
        while low < high {
            let mid = low + (high - low) / 2
            if self.topInset + self.offset(mid + 1) < bounds.minY { low = mid + 1 }
            else { high = mid }
        }
        let first = low
        high = self.count
        while low < high {
            let mid = low + (high - low) / 2
            if self.topInset + self.offset(mid) <= bounds.maxY { low = mid + 1 }
            else { high = mid }
        }
        return first..<low
    }
}

private struct NagramiXReactionNameMeasureKey: Hashable {
    let text: String
    let width: CGFloat
    let fontSize: CGFloat
}
