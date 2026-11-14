import Foundation
import UIKit
import Display
import AsyncDisplayKit
import SwiftSignalKit
import TelegramCore
import TelegramPresentationData
import LegacyComponents
import ItemListUI
import PresentationDataUtils
import NagramiXCore

class NagramiXSnowDensityItem: ListViewItem, ItemListItem {
    let presentationData: ItemListPresentationData
    let title: String
    var theme: PresentationTheme { self.presentationData.theme }
    let value: Int
    let sectionId: ItemListSectionId
    let updated: (Int) -> Void

    init(presentationData: ItemListPresentationData, title: String, value: Int, sectionId: ItemListSectionId, updated: @escaping (Int) -> Void) {
        self.presentationData = presentationData
        self.title = title
        self.value = value
        self.sectionId = sectionId
        self.updated = updated
    }

    func nodeConfiguredForParams(async: @escaping (@escaping () -> Void) -> Void, params: ListViewItemLayoutParams, synchronousLoads: Bool, neighbors: ListViewItemNeighbors, completion: @escaping (ListViewItemNode, @escaping () -> (Signal<Void, NoError>?, (ListViewItemApply) -> Void)) -> Void) {
        async {
            let node = NagramiXSnowDensityItemNode()
            let (layout, apply) = node.asyncLayout()(self, params, itemListNeighbors(item: self, topFacet: neighbors.previous?.base(ItemListNeighborFacet.self), bottomFacet: neighbors.next?.base(ItemListNeighborFacet.self)))

            node.contentSize = layout.contentSize
            node.insets = layout.insets

            Queue.mainQueue().async {
                completion(node, {
                    return (nil, { _ in apply() })
                })
            }
        }
    }

    func updateNode(async: @escaping (@escaping () -> Void) -> Void, node: @escaping () -> ListViewItemNode, params: ListViewItemLayoutParams, neighbors: ListViewItemNeighbors, animation: ListViewItemUpdateAnimation, completion: @escaping (ListViewItemNodeLayout, @escaping (ListViewItemApply) -> Void) -> Void) {
        Queue.mainQueue().async {
            if let nodeValue = node() as? NagramiXSnowDensityItemNode {
                let makeLayout = nodeValue.asyncLayout()

                async {
                    let (layout, apply) = makeLayout(self, params, itemListNeighbors(item: self, topFacet: neighbors.previous?.base(ItemListNeighborFacet.self), bottomFacet: neighbors.next?.base(ItemListNeighborFacet.self)))
                    Queue.mainQueue().async {
                        completion(layout, { _ in
                            apply()
                        })
                    }
                }
            }
        }
    }
}

class NagramiXSnowDensityItemNode: ListViewItemNode {
    private let backgroundNode: ASDisplayNode
    private let topStripeNode: ASDisplayNode
    private let bottomStripeNode: ASDisplayNode
    private let maskNode: ASImageNode

    private var sliderView: NagramiXSnowDensitySliderView?
    private let titleLabel = UILabel()
    private let minimumLabel = UILabel()
    private let valueLabel = UILabel()
    private let maximumLabel = UILabel()
    private var isInteracting = false

    private var item: NagramiXSnowDensityItem?
    private var layoutParams: ListViewItemLayoutParams?

    init() {
        self.backgroundNode = ASDisplayNode()
        self.backgroundNode.isLayerBacked = true

        self.topStripeNode = ASDisplayNode()
        self.topStripeNode.isLayerBacked = true

        self.bottomStripeNode = ASDisplayNode()
        self.bottomStripeNode.isLayerBacked = true

        self.maskNode = ASImageNode()

        super.init(layerBacked: false)
    }

    override func didLoad() {
        super.didLoad()

        let sliderView = NagramiXSnowDensitySliderView()
        sliderView.enablePanHandling = true
        sliderView.trackCornerRadius = 1.0
        sliderView.lineSize = 2.0
        sliderView.minimumValue = 0.0
        sliderView.startValue = 0.0
        sliderView.maximumValue = 90.0
        sliderView.disablesInteractiveTransitionGestureRecognizer = true
        sliderView.isAccessibilityElement = true
        sliderView.accessibilityTraits = .adjustable
        sliderView.interactionBegan = { [weak self] in self?.isInteracting = true }
        sliderView.interactionEnded = { [weak self] in
            guard let self else { return }
            self.isInteracting = false
            self.commitValue()
        }
        self.view.addSubview(sliderView)
        self.titleLabel.numberOfLines = 0
        self.view.addSubview(self.titleLabel)
        self.view.addSubview(self.minimumLabel)
        self.view.addSubview(self.valueLabel)
        self.view.addSubview(self.maximumLabel)
        self.minimumLabel.text = "10%"
        self.maximumLabel.text = "100%"
        self.maximumLabel.textAlignment = .right
        self.valueLabel.textAlignment = .center
        sliderView.addTarget(self, action: #selector(self.sliderValueChanged), for: .valueChanged)
        self.sliderView = sliderView
        self.updateControls()
    }

    private func headerHeight(item: NagramiXSnowDensityItem, params: ListViewItemLayoutParams) -> CGFloat {
        let scale = item.presentationData.fontSize.baseDisplaySize / 17.0
        let available = NagramiXSnowDensityGeometry(width: params.width, leftInset: params.leftInset, rightInset: params.rightInset).width
        let valueWidth = ceil(("100%" as NSString).size(withAttributes: [.font: Font.regular(17.0 * scale)]).width)
        let stacked = valueWidth + 96.0 * scale > available
        let width = stacked ? available : max(1.0, available - valueWidth - 8.0)
        let size = (item.title as NSString).boundingRect(with: CGSize(width: width, height: CGFloat.greatestFiniteMagnitude), options: [.usesLineFragmentOrigin, .usesFontLeading], attributes: [.font: Font.regular(17.0 * scale)], context: nil).size
        return max(ceil(24.0 * scale), ceil(size.height)) + (stacked ? ceil(24.0 * scale) + 4.0 : 0.0)
    }

    private func updateControls() {
        guard let item = self.item, let params = self.layoutParams, let sliderView = self.sliderView else { return }
        let scale = item.presentationData.fontSize.baseDisplaySize / 17.0
        let height = self.headerHeight(item: item, params: params)
        let geometry = NagramiXSnowDensityGeometry(width: params.width, leftInset: params.leftInset, rightInset: params.rightInset)
        let left = geometry.left
        let right = geometry.right
        let available = max(1.0, right - left)
        let valueWidth = min(available, ceil(("100%" as NSString).size(withAttributes: [.font: Font.regular(17.0 * scale)]).width))
        let stacked = valueWidth + 96.0 * scale > available
        let titleHeight = height - (stacked ? ceil(24.0 * scale) + 4.0 : 0.0)
        self.titleLabel.text = item.title
        self.titleLabel.font = Font.regular(17.0 * scale)
        self.titleLabel.textColor = item.theme.list.itemPrimaryTextColor
        self.titleLabel.frame = CGRect(x: left, y: 8.0, width: stacked ? available : max(1.0, available - valueWidth - 8.0), height: titleHeight)
        self.valueLabel.font = self.titleLabel.font
        self.valueLabel.textColor = item.theme.list.itemSecondaryTextColor
        self.valueLabel.textAlignment = .right
        self.valueLabel.frame = CGRect(x: right - valueWidth, y: stacked ? titleHeight + 12.0 : 8.0, width: valueWidth, height: ceil(24.0 * scale))
        self.minimumLabel.font = Font.regular(14.0 * scale)
        self.maximumLabel.font = self.minimumLabel.font
        self.minimumLabel.textColor = item.theme.list.itemSecondaryTextColor
        self.maximumLabel.textColor = item.theme.list.itemSecondaryTextColor
        let sideWidth = min((right - left) / 2.0, 90.0 * scale)
        self.minimumLabel.frame = CGRect(x: left, y: height + 58.0, width: sideWidth, height: ceil(22.0 * scale))
        self.maximumLabel.frame = CGRect(x: right - sideWidth, y: height + 58.0, width: sideWidth, height: ceil(22.0 * scale))
        sliderView.backgroundColor = item.theme.list.itemBlocksBackgroundColor
        sliderView.updateAppearance(isDark: item.theme.overallDarkAppearance, background: item.theme.list.itemSwitchColors.frameColor, foreground: item.theme.list.itemAccentColor)
        sliderView.accessibilityLabel = item.title
        sliderView.frame = geometry.sliderFrame(headerHeight: height)
        if !self.isInteracting { sliderView.density = item.value }
        self.updateValueLabel()
    }

    private func updateValueLabel() {
        guard let sliderView = self.sliderView else { return }
        let text = "\(sliderView.density)%"
        self.valueLabel.text = text
        sliderView.accessibilityValue = text
    }

    private func commitValue() {
        guard let item = self.item, let sliderView = self.sliderView else { return }
        let value = sliderView.density
        if value != item.value { item.updated(value) }
    }

    func asyncLayout() -> (_ item: NagramiXSnowDensityItem, _ params: ListViewItemLayoutParams, _ neighbors: ItemListNeighbors) -> (ListViewItemNodeLayout, () -> Void) {
        return { [self] item, params, neighbors in
            let contentSize: CGSize
            let insets: UIEdgeInsets
            let separatorHeight = UIScreenPixel

            contentSize = CGSize(width: params.width, height: self.headerHeight(item: item, params: params) + 66.0 + ceil(22.0 * item.presentationData.fontSize.baseDisplaySize / 17.0))
            insets = itemListNeighborsGroupedInsets(neighbors, params)

            let layout = ListViewItemNodeLayout(contentSize: contentSize, insets: insets)
            let layoutSize = layout.size

            return (layout, { [weak self] in
                if let strongSelf = self {
                    strongSelf.item = item
                    strongSelf.layoutParams = params

                    strongSelf.backgroundNode.backgroundColor = item.theme.list.itemBlocksBackgroundColor
                    strongSelf.topStripeNode.backgroundColor = item.theme.list.itemBlocksSeparatorColor
                    strongSelf.bottomStripeNode.backgroundColor = item.theme.list.itemBlocksSeparatorColor

                    if strongSelf.backgroundNode.supernode == nil {
                        strongSelf.insertSubnode(strongSelf.backgroundNode, at: 0)
                    }
                    if strongSelf.topStripeNode.supernode == nil {
                        strongSelf.insertSubnode(strongSelf.topStripeNode, at: 1)
                    }
                    if strongSelf.bottomStripeNode.supernode == nil {
                        strongSelf.insertSubnode(strongSelf.bottomStripeNode, at: 2)
                    }
                    if strongSelf.maskNode.supernode == nil {
                        strongSelf.insertSubnode(strongSelf.maskNode, at: 3)
                    }

                    let hasCorners = itemListHasRoundedBlockLayout(params)
                    var hasTopCorners = false
                    var hasBottomCorners = false
                    switch neighbors.top {
                    case .sameSection(false):
                        strongSelf.topStripeNode.isHidden = true
                    default:
                        hasTopCorners = true
                        strongSelf.topStripeNode.isHidden = hasCorners
                    }
                    let bottomStripeInset: CGFloat
                    let bottomStripeOffset: CGFloat
                    switch neighbors.bottom {
                        case .sameSection(false):
                            bottomStripeInset = params.leftInset + 16.0
                            bottomStripeOffset = -separatorHeight
                            strongSelf.bottomStripeNode.isHidden = false
                        default:
                            bottomStripeInset = 0.0
                            bottomStripeOffset = 0.0
                            hasBottomCorners = true
                            strongSelf.bottomStripeNode.isHidden = hasCorners
                    }

                    strongSelf.maskNode.image = hasCorners ? PresentationResourcesItemList.cornersImage(item.theme, top: hasTopCorners, bottom: hasBottomCorners) : nil

                    strongSelf.backgroundNode.frame = CGRect(origin: CGPoint(x: 0.0, y: -min(insets.top, separatorHeight)), size: CGSize(width: params.width, height: contentSize.height + min(insets.top, separatorHeight) + min(insets.bottom, separatorHeight)))
                    strongSelf.maskNode.frame = strongSelf.backgroundNode.frame.insetBy(dx: params.leftInset, dy: 0.0)
                    strongSelf.topStripeNode.frame = CGRect(origin: CGPoint(x: 0.0, y: -min(insets.top, separatorHeight)), size: CGSize(width: layoutSize.width, height: separatorHeight))
                    strongSelf.bottomStripeNode.frame = CGRect(origin: CGPoint(x: bottomStripeInset, y: contentSize.height + bottomStripeOffset), size: CGSize(width: layoutSize.width - bottomStripeInset, height: separatorHeight))

                    strongSelf.updateControls()
                }
            })
        }
    }

    override func animateInsertion(_ currentTimestamp: Double, duration: Double, options: ListViewItemAnimationOptions) {
        self.layer.animateAlpha(from: 0.0, to: 1.0, duration: 0.4)
    }

    override func animateRemoved(_ currentTimestamp: Double, duration: Double) {
        self.layer.animateAlpha(from: 1.0, to: 0.0, duration: 0.15, removeOnCompletion: false)
    }

    @objc private func sliderValueChanged() {
        self.updateValueLabel()
        if !self.isInteracting { self.commitValue() }
    }
}

private struct NagramiXSnowDensityGeometry {
    static let thumbDiameter: CGFloat = 28.0
    // The native legacy control puts its thumb center 7pt from each edge.
    static let thumbInset: CGFloat = thumbDiameter * 0.5 - 7.0
    let left: CGFloat
    let right: CGFloat
    var width: CGFloat { max(1.0, self.right - self.left) }

    init(width: CGFloat, leftInset: CGFloat, rightInset: CGFloat) {
        self.left = leftInset + 16.0
        self.right = max(self.left + 1.0, width - rightInset - 15.0)
    }

    func sliderFrame(headerHeight: CGFloat) -> CGRect {
        return CGRect(x: self.left + Self.thumbInset, y: headerHeight + 14.0, width: max(1.0, self.width - Self.thumbInset * 2.0), height: 44.0)
    }
}

private final class NagramiXSnowDensityGlassThumbView: UIView {
    private let effectView: UIVisualEffectView?
    private let sheenLayer = CAGradientLayer()
    private let rimLayer = CAShapeLayer()
    private var currentIsDark: Bool?

    override init(frame: CGRect) {
        if #available(iOS 26.0, *) {
            let effect = UIGlassEffect(style: .clear)
            effect.isInteractive = false
            self.effectView = UIVisualEffectView(effect: effect)
        } else {
            self.effectView = nil
        }
        super.init(frame: frame)
        self.isOpaque = false
        self.isUserInteractionEnabled = false
        self.isAccessibilityElement = false
        self.accessibilityElementsHidden = true
        if let effectView = self.effectView {
            effectView.isUserInteractionEnabled = false
            effectView.clipsToBounds = true
            self.addSubview(effectView)
        }
        self.sheenLayer.startPoint = CGPoint(x: 0.15, y: 0.0)
        self.sheenLayer.endPoint = CGPoint(x: 0.85, y: 1.0)
        self.sheenLayer.masksToBounds = true
        self.sheenLayer.locations = [0.0, 0.38, 0.7, 1.0]
        self.layer.addSublayer(self.sheenLayer)
        self.rimLayer.fillColor = UIColor.clear.cgColor
        self.rimLayer.lineWidth = 0.7
        self.layer.addSublayer(self.rimLayer)
        self.layer.shadowColor = UIColor.black.cgColor
        self.layer.shadowOffset = CGSize(width: 0.0, height: 1.0)
        self.layer.shadowRadius = 2.0
        self.update(isDark: true)
    }

    required init?(coder: NSCoder) {
        return nil
    }

    func update(isDark: Bool) {
        guard self.currentIsDark != isDark else { return }
        self.currentIsDark = isDark
        self.effectView?.overrideUserInterfaceStyle = isDark ? .dark : .light
        // The center remains transparent, including the older-system fallback.
        self.backgroundColor = UIColor(white: isDark ? 1.0 : 0.0, alpha: 0.025)
        self.sheenLayer.colors = [0.18, 0.015, 0.0, 0.12].map { UIColor(white: 1.0, alpha: $0).cgColor }
        self.rimLayer.strokeColor = UIColor(white: 1.0, alpha: isDark ? 0.7 : 0.9).cgColor
        self.layer.shadowOpacity = isDark ? 0.3 : 0.18
    }

    override func layoutSubviews() {
        super.layoutSubviews()
        guard self.bounds.width > 1.0, self.bounds.height > 1.0 else { return }
        CATransaction.begin()
        CATransaction.setDisableActions(true)
        let radius = min(self.bounds.width, self.bounds.height) * 0.5
        self.layer.cornerRadius = radius
        self.effectView?.frame = self.bounds
        self.effectView?.layer.cornerRadius = radius
        self.sheenLayer.frame = self.bounds
        self.sheenLayer.cornerRadius = radius
        self.rimLayer.frame = self.bounds
        self.rimLayer.path = UIBezierPath(ovalIn: self.bounds.insetBy(dx: 0.5, dy: 0.5)).cgPath
        self.layer.shadowPath = UIBezierPath(ovalIn: self.bounds).cgPath
        CATransaction.commit()
    }
}

private final class NagramiXSnowDensitySliderView: TGPhotoEditorSliderView {
    private let glassThumbView = NagramiXSnowDensityGlassThumbView(frame: .zero)
    private let trackBackgroundView = UIView()
    private let trackForegroundView = UIView()

    // A zero-based native range avoids the legacy control's positive-minimum
    // geometry. Only this adapter is zero-based; stored/displayed values stay 10...100.
    var density: Int {
        get { NagramiXSnowSettings.normalizedDensity(Int(self.value.rounded()) + 10) }
        set { self.value = CGFloat(NagramiXSnowSettings.normalizedDensity(newValue) - 10) }
    }

    private static let clearKnobImage: UIImage = {
        let size = CGSize(width: NagramiXSnowDensityGeometry.thumbDiameter, height: NagramiXSnowDensityGeometry.thumbDiameter)
        let format = UIGraphicsImageRendererFormat()
        format.opaque = false
        return UIGraphicsImageRenderer(size: size, format: format).image { context in
            context.cgContext.clear(CGRect(origin: .zero, size: size))
        }
    }()

    override init(frame: CGRect) {
        super.init(frame: frame)
        self.configureGlass()
    }

    required init?(coder: NSCoder) {
        super.init(coder: coder)
        self.configureGlass()
    }

    private func configureGlass() {
        self.isOpaque = false
        self.clipsToBounds = false
        self.backColor = .clear
        self.trackColor = .clear
        self.startColor = .clear
        self.knobImage = Self.clearKnobImage
        self.trackBackgroundView.isUserInteractionEnabled = false
        self.trackForegroundView.isUserInteractionEnabled = false
        self.trackBackgroundView.layer.cornerRadius = 1.0
        self.trackForegroundView.layer.cornerRadius = 1.0
        self.insertSubview(self.trackBackgroundView, at: 0)
        self.insertSubview(self.trackForegroundView, at: 1)
        self.knobView?.addSubview(self.glassThumbView)
        self.knobView?.clipsToBounds = false
    }

    func updateAppearance(isDark: Bool, background: UIColor, foreground: UIColor) {
        self.trackBackgroundView.backgroundColor = background
        self.trackForegroundView.backgroundColor = foreground
        self.glassThumbView.update(isDark: isDark)
    }

    override func layoutSubviews() {
        super.layoutSubviews()
        guard let knobView = self.knobView else { return }
        let inset = NagramiXSnowDensityGeometry.thumbInset
        let trackFrame = CGRect(x: -inset, y: floor((self.bounds.height - 2.0) * 0.5), width: self.bounds.width + inset * 2.0, height: 2.0)
        self.trackBackgroundView.frame = trackFrame
        let filledWidth: CGFloat
        if self.value <= self.minimumValue {
            filledWidth = 0.0
        } else if self.value >= self.maximumValue {
            filledWidth = trackFrame.width
        } else {
            filledWidth = max(0.0, min(trackFrame.width, knobView.frame.midX - trackFrame.minX))
        }
        self.trackForegroundView.frame = CGRect(x: trackFrame.minX, y: trackFrame.minY, width: filledWidth, height: trackFrame.height)
        self.glassThumbView.frame = knobView.bounds
    }

    override func point(inside point: CGPoint, with event: UIEvent?) -> Bool {
        return self.bounds.insetBy(dx: -NagramiXSnowDensityGeometry.thumbInset, dy: 0.0).contains(point)
    }

    override func accessibilityIncrement() {
        self.value = min(self.maximumValue, self.value + 5.0)
        self.sendActions(for: .valueChanged)
    }
    override func accessibilityDecrement() {
        self.value = max(self.minimumValue, self.value - 5.0)
        self.sendActions(for: .valueChanged)
    }
}
