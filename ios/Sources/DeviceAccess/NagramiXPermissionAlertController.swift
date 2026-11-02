import UIKit
import Display

/// Только окна настроек после отказа. Само разрешение запрашивает DeviceAccess.
public func nagramiXPermissionAlertController(theme: AlertControllerTheme, title: String?, text: String, actions: [TextAlertAction]) -> ViewController {
    let alert = UIAlertController(title: title, message: text, preferredStyle: .alert)
    // Штатный мост Telegram для UIViewController: UIKit сам измеряет текст,
    // кнопки и доступную область, без ограниченной маски TextAlertContentNode.
    let controller = LegacyPresentedController(legacyController: alert, presentation: .custom)
    controller.blocksBackgroundWhenInOverlay = true
    controller.statusBar.statusBarStyle = .Ignore
    alert.overrideUserInterfaceStyle = theme.backgroundType == .dark ? .dark : .light
    alert.view.tintColor = theme.accentColor

    for action in actions {
        let style: UIAlertAction.Style
        switch action.type {
        case .genericAction:
            style = .cancel
        case .defaultAction:
            style = .default
        case .destructiveAction, .defaultDestructiveAction:
            style = .destructive
        }
        let nativeAction = UIAlertAction(title: action.title, style: style, handler: { [weak controller] _ in
            // UIKit закрывает alert; убираем также прозрачный host Telegram.
            // Существующий callback (в том числе Настройки) выполняется один раз.
            controller?.dismiss(completion: action.action)
        })
        alert.addAction(nativeAction)
        switch action.type {
        case .defaultAction, .defaultDestructiveAction:
            alert.preferredAction = nativeAction
        default:
            break
        }
    }
    return controller
}
