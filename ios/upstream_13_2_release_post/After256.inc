import Foundation
import UIKit
import AsyncDisplayKit
import Display
import TelegramCore
import AccountContext
import ChatPresentationInterfaceState
import ChatControllerInteraction
import ChatInputNode
import ChatEntityKeyboardInputNode
import ChatInputPanelNode
import ChatButtonKeyboardInputNode
import ChatTextInputPanelNode

// Formatting is an ordinary native input node, so ChatControllerNode supplies
// exactly the same slide, clipping, composer movement and dismissal as emoji.
private final class NagramiXFormattingInputNode: ChatInputNode {
    let panel: UIView

    init(panel: UIView) {
        self.panel = panel
        super.init()
        self.clipsToBounds = true
        self.view.addSubview(panel)
        panel.layer.cornerRadius = 30
        panel.layer.cornerCurve = .continuous
        panel.layer.maskedCorners = [.layerMinXMinYCorner, .layerMaxXMinYCorner]
        panel.clipsToBounds = true
    }

    override func layout() {
        super.layout()
        // The parent may reduce the visible input bounds after updateLayout,
        // for example while dragging below a tall editing field. Keep the
        // surface and its controls inside those actual bounds, not a stale
        // preferred keyboard size or UIKit's intermediate autoresizing result.
        if self.panel.frame != self.bounds {
            self.panel.frame = self.bounds
            self.panel.setNeedsLayout()
        }
    }

    override func updateLayout(width: CGFloat, leftInset: CGFloat, rightInset: CGFloat, bottomInset: CGFloat, standardInputHeight: CGFloat, inputHeight: CGFloat, maximumHeight: CGFloat, inputPanelHeight: CGFloat, transition: ContainedViewLayoutTransition, interfaceState: ChatPresentationInterfaceState, layoutMetrics: LayoutMetrics, deviceMetrics: DeviceMetrics, isVisible: Bool, isExpanded: Bool) -> (CGFloat, CGFloat) {
        // ChatEntityKeyboardInputNode returns this same expanded/standard height.
        // The parent computes expansion and safe bounds for both node types.
        guard width.isFinite, width >= 0, standardInputHeight.isFinite else { return (0, 0) }
        let height = max(0, standardInputHeight)
        self.panel.frame = CGRect(x: 0, y: 0, width: width, height: height)
        self.panel.setNeedsLayout()
        return (height, 0)
    }
}

func inputNodeForChatPresentationIntefaceState(_ chatPresentationInterfaceState: ChatPresentationInterfaceState, context: AccountContext, currentNode: ChatInputNode?, interfaceInteraction: ChatPanelInterfaceInteraction?, controllerInteraction: ChatControllerInteraction, inputPanelNode: ChatInputPanelNode?, makeMediaInputNode: () -> ChatInputNode?) -> ChatInputNode? {
    if let inputPanelNode = inputPanelNode, !(inputPanelNode is ChatTextInputPanelNode) {
        return nil
    }
    // The text panel shows the bot's Start button in place of its input (a blocked bot, a bot not started yet): no
    // input node goes with it. The input mode is kept, so a reply keyboard comes back once the bot is unblocked.
    if chatDisplaysBotStartButton(chatPresentationInterfaceState) {
        return nil
    }
    if let textPanel = inputPanelNode as? ChatTextInputPanelNode,
       let panel = textPanel.nagramiXFormattingPanelView(for: chatPresentationInterfaceState) {
        if let current = currentNode as? NagramiXFormattingInputNode, current.panel === panel {
            return current
        }
        let node = NagramiXFormattingInputNode(panel: panel)
        node.interfaceInteraction = interfaceInteraction
        return node
    }
    switch chatPresentationInterfaceState.inputMode {
    case .media:
        if let currentNode = currentNode as? ChatEntityKeyboardInputNode {
            return currentNode
        } else if let inputMediaNode = makeMediaInputNode() {
            inputMediaNode.interfaceInteraction = interfaceInteraction
            return inputMediaNode
        } else {
            return nil
        }
    case .inputButtons:
        if chatPresentationInterfaceState.forceInputCommandsHidden {
            return nil
        } else {
            if let currentNode = currentNode as? ChatButtonKeyboardInputNode {
                return currentNode
            } else {
                let inputNode = ChatButtonKeyboardInputNode(context: context, controllerInteraction: controllerInteraction)
                inputNode.interfaceInteraction = interfaceInteraction
                return inputNode
            }
        }
    case .none, .text:
        return nil
    }
}
