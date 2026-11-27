import Foundation
#if canImport(CoreGraphics)
import CoreGraphics
#endif

func floorToScreenPixels(_ value: CGFloat) -> CGFloat { floor(value * 3) / 3 }
struct UIEdgeInsets { var left: CGFloat = 0; var right: CGFloat = 0; static let zero = Self() }
class UIView {
    var frame = CGRect.zero
    var isHidden = false
    weak var superview: UIView?
    func addSubview(_ child: UIView) { child.superview = self }
}
struct ContainedViewLayoutTransition {
    static let immediate = Self()
    func updateFrame(view: UIView, frame: CGRect) { view.frame = frame }
}
struct ComponentTransition {
    static let immediate = Self(.immediate)
    init(_ transition: ContainedViewLayoutTransition) {}
    func setFrame(view: UIView, frame: CGRect) { view.frame = frame }
}
final class Label: UIView {
    var textWidth: CGFloat = 0
    func measure(_ size: CGSize) -> CGSize {
        CGSize(width: min(textWidth, size.width), height: textWidth == 0 ? 0 : 15)
    }
}
final class Glass: UIView {
    let contentView = UIView()
    enum Kind { case panel }
    struct Tint { let kind: Kind }
    func update(size: CGSize, isDark: Bool, transition: ComponentTransition) {}
    func update(size: CGSize, cornerRadius: CGFloat, isDark: Bool, tintColor: Tint, isInteractive: Bool = false, transition: ComponentTransition) {}
}
extension CGSize {
    func centered(in frame: CGRect) -> CGRect {
        CGRect(x: frame.midX - width / 2, y: frame.midY - height / 2, width: width, height: height)
    }
}
final class Counter {
    let view: UIView? = UIView()
    var textWidth: CGFloat = 0
    func measure(_ size: CGSize) -> CGSize { CGSize(width: min(size.width, textWidth), height: 16) }
}
protocol NavigationBarTitleView: UIView {
    var alignedContentInsets: UIEdgeInsets? { get }
    func updateLayout(availableSize: CGSize, transition: ContainedViewLayoutTransition) -> CGSize
}
final class GalleryTitleView: UIView, NavigationBarTitleView {
    var alignedContentInsets: UIEdgeInsets?
    let authorNameNode = Label(), dateNode = Label()
    let backgroundContainer = Glass(), backgroundView = Glass(), titleBackgroundContainer = Glass(), titleBackground = Glass()
    let title = Counter()
    struct Content { var action: (() -> Void)? }
    var content: Content?
    func setContent(content: Content?) { self.content = content }
    var titleString: String? = "3 из 20"
    // PRODUCTION_TITLE
}
struct NavigationBarComponent {
    struct View {
        let primaryLeftButtonsWidth: CGFloat
        let primaryRightButtonsWidth: CGFloat
    }
}
final class NavigationBarNode {
    static let nominalHeight: CGFloat = 60
    var titleView: UIView?
    var trailingButtonsInset: CGFloat = 0
    struct Layout { let size: CGSize; let leftInset: CGFloat; let rightInset: CGFloat }
    // PRODUCTION_NAVIGATION
}
// PRODUCTION_PLACEMENT

final class NavigationItem {
    var title = "3 / 20"
    var titleAssignments = 0
    var titleView: UIView? { didSet { titleAssignments += 1 } }
}
final class GalleryHeaderBinding {
    let navigationItem = NavigationItem()
    let titleView = GalleryTitleView()
    func update(_ content: GalleryTitleView.Content?) {
        let changed: (GalleryTitleView.Content?) -> Void = { [weak self] titleContent in
            // PRODUCTION_BINDING
        }
        changed(content)
    }
}

@main enum HeaderTests {
    static func main() {
        let binding = GalleryHeaderBinding()
        binding.update(nil)
        precondition(binding.navigationItem.titleAssignments == 0)
        binding.update(.init(action: nil))
        binding.update(.init(action: nil))
        precondition(binding.navigationItem.titleView === binding.titleView && binding.navigationItem.titleAssignments == 1)
        binding.update(nil)
        precondition(binding.navigationItem.titleView == nil && binding.navigationItem.title == "3 / 20")
        let title = binding.titleView
        let bar = NavigationBarNode()
        bar.titleView = title
        title.alignedContentInsets = .zero
        var cases = 0
        for (width, safeLeft, safeRight, island) in [(320, 0, 0, 0), (393, 0, 0, 0), (852, 59, 59, 0), (744, 42, 8, 23)] {
            let layout = NavigationBarNode.Layout(size: CGSize(width: width, height: 88), leftInset: CGFloat(safeLeft), rightInset: CGFloat(safeRight))
            bar.trailingButtonsInset = CGFloat(island)
            // Reuse the same visible header while the bar adds/removes actions and the device rotates.
            for right in [44, 88, 168, 240, 300, 44] {
                for length: CGFloat in [0, 55, 360] {
                    title.authorNameNode.textWidth = length
                    title.dateNode.textWidth = 66
                    title.title.textWidth = 180
                    let row = NavigationBarComponent.View(primaryLeftButtonsWidth: 44, primaryRightButtonsWidth: CGFloat(right))
                    bar.layoutTitleView(layout: layout, rowView: row, contentVerticalOrigin: 36, transition: .immediate)
                    let leftEdge = CGFloat(safeLeft + 16 + 44)
                    let rightEdge = CGFloat(width - safeRight - island - 16 - right)
                    if rightEdge - leftEdge <= 16 {
                        precondition(title.isHidden && title.frame.width == 0)
                    } else {
                        precondition(!title.isHidden && title.frame.minX >= leftEdge + 8 && title.frame.maxX <= rightEdge - 8)
                        for frame in [title.backgroundContainer.frame, title.titleBackgroundContainer.frame] {
                            precondition(frame.minX >= 0 && frame.maxX <= title.frame.width)
                        }
                        for frame in [title.authorNameNode.frame, title.dateNode.frame] {
                            precondition(frame.minX >= 0 && frame.maxX <= title.backgroundContainer.frame.width)
                        }
                        precondition(title.titleBackgroundContainer.frame.minY >= title.backgroundContainer.frame.maxY)
                    }
                    cases += 1
                }
            }
        }
        print("\(cases) gallery header layouts passed")
    }
}
