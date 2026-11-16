"""Исполнять настоящие очередь, enqueue и deinit с явной границей WebKit."""
from pathlib import Path
from validate_quick_format import block
from doh_empty_action_runtime import library

WEB = 'submodules/TelegramUniversalVideoContent/Sources/WebEmbedPlayerNode.swift'
ROOT = Path(__file__).resolve().parents[1]


def signal_library(source):
    sk = source / 'submodules/SSignalKit/SwiftSignalKit/Source'
    return library(source) + '\n' + (sk / 'QueueLocalObject.swift').read_text() + '\n' + block((sk / 'Signal_Dispatch.swift').read_text(), 'public func runOn<T, E>(_ queue: Queue)')


def fixture(source):
    text = (source / WEB).read_text()
    helper = block(text, 'private final class NagramiXWebJavaScriptQueue')
    resources = block(text, 'private final class NagramiXWebPlayerResources')
    properties = text.split('    private let nagramiXWebResources:', 1)[1].split('    init(impl:', 1)[0]
    setup = text.split('        self.nagramiXWebResources = ', 1)[1].split('        super.init()', 1)[0]
    return signal_library(source) + '\n' + (ROOT / 'scripts/tests/NagramiXWebPlayerMainQueueBoundary.swift').read_text() + '\n' + helper + '\n' + resources + '''
private final class Player {
    private let nagramiXWebResources:''' + properties + '''
    init(_ webView: WKWebView) {
        let systemPiP = NagramiXWebSystemPictureInPicture()
        systemPiP.webView = webView
        self.nagramiXWebResources = ''' + setup + '''
    }
''' + block(text, '    private func evaluateJavaScript(') + '''
    func send(_ script: String, completion: ((Any?) -> Void)? = nil) {
        self.evaluateJavaScript(js: script, completion: completion)
    }
}
''' + (ROOT / 'scripts/tests/NagramiXWebPlayerMainQueueTests.swift').read_text()


def released_fixture(source, previous):
    return signal_library(source) + '\n' + (ROOT / 'scripts/tests/NagramiXWebPlayerMainQueueBoundary.swift').read_text() + '''
private final class ReleasedPlayer {
 private let webView=WKWebView()
 private let nagramiXSystemPiP=NagramiXWebSystemPictureInPicture()
 private var nagramiXPolicyObserver:NSObjectProtocol?
''' + block(previous, '    deinit {') + '''
}
@main private struct ReleasedTest {
 static func main(){
  let owner=Box<ReleasedPlayer?>(ReleasedPlayer())
  let done=DispatchSemaphore(value:0)
  DispatchQueue.global().async {owner.value=nil;done.signal()}
  _=done.wait(timeout:.now()+5)
  expect(false,"released destructor unexpectedly accepted background cleanup")
 }
}
'''
