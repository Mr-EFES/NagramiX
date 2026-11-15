// The real Apple views are opaque here. These adapters record only visibility
// and lifecycle calls; CoreAnimation/rendering and navigation are not simulated.
final class StoryWeakReference<T: AnyObject> {
    weak var value: T?
    init(_ value: T?) { self.value = value }
}
public class UIView {
    var bounds = CGRect(x: 0, y: 0, width: 60, height: 60)
    var isHidden = false { didSet { visibilityWrites.append(isHidden) } }
    var disablesInteractiveModalDismiss = false
    var visibilityWrites: [Bool] = []
}
final class AvatarNode {
    let view = UIView()
    var isHidden: Bool {
        get { view.isHidden }
        set { view.isHidden = newValue }
    }
}
enum StoryContainerScreenComponent {
    final class View {
        private(set) var animationCount = 0
        func animateIn() { animationCount += 1 }
    }
}
final class HostView { let componentView: Any? = StoryContainerScreenComponent.View() }
final class Node { let hostView = HostView() }
