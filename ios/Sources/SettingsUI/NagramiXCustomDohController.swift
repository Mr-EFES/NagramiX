import Foundation
import Display
import SwiftSignalKit
import MtProtoKit
import TelegramPresentationData
import PresentationDataUtils
import AccountContext
import ComponentFlow
import AlertComponent
import AlertInputFieldComponent
import AlertUI
import NagramiXCore

private func validatedNagramiXDohUrl(_ value: String) -> String? {
    guard value == value.trimmingCharacters(in: .whitespacesAndNewlines), !value.isEmpty else {
        return nil
    }
    guard value.rangeOfCharacter(from: .whitespacesAndNewlines) == nil, let components = URLComponents(string: value), components.scheme?.lowercased() == "https", let host = components.host, !host.isEmpty, components.user == nil, components.password == nil, let url = components.url else {
        return nil
    }
    return url.absoluteString
}

func nagramiXCustomDohController(context: AccountContext, initialValue: String, apply: @escaping (String) -> Void, clear: @escaping () -> Void) -> ViewController {
    let presentationData = context.sharedContext.currentPresentationData.with { $0 }
    let strings = presentationData.strings
    let inputState = AlertInputFieldComponent.ExternalState()
    let doneIsEnabled = inputState.valueSignal
    |> map { validatedNagramiXDohUrl($0) != nil }
    let progress = ValuePromise<Bool>(false)
    let validationDisposable = MetaDisposable()

    var applyImpl: (() -> Void)?
    let content: [AnyComponentWithIdentity<AlertComponentEnvironment>] = [
        AnyComponentWithIdentity(id: "title", component: AnyComponent(AlertTitleComponent(title: strings.nagramiXDnsCustom))),
        AnyComponentWithIdentity(id: "text", component: AnyComponent(AlertTextComponent(content: .plain(strings.nagramiXCustomDohInvalid)))),
        AnyComponentWithIdentity(id: "input", component: AnyComponent(AlertInputFieldComponent(context: context, initialValue: initialValue, placeholder: strings.nagramiXCustomDohPlaceholder, characterLimit: 2048, hasClearButton: true, keyboardType: .URL, autocapitalizationType: .none, autocorrectionType: .no, isInitiallyFocused: true, externalState: inputState, shouldChangeText: { _ in true }, returnKeyAction: { applyImpl?() })))
    ]
    var actions: [AlertScreen.Action] = [
        .init(title: strings.Common_Cancel),
        .init(title: strings.nagramiXSave, type: .default, action: { applyImpl?() }, autoDismiss: false, isEnabled: doneIsEnabled, progress: progress.get())
    ]
    if !initialValue.isEmpty {
        actions.insert(.init(title: strings.Common_Delete, type: .destructive, action: clear), at: 1)
    }
    let controller = AlertScreen(
        configuration: AlertScreen.Configuration(allowInputInset: true),
        content: content,
        actions: actions,
        updatedPresentationData: (presentationData, context.sharedContext.presentationData)
    )
    applyImpl = { [weak controller] in
        guard let url = validatedNagramiXDohUrl(inputState.value) else {
            inputState.animateError()
            return
        }
        progress.set(true)
        var didResolve = false
        validationDisposable.set((Signal<String, NoError> { subscriber in
            let disposable = NagramiXDNSResolver.testEndpoint(url, hostname: "example.com").start(next: { value in
                if let value = value as? String, !value.isEmpty {
                    subscriber.putNext(value)
                    subscriber.putCompletion()
                }
            }, error: { _ in
                subscriber.putCompletion()
            }, completed: {
                subscriber.putCompletion()
            })
            return ActionDisposable { disposable?.dispose() }
        }
        |> take(1)
        |> deliverOnMainQueue).start(next: { _ in
            didResolve = true
            apply(url)
            controller?.dismiss()
        }, completed: {
            if !didResolve {
                progress.set(false)
                inputState.animateError()
                controller?.present(textAlertController(context: context, title: nil, text: strings.nagramiXCustomDohUnavailable, actions: [TextAlertAction(type: .defaultAction, title: strings.Common_OK, action: {})]), in: .window(.root))
            }
        }))
    }
    controller.dismissed = { _ in
        validationDisposable.dispose()
    }
    return controller
}
