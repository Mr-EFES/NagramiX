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

private func nagramiXCustomDohHint(_ value: String) -> String {
    return value.replacingOccurrences(of: "HTTPS URL ", with: "HTTPS URL\n")
}

// The controller callbacks run on the main queue. A terminal action owns the
// result once, so Delete/dismiss cannot be followed by a delayed Save callback.
private final class NagramiXCustomDohSubmission {
    private enum State { case editing, validating, finished }
    private var state: State = .editing
    var isFinished: Bool { self.state == .finished }

    func begin() -> Bool {
        guard self.state == .editing else { return false }
        self.state = .validating
        return true
    }
    func finish() -> Bool {
        guard self.state != .finished else { return false }
        self.state = .finished
        return true
    }
    func failed() -> Bool {
        guard self.state == .validating else { return false }
        self.state = .editing
        return true
    }
}

func nagramiXCustomDohController(context: AccountContext, initialValue: String, apply: @escaping (String) -> Void, clear: @escaping () -> Void) -> ViewController {
    let presentationData = context.sharedContext.currentPresentationData.with { $0 }
    let strings = presentationData.strings
    let inputState = AlertInputFieldComponent.ExternalState()
    let doneIsEnabled = inputState.valueSignal
    |> map { validatedNagramiXDohUrl($0) != nil }
    let progress = ValuePromise<Bool>(false)
    let validationDisposable = MetaDisposable()
    let submission = NagramiXCustomDohSubmission()

    var applyImpl: (() -> Void)?
    var removeImpl: (() -> Void)?
    let content: [AnyComponentWithIdentity<AlertComponentEnvironment>] = [
        AnyComponentWithIdentity(id: "title", component: AnyComponent(AlertTitleComponent(title: strings.nagramiXDnsCustom))),
        AnyComponentWithIdentity(id: "text", component: AnyComponent(AlertTextComponent(content: .plain(nagramiXCustomDohHint(strings.nagramiXCustomDohInvalid))))),
        AnyComponentWithIdentity(id: "input", component: AnyComponent(AlertInputFieldComponent(context: context, initialValue: initialValue, placeholder: strings.nagramiXCustomDohPlaceholder, characterLimit: 2048, hasClearButton: true, keyboardType: .URL, autocapitalizationType: .none, autocorrectionType: .no, isInitiallyFocused: true, externalState: inputState, shouldChangeText: { _ in true }, returnKeyAction: { applyImpl?() })))
    ]
    let actionsSignal: Signal<[AlertScreen.Action], NoError> = inputState.valueSignal
    |> map { !$0.isEmpty }
    |> distinctUntilChanged
    |> map { hasValue in
        return [
            .init(id: "dismiss", title: hasValue ? strings.Common_Delete : strings.WebApp_Download_Cancel, type: hasValue ? .destructive : .generic, action: { removeImpl?() }, autoDismiss: false),
            .init(id: "save", title: strings.nagramiXSave, type: .default, action: { applyImpl?() }, autoDismiss: false, isEnabled: doneIsEnabled, progress: progress.get())
        ]
    }
    let controller = AlertScreen(
        configuration: AlertScreen.Configuration(allowInputInset: true),
        contentSignal: .single(content),
        actionsSignal: actionsSignal,
        updatedPresentationData: (presentationData, context.sharedContext.presentationData)
    )
    removeImpl = { [weak controller] in
        guard submission.finish() else { return }
        validationDisposable.dispose()
        if !inputState.value.isEmpty {
            clear()
        }
        controller?.dismiss()
    }
    applyImpl = { [weak controller] in
        guard !submission.isFinished else { return }
        guard let url = validatedNagramiXDohUrl(inputState.value) else {
            inputState.animateError()
            return
        }
        guard submission.begin() else { return }
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
            guard submission.finish() else { return }
            didResolve = true
            apply(url)
            controller?.dismiss()
        }, completed: {
            if !didResolve && submission.failed() {
                progress.set(false)
                inputState.animateError()
                controller?.present(textAlertController(context: context, title: nil, text: strings.nagramiXCustomDohUnavailable, actions: [TextAlertAction(type: .defaultAction, title: strings.Common_OK, action: {})]), in: .window(.root))
            }
        }))
    }
    controller.dismissed = { _ in
        _ = submission.finish()
        validationDisposable.dispose()
    }
    return controller
}
