import Foundation
import UIKit
import Display
import TelegramPresentationData
import ComponentFlow
import GlassBackgroundComponent
import HorizontalTabsComponent

public final class NagramiXItemListControllerSegmentedTitleView: UIView {
    private let backgroundContainer: GlassBackgroundContainerView
    private let backgroundView: GlassBackgroundView
    private let tabSelector = ComponentView<Empty>()
    private let fillsAvailableWidth: Bool
    private var expandedContentFrame: CGRect?
    
    public var theme: PresentationTheme {
        didSet {
            if self.theme !== oldValue {
                self.setNeedsLayout()
            }
        }
    }
    public var segments: [String] {
        didSet {
            if self.segments != oldValue {
                self.setNeedsLayout()
            }
        }
    }
    
    public var index: Int {
        didSet {
            if self.index != oldValue {
                self.animateLayout = true
                self.setNeedsLayout()
            }
        }
    }
    
    private var validLayout: CGSize?
    private var animateLayout: Bool = false
    
    public var indexUpdated: ((Int) -> Void)?
    
    public init(theme: PresentationTheme, segments: [String], selectedIndex: Int, fillsAvailableWidth: Bool = false) {
        self.theme = theme
        self.segments = segments
        self.index = selectedIndex
        self.fillsAvailableWidth = fillsAvailableWidth
        
        self.backgroundContainer = GlassBackgroundContainerView()
        self.backgroundView = GlassBackgroundView()
        
        super.init(frame: CGRect())
        
        self.clipsToBounds = !self.fillsAvailableWidth
        self.addSubview(self.backgroundContainer)
        self.backgroundContainer.contentView.addSubview(self.backgroundView)

        if self.fillsAvailableWidth {
            self.setContentHuggingPriority(.defaultLow, for: .horizontal)
            self.setContentCompressionResistancePriority(.defaultLow, for: .horizontal)
        }
    }
    
    required public init?(coder aDecoder: NSCoder) {
        fatalError("init(coder:) has not been implemented")
    }
    
    override public var intrinsicContentSize: CGSize {
        if self.fillsAvailableWidth {
            return CGSize(width: UIView.noIntrinsicMetric, height: 44.0)
        }
        return super.intrinsicContentSize
    }

    override public func sizeThatFits(_ size: CGSize) -> CGSize {
        if self.fillsAvailableWidth {
            return CGSize(width: size.width, height: 44.0)
        }
        return super.sizeThatFits(size)
    }

    override public func layoutSubviews() {
        super.layoutSubviews()
        
        let size = self.bounds.size
        self.validLayout = size
        self.update(transition: .immediate)
    }
    
    override public func point(inside point: CGPoint, with event: UIEvent?) -> Bool {
        if let expandedContentFrame = self.expandedContentFrame, expandedContentFrame.contains(point) {
            return true
        }
        return super.point(inside: point, with: event)
    }

    private func update(transition: ComponentTransition) {
        guard let size = self.validLayout else {
            return
        }

        var contentWidth = size.width
        if self.fillsAvailableWidth, let window = self.window {
            let windowFrame = self.convert(self.bounds, to: window)
            let trailingInset = max(16.0, window.safeAreaInsets.right)
            contentWidth = max(contentWidth, floor(window.bounds.width - windowFrame.minX - trailingInset))
        }
        
        let mappedItems: [NagramiXHorizontalTabsComponent.Tab] = zip(0 ..< self.segments.count, self.segments).map { index, segment in
            return NagramiXHorizontalTabsComponent.Tab(
                id: AnyHashable(index),
                content: .title(NagramiXHorizontalTabsComponent.Tab.Title(text: segment, entities: [], enableAnimations: false, isBold: self.fillsAvailableWidth)),
                badge: nil,
                action: { [weak self] in
                    guard let self else {
                        return
                    }
                    self.indexUpdated?(index)
                },
                contextAction: nil,
                deleteAction: nil
            )
        }
        
        var transition = transition
        if self.animateLayout {
            transition = .spring(duration: 0.4)
            self.animateLayout = false
        }
        
        let tabSelectorSize = self.tabSelector.update(
            transition: transition,
            component: AnyComponent(NagramiXHorizontalTabsComponent(
                context: nil,
                theme: self.theme,
                tabs: mappedItems,
                selectedTab: AnyHashable(self.index),
                isEditing: false,
                layout: self.fillsAvailableWidth ? .equal : .fit
            )),
            environment: {},
            containerSize: CGSize(width: contentWidth, height: 44.0)
        )
        
        let tabSelectorFrame = CGRect(origin: CGPoint(x: self.fillsAvailableWidth ? 0.0 : floor((size.width - tabSelectorSize.width) / 2.0), y: floor((size.height - tabSelectorSize.height) / 2.0)), size: tabSelectorSize)
        self.expandedContentFrame = tabSelectorFrame
        
        transition.setFrame(view: self.backgroundContainer, frame: tabSelectorFrame)
        self.backgroundContainer.update(size: tabSelectorFrame.size, isDark: self.theme.overallDarkAppearance, transition: transition)
        
        transition.setFrame(view: self.backgroundView, frame: CGRect(origin: CGPoint(), size: tabSelectorFrame.size))
        self.backgroundView.update(size: tabSelectorFrame.size, cornerRadius: tabSelectorFrame.height * 0.5, isDark: theme.overallDarkAppearance, tintColor: .init(kind: .panel), transition: transition)
        
        if let tabSelectorView = self.tabSelector.view as? NagramiXHorizontalTabsComponent.View {
            if tabSelectorView.superview == nil {
                self.backgroundView.contentView.addSubview(tabSelectorView)
                tabSelectorView.setOverlayContainerView(overlayContainerView: self)
            }
            transition.setFrame(view: tabSelectorView, frame: CGRect(origin: CGPoint(), size: tabSelectorFrame.size))
        }
    }
}
