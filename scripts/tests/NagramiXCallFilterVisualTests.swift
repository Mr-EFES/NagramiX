@main private struct Tests {
    static func main() {
        for width: CGFloat in [280,320,384,430,768] {
            for heights: (CGFloat,CGFloat) in [(34,17),(51,34),(17,51),(80,90)] {
                for mode in [Calls.Mode.tab, .navigation] {
                    ImmediateTextNode.measuredHeights["all calls"] = heights.0
                    ImmediateTextNode.measuredHeights["missed calls"] = heights.1
                    let calls = Calls()
                    calls.mode = mode
                    var layout = ContainerViewLayout(); layout.size.width = width
                    if width == 768 { layout.safeInsets.left = 72 }
                    calls.containerLayout = (layout,90)
                    calls.show(.all)
                    let duck = calls.emptyAnimationNode.frame
                    let button = calls.emptyButtonNode.frame
                    let animationCount = calls.animations
                    calls.updateType(.missed)
                    expect(calls.emptyStatePromise.values.isEmpty, "switch filter must not expose synthetic new-call row")
                    calls.show(.missed)
                    expect(calls.emptyAnimationNode.frame == duck, "all and missed reserve same duck position")
                    expect(calls.emptyButtonNode.frame == button, "all and missed reserve same new-call action position")
                    expect(calls.emptyTextNode.frame.midY == duck.maxY + 13 + max(heights.0,heights.1) / 2, "text centered in shared measured band")
                    expect(calls.animations == animationCount, "same empty state must not restart fade")
                    expect(calls.listNode.alpha == 0 && calls.emptyAnimationNode.visibility, "empty remains visible while filter changes")
                    expect(calls.emptyTextNode.frame.maxY <= calls.emptyButtonNode.frame.minY, "localized multiline placeholder does not overlap action")
                    calls.currentLocationAndType.scope = .all
                    calls.show(.missed)
                    expect(calls.emptyTextNode.attributedText?.string == "missed calls", "placeholder honors supplied filter")
                    calls.show(.all,hidden:true)
                    expect(calls.listNode.alpha == 1 && !calls.emptyButtonNode.isUserInteractionEnabled, "nonempty list uses existing visibility contract")
                }
            }
        }
        let calls = Calls(); calls.show(.all)
        let count = calls.animations
        for _ in 0 ..< 10 { calls.updateType(.missed); calls.show(.missed); calls.updateType(.all); calls.show(.all) }
        expect(calls.animations == count && calls.emptyStatePromise.values.isEmpty, "rapid empty filter toggles remain stable")
        print("Call filter visual consistency: \(assertions) actual-body checks passed; text measurement and UIKit are explicit IO hosts")
    }
}
