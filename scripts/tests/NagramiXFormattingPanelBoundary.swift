import Foundation

// Platform boundaries only. The actual factory/adapter, panel methods and
// Foundation geometry are extracted unchanged from the patched native source.
final class Layer {
    enum Curve { case continuous }
    enum Corner { case layerMinXMinYCorner, layerMaxXMinYCorner }
    var cornerRadius: CGFloat = 0
    var cornerCurve = Curve.continuous
    var maskedCorners: Set<Corner> = []
}
struct LayoutMetrics {}
struct DeviceMetrics {}
struct AccountContext {}
struct ChatControllerInteraction {}
typealias ChatInputPanelNode = AnyObject
typealias ChatTextInputPanelNode = FormattingPanel
typealias ChatPanelInterfaceInteraction = Interaction
typealias ContainedViewLayoutTransition = Transition

class ChatInputNode {
    let view = UIView()
    var clipsToBounds = false
    var interfaceInteraction: Interaction?
    func updateLayout(width: CGFloat, leftInset: CGFloat, rightInset: CGFloat, bottomInset: CGFloat,
                      standardInputHeight: CGFloat, inputHeight: CGFloat, maximumHeight: CGFloat,
                      inputPanelHeight: CGFloat, transition: Transition,
                      interfaceState: ChatPresentationInterfaceState, layoutMetrics: LayoutMetrics,
                      deviceMetrics: DeviceMetrics, isVisible: Bool, isExpanded: Bool) -> (CGFloat, CGFloat) {
        return (0, 0)
    }
}
final class ChatEntityKeyboardInputNode: ChatInputNode {}
final class ChatButtonKeyboardInputNode: ChatInputNode {
    init(context: AccountContext, controllerInteraction: ChatControllerInteraction) { super.init() }
}
final class EmptyInputView: UIView {}
struct Component { var hideKeyboard: Bool }

extension ChatPresentationInterfaceState {
    func updatedInputMode(_ f: (InputMode) -> InputMode) -> ChatPresentationInterfaceState {
        let copy = ChatPresentationInterfaceState()
        copy.inputTextPanelState = self.inputTextPanelState
        copy.interfaceState = self.interfaceState
        copy.chatLocation = self.chatLocation
        copy.inputMode = f(self.inputMode)
        return copy
    }
}

func updateComponentInput(panelNode: FormattingPanel, component: Component, presentationInterfaceState: ChatPresentationInterfaceState) {
    // COMPONENT_INPUT_VIEW
}

// NATIVE_INPUT_FACTORY
