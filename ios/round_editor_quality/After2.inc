import Foundation
import NagramiXCore
import UIKit
import Display
import ComponentFlow
import MediaPickerUI
import MediaEditorBottomControls
import LegacyComponents
import TelegramPresentationData

private let chatMediaEditorBottomControlsSendColor = UIColor(rgb: 0x0088ff)

final class ChatMediaEditorBottomControlsComponent: Component {
    typealias View = MediaEditorBottomControlsComponent.View

    let items: ChatMediaEditorBottomControlsItems
    let isHidden: Bool
    let isMiddleEnabled: Bool
    let areSideButtonsEnabled: Bool
    let isRightEnabled: Bool
    let infoString: String?
    let paintModeTitle: (ChatMediaEditorPaintTab) -> String
    let leftPressed: () -> Void
    let rightPressed: () -> Void
    let rightLongPressed: ((UIView) -> Void)?
    let middlePressed: (ChatMediaEditorBottomControlsAction) -> Void
    let accessibilityStrings: PresentationStrings?
    let side: ChatMediaEditorToolbarSide?

    init(
        items: ChatMediaEditorBottomControlsItems,
        isHidden: Bool,
        isMiddleEnabled: Bool,
        areSideButtonsEnabled: Bool,
        isRightEnabled: Bool,
        infoString: String?,
        paintModeTitle: @escaping (ChatMediaEditorPaintTab) -> String,
        leftPressed: @escaping () -> Void,
        rightPressed: @escaping () -> Void,
        rightLongPressed: ((UIView) -> Void)?,
        middlePressed: @escaping (ChatMediaEditorBottomControlsAction) -> Void,
        accessibilityStrings: PresentationStrings? = nil,
        side: ChatMediaEditorToolbarSide? = nil
    ) {
        self.items = items
        self.isHidden = isHidden
        self.isMiddleEnabled = isMiddleEnabled
        self.areSideButtonsEnabled = areSideButtonsEnabled
        self.isRightEnabled = isRightEnabled
        self.infoString = infoString
        self.paintModeTitle = paintModeTitle
        self.leftPressed = leftPressed
        self.rightPressed = rightPressed
        self.rightLongPressed = rightLongPressed
        self.middlePressed = middlePressed
        self.accessibilityStrings = accessibilityStrings
        self.side = side
    }

    static func ==(lhs: ChatMediaEditorBottomControlsComponent, rhs: ChatMediaEditorBottomControlsComponent) -> Bool {
        if lhs.items != rhs.items {
            return false
        }
        if lhs.isHidden != rhs.isHidden {
            return false
        }
        if lhs.isMiddleEnabled != rhs.isMiddleEnabled {
            return false
        }
        if lhs.areSideButtonsEnabled != rhs.areSideButtonsEnabled {
            return false
        }
        if lhs.isRightEnabled != rhs.isRightEnabled {
            return false
        }
        if lhs.infoString != rhs.infoString {
            return false
        }
        if (lhs.rightLongPressed == nil) != (rhs.rightLongPressed == nil) {
            return false
        }
        if lhs.side != rhs.side {
            return false
        }
        return true
    }

    private func makeSharedComponent(availableSize: CGSize) -> MediaEditorBottomControlsComponent {
        let items = self.items
        let strings = self.accessibilityStrings
        let left = MediaEditorBottomControlsSideItem(
            id: items.left == .back ? "back" : "close",
            content: .icon(items.left == .back ? "Navigation/Back" : "Navigation/Close", flipped: false),
            width: chatMediaEditorBottomControlsButtonSide,
            tint: .panel,
            accessibilityLabel: items.left == .back ? strings?.Common_Back : strings?.Common_Close
        )
        let rightIconName: String
        let rightId: String
        let rightLabel: String?
        switch items.right {
        case .send:
            rightIconName = "Media Editor/Send"
            rightId = "send"
            rightLabel = strings?.MediaPicker_Send
        case .schedule:
            rightIconName = "Chat/Input/ScheduleIcon"
            rightId = "schedule"
            rightLabel = strings?.Conversation_ScheduleMessage_Title
        case .check:
            rightIconName = "Navigation/Done"
            rightId = "check"
            rightLabel = strings?.Common_Done
        }
        let right = MediaEditorBottomControlsSideItem(
            id: rightId,
            content: .icon(rightIconName, flipped: false),
            width: chatMediaEditorBottomControlsRightWidth(items.right),
            tint: .accent(chatMediaEditorBottomControlsSendColor),
            accessibilityLabel: rightLabel
        )
        let paintModeTitle = self.paintModeTitle
        let middlePressed = self.middlePressed
        let middle = items.middle.map { item -> MediaEditorBottomControlsMiddleItem in
            let content: MediaEditorBottomControlsMiddleItem.Content
            switch item.content {
            case let .roundVideo(selected):
                content = .coloredImage(key: "nagramix-round-video-\(selected)", size: CGSize(width: 28.0, height: 28.0), generate: { color in
                    return nagramiXRoundVideoToolbarImage(selected: selected, color: color)
                })
            case let .icon(name):
                content = .icon(name)
            case let .roundVideoQuality(side):
                content = .coloredImage(key: "nagramix-round-quality-\(side)", size: CGSize(width: 28.0, height: 22.0), generate: { color in
                    return nagramiXRoundVideoQualityImage(side: side, color: color)
                })
            case let .quality(isPhoto, highQuality, preset):
                content = .coloredImage(key: "quality-\(isPhoto)-\(highQuality)-\(preset)", size: CGSize(width: 28.0, height: 22.0), generate: { color in
                    return mediaPickerPhotoToolbarQualityIcon(isPhoto: isPhoto, highQuality: highQuality, preset: preset, color: color)
                })
            case let .paintMode(tab):
                content = .text(paintModeTitle(tab), font: Font.medium(15.0), horizontalInset: chatMediaEditorBottomControlsTextInset)
            }
            let action = item.action
            var accessibilityLabel: String?
            if let strings {
                switch action {
                case .roundVideo:
                    accessibilityLabel = strings.nagramiXRoundVideoTitle
                case let .tab(tab):
                    if tab == .paintTab {
                        accessibilityLabel = strings.Paint_Draw
                    } else if tab == .qualityTab {
                        accessibilityLabel = strings.PhotoEditor_QualityTool
                    } else if tab == .mirrorTab {
                        accessibilityLabel = strings.Paint_Flip
                    }
                case let .tools(tab):
                    switch tab {
                    case .tint:
                        accessibilityLabel = strings.PhotoEditor_TintTool
                    case .blur:
                        accessibilityLabel = strings.Story_Editor_Blur_Title
                    case .curves:
                        accessibilityLabel = strings.PhotoEditor_CurvesTool
                    case .adjustments:
                        accessibilityLabel = nil
                    }
                case .paint:
                    accessibilityLabel = nil
                }
            }
            return MediaEditorBottomControlsMiddleItem(
                id: item.id,
                content: content,
                isHighlighted: item.isHighlighted,
                isDisabled: item.isDisabled,
                accessibilityLabel: accessibilityLabel,
                action: {
                    middlePressed(action)
                }
            )
        }
        let hasRoundVideo = items.middle.contains { $0.action == .roundVideo }
        let spacing = hasRoundVideo ? 0.0 : items.middleSpacing
        let spec = nagramiXRoundVideoToolbarSpec(width: availableSize.width, itemCount: items.middle.count, rightWidth: chatMediaEditorBottomControlsRightWidth(items.right), hasRoundVideo: hasRoundVideo && self.side == nil)
        return MediaEditorBottomControlsComponent(
            spec: spec,
            left: left,
            right: right,
            middle: middle,
            selectedId: items.selectedId,
            middleSpacing: spacing,
            isHidden: self.isHidden,
            isMiddleEnabled: self.isMiddleEnabled,
            areSideButtonsEnabled: self.areSideButtonsEnabled,
            isRightEnabled: self.isRightEnabled,
            infoString: self.infoString,
            leftPressed: self.leftPressed,
            rightPressed: self.rightPressed,
            rightLongPressed: self.rightLongPressed,
            customLayout: self.side.map { side in
                let middleSpacing = spacing
                return MediaEditorBottomControlsCustomLayout(key: AnyHashable("chat.column.\(side)"), layout: { size, middleItemWidths, leftWidth, rightWidth in
                    return chatMediaEditorBottomControlsColumnLocalLayout(size: size, middleItemWidths: middleItemWidths, middleSpacing: middleSpacing, leftWidth: leftWidth, rightWidth: rightWidth)
                })
            },
            middleFadesWhenEmpty: true
        )
    }

    func makeView() -> View {
        return View(frame: CGRect())
    }

    func update(view: View, availableSize: CGSize, state: EmptyComponentState, environment: Environment<Empty>, transition: ComponentTransition) -> CGSize {
        return view.update(component: self.makeSharedComponent(availableSize: availableSize), availableSize: availableSize, state: state, environment: environment, transition: transition)
    }
}

// Vector glyph: the same camera-in-circle in normal and selected states.
func nagramiXRoundVideoToolbarImage(selected: Bool, color: UIColor) -> UIImage? {
    return generateImage(CGSize(width: 28.0, height: 28.0), rotatedContext: { size, context in
        context.clear(CGRect(origin: .zero, size: size))
        context.setLineWidth(1.7)
        context.setLineJoin(.round)
        if selected {
            context.setFillColor(TGPhotoEditorInterfaceAssets.accentColor().cgColor)
            context.fillEllipse(in: CGRect(x: 0.0, y: 0.0, width: 28.0, height: 28.0))
        } else {
            context.setStrokeColor(color.cgColor)
            context.strokeEllipse(in: CGRect(x: 1.0, y: 1.0, width: 26.0, height: 26.0))
        }
        context.setStrokeColor((selected ? UIColor.white : color).cgColor)
        context.addPath(UIBezierPath(roundedRect: CGRect(x: 6.0, y: 9.0, width: 11.0, height: 10.0), cornerRadius: 2.0).cgPath)
        context.strokePath()
        context.move(to: CGPoint(x: 17.0, y: 12.0))
        context.addLine(to: CGPoint(x: 22.0, y: 9.5))
        context.addLine(to: CGPoint(x: 22.0, y: 18.5))
        context.addLine(to: CGPoint(x: 17.0, y: 16.0))
        context.strokePath()
    })
}

// The round export side is a pixel value, not a legacy video-preset index.
func nagramiXRoundVideoQualityImage(side: Int, color: UIColor) -> UIImage? {
    return generateImage(CGSize(width: 28.0, height: 22.0), rotatedContext: { size, context in
        context.clear(CGRect(origin: .zero, size: size))
        let lineWidth: CGFloat = 1.5
        context.setStrokeColor(color.cgColor)
        context.setLineWidth(lineWidth)
        context.addPath(UIBezierPath(roundedRect: CGRect(origin: .zero, size: size).insetBy(dx: lineWidth / 2.0, dy: lineWidth / 2.0), cornerRadius: 5.0).cgPath)
        context.strokePath()
        let text = "\(side)" as NSString
        let attributes: [NSAttributedString.Key: Any] = [.font: Font.semibold(11.0), .foregroundColor: color]
        let textSize = text.size(withAttributes: attributes)
        text.draw(at: CGPoint(x: floor((size.width - textSize.width) / 2.0), y: floor((size.height - textSize.height) / 2.0)), withAttributes: attributes)
    })
}
