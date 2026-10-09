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
import NagramiXMediaSettings

class NagramiXPercentageItem: ListViewItem, ItemListItem {
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
            let node = NagramiXPercentageItemNode()
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
            if let nodeValue = node() as? NagramiXPercentageItemNode {
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

class NagramiXPercentageItemNode: ListViewItemNode {
    private let backgroundNode: ASDisplayNode
    private let topStripeNode: ASDisplayNode
    private let bottomStripeNode: ASDisplayNode
    private let maskNode: ASImageNode

    private var sliderView: TGPhotoEditorSliderView?
    private let minimumLabel = UILabel()
    private let valueLabel = UILabel()
    private let maximumLabel = UILabel()
    private var isInteracting = false

    private var item: NagramiXPercentageItem?
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

        let sliderView = NagramiXPercentageSliderView()
        sliderView.enablePanHandling = true
        sliderView.trackCornerRadius = 1.0
        sliderView.lineSize = 2.0
        sliderView.minimumValue = 0.0
        sliderView.startValue = 0.0
        sliderView.maximumValue = 100.0
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
        self.view.addSubview(self.minimumLabel)
        self.view.addSubview(self.valueLabel)
        self.view.addSubview(self.maximumLabel)
        self.minimumLabel.text = "0%"
        self.maximumLabel.text = "100%"
        self.maximumLabel.textAlignment = .right
        self.valueLabel.textAlignment = .center
        sliderView.addTarget(self, action: #selector(self.sliderValueChanged), for: .valueChanged)
        self.sliderView = sliderView
        self.updateControls()
    }

    private func updateControls() {
        guard let item = self.item, let params = self.layoutParams, let sliderView = self.sliderView else { return }
        let fontScale = item.presentationData.fontSize.baseDisplaySize / 17.0
        let labelHeight = ceil(32.0 * fontScale)
        self.minimumLabel.font = Font.regular(16.0 * fontScale)
        self.maximumLabel.font = self.minimumLabel.font
        self.valueLabel.font = Font.regular(22.0 * fontScale)
        self.minimumLabel.textColor = item.theme.list.itemSecondaryTextColor
        self.maximumLabel.textColor = item.theme.list.itemSecondaryTextColor
        self.valueLabel.textColor = item.theme.list.itemPrimaryTextColor
        let left = params.leftInset + 24.0
        let right = params.width - params.rightInset - 24.0
        let sideWidth = min((right - left) / 3.0, 90.0 * fontScale)
        self.minimumLabel.frame = CGRect(x: left, y: 8.0, width: sideWidth, height: labelHeight)
        self.maximumLabel.frame = CGRect(x: right - sideWidth, y: 8.0, width: sideWidth, height: labelHeight)
        self.valueLabel.frame = CGRect(x: left + sideWidth, y: 8.0, width: max(1.0, right - left - sideWidth * 2.0), height: labelHeight)
        sliderView.backgroundColor = item.theme.list.itemBlocksBackgroundColor
        sliderView.backColor = item.theme.list.itemSwitchColors.frameColor
        sliderView.trackColor = item.theme.list.itemAccentColor
        sliderView.knobImage = PresentationResourcesItemList.knobImage(item.theme)
        sliderView.accessibilityLabel = item.title
        sliderView.frame = CGRect(x: left, y: labelHeight + 12.0, width: max(1.0, right - left), height: 44.0)
        if !self.isInteracting { sliderView.value = CGFloat(item.value) }
        self.updateValueLabel()
    }

    private func updateValueLabel() {
        guard let sliderView = self.sliderView else { return }
        let text = "\(NagramiXMediaSettings.normalizedPercentage(Int(sliderView.value.rounded())))%"
        self.valueLabel.text = text
        sliderView.accessibilityValue = text
    }

    private func commitValue() {
        guard let item = self.item, let sliderView = self.sliderView else { return }
        let value = NagramiXMediaSettings.normalizedPercentage(Int(sliderView.value.rounded()))
        if value != item.value { item.updated(value) }
    }

    func asyncLayout() -> (_ item: NagramiXPercentageItem, _ params: ListViewItemLayoutParams, _ neighbors: ItemListNeighbors) -> (ListViewItemNodeLayout, () -> Void) {
        return { item, params, neighbors in
            let contentSize: CGSize
            let insets: UIEdgeInsets
            let separatorHeight = UIScreenPixel

            contentSize = CGSize(width: params.width, height: ceil(32.0 * item.presentationData.fontSize.baseDisplaySize / 17.0) + 64.0)
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

private final class NagramiXPercentageSliderView: TGPhotoEditorSliderView {
    override func accessibilityIncrement() {
        self.value = min(self.maximumValue, self.value + 5.0)
        self.sendActions(for: .valueChanged)
    }
    override func accessibilityDecrement() {
        self.value = max(self.minimumValue, self.value - 5.0)
        self.sendActions(for: .valueChanged)
    }
}
