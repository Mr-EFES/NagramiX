import Foundation

@main struct FormattingBoundsTests {
    static func main() {
        FormattingPanelTests.main()
        NagramiXFormattingSettings.setEnabled(true)
        let panel = FormattingPanel()
        let state = panel.presentationInterfaceState!
        panel.nagramiXConfigureFormattingHost(inputView: EmptyInputView(), requestLayout: {})
        panel.nagramiXToggleFormatting()
        let host = inputNodeForChatPresentationIntefaceState(state, context: AccountContext(), currentNode: nil,
            interfaceInteraction: panel.interfaceInteraction, controllerInteraction: ChatControllerInteraction(),
            inputPanelNode: panel, makeMediaInputNode: { nil })!
        let content = host.view.subviews.first!
        var checks = 0
        func check(_ condition: Bool, _ message: String) {
            if !condition {
                print("FAIL: \(message)")
                exit(1)
            }
            checks += 1
        }
        // Native ChatControllerNode computes effective bounds after the input
        // node's preferred-height update. Model those separate lifecycle steps.
        for width in [320.0, 393, 440, 844] {
            for height in [346.0, 216, 130, 24, 0, 320] {
                _ = host.updateLayout(width: width, leftInset: 0, rightInset: 0, bottomInset: 34,
                    standardInputHeight: 346, inputHeight: 0, maximumHeight: 700, inputPanelHeight: 52,
                    transition: .immediate, interfaceState: state, layoutMetrics: LayoutMetrics(),
                    deviceMetrics: DeviceMetrics(), isVisible: true, isExpanded: false)
                host.bounds = CGRect(x: 0, y: 0, width: width, height: height)
                host.layout()
                check(content.frame == host.bounds, "formatting must fill the actual visible host after resizing")
                let invalidations = content.layoutInvalidations
                host.layout()
                check(content.frame == host.bounds && content.layoutInvalidations == invalidations,
                      "unchanged bounds must not start another layout/animation cycle")
                check(host.view.subviews.count == 1 && host.view.subviews.first === content,
                      "resizing retains one formatting surface and its current state")
            }
        }
        check(host.clipsToBounds, "host clips the panel during native interactive transitions")
        check(content.clipsToBounds, "surface clips its own scroll content")
        print("PASS \(checks) formatting bounds/resize regression checks; UIKit lifecycle is a boundary")
    }
}
