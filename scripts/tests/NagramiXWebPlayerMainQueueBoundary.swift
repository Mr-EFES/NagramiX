import Foundation
import Dispatch
#if canImport(Glibc)
import Glibc
#else
import Darwin
#endif

// These hosts expose queue/ownership errors; they do not implement WebKit or UIKit.
private final class Evidence {
    static var checks = 0
    static var stops = 0
    static var removed = 0
    static var destroyedViews = 0
    static func main() {
        if !Thread.isMainThread {
            FileHandle.standardError.write(Data("WebKit cleanup must run on main\n".utf8))
            exit(96)
        }
    }
}
private func expect(_ value: @autoclosure () -> Bool, _ label: String) {
    Evidence.main()
    guard value() else {
        FileHandle.standardError.write(Data((label + "\n").utf8)); exit(96)
    }
    Evidence.checks += 1
}
private final class Probe<T: AnyObject> { weak var value: T? }
private final class Box<T> { var value: T; init(_ value: T) { self.value = value } }
private final class Gesture { var isEnabled = true { didSet { Evidence.main() } } }
private class UIView: NSObject {
    let gestureRecognizers: [Gesture]? = [Gesture()]
    var subviews: [UIView] = []
}
private final class Controller {
    func removeScriptMessageHandler(forName name: String) {
        Evidence.main(); expect(name == "nagramiXSystemPiP", "handler name preserved"); Evidence.removed += 1
    }
}
private final class Configuration { let userContentController = Controller() }
private final class WKWebView: UIView {
    let configuration = Configuration()
    var navigationDelegate: AnyObject? { didSet { Evidence.main() } }
    var scripts: [String] = []
    var callbacks: [((Any?, Error?) -> Void)] = []
    func evaluateJavaScript(_ js: String, completionHandler: ((Any?, Error?) -> Void)?) {
        Evidence.main(); scripts.append(js)
        if let completionHandler { callbacks.append(completionHandler) }
    }
    func complete(_ value: Any? = nil, error: Error? = nil) {
        Evidence.main(); let callback = callbacks.removeFirst(); callback(value, error)
    }
    func stopLoading() { Evidence.main(); Evidence.stops += 1 }
    deinit { Evidence.main(); Evidence.destroyedViews += 1 }
}
private final class NagramiXWebSystemPictureInPicture {
    weak var webView: WKWebView?
    var actualMediaChanged: ((Bool) -> Void)?
    var restore: ((@escaping (Bool) -> Void) -> Void)?
    func stop() { Evidence.main() }
    deinit { Evidence.main() }
}
private func pump(until done: () -> Bool) {
    let deadline = Date().addingTimeInterval(5)
    while !done() && Date() < deadline { _ = RunLoop.current.run(mode: .default, before: Date().addingTimeInterval(0.001)) }
    expect(done(), "bounded main-queue operation completed")
}
private struct Failure: Error {}
