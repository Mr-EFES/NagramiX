import Foundation
import UIKit
import Display
import TelegramPresentationData
import ComponentFlow
import ComponentDisplayAdapters
import GlassBackgroundComponent
import HorizontalTabsComponent

public final class NagramiXItemListControllerSegmentedTitleView: UIView, NavigationBarTitleView {
    private let backgroundContainer: GlassBackgroundContainerView
    private let backgroundView: GlassBackgroundView
    private let tabSelector = ComponentView<Empty>()
    private let fillsAvailableWidth: Bool
    
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
    
    private var animateLayout: Bool = false
    
    public var indexUpdated: ((Int) -> Void)?
    public var requestUpdate: ((ContainedViewLayoutTransition) -> Void)?
    public var alignedContentInsets: UIEdgeInsets?
    
    public init(theme: PresentationTheme, segments: [String], selectedIndex: Int, fillsAvailableWidth: Bool = false) {
        self.theme = theme
        self.segments = segments
        self.index = selectedIndex
        self.fillsAvailableWidth = fillsAvailableWidth
        
        self.backgroundContainer = GlassBackgroundContainerView()
        self.backgroundView = GlassBackgroundView()
        
        super.init(frame: CGRect())
        
        self.clipsToBounds = true
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
    
    override public func layoutSubviews() {
        super.layoutSubviews()
        let size = self.bounds.size
        self.update(availableWidth: size.width, containerSize: size, transition: .immediate)
    }

    public func updateLayout(availableSize: CGSize, transition: ContainedViewLayoutTransition) -> CGSize {
        return self.update(availableWidth: availableSize.width, containerSize: nil, transition: ComponentTransition(transition))
    }

    public func animateLayoutTransition() {
    }

    @discardableResult
    private func update(availableWidth: CGFloat, containerSize: CGSize?, transition: ComponentTransition) -> CGSize {
        let width = max(0.0, availableWidth)
        let height: CGFloat = self.fillsAvailableWidth ? 40.0 : 44.0
        self.backgroundContainer.isHidden = width <= 6.0
        guard !self.backgroundContainer.isHidden else {
            return CGSize(width: width, height: height)
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
            containerSize: CGSize(width: width, height: height)
        )

        let size = containerSize ?? tabSelectorSize
        let tabSelectorFrame = CGRect(origin: CGPoint(x: floorToScreenPixels((size.width - tabSelectorSize.width) * 0.5), y: floorToScreenPixels((size.height - tabSelectorSize.height) * 0.5)), size: tabSelectorSize)
        
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
        return tabSelectorSize
    }
}
