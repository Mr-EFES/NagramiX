final class Bridge {
    final class Frame {}
    var isActive = true
    var request: String? = "first"
    var frame: Frame? = Frame()
    var frameKey: String? = "frame"
    var stops = 0, checks = 0
    var dispatched: [[String: String]] = []
    func stop() { stops += 1; request = nil; isActive = false }
    func dispatch(_ command: [String: String], frame: Frame?) {
        precondition(frame === self.frame)
        dispatched.append(command)
    }
    func schedulePresentationCheck() { checks += 1 }
    // PRODUCTION_EXIT
}
@main struct Tests {
    static func main() {
        let bridge = Bridge()
        bridge.requestExit()
        precondition(bridge.dispatched == [["command": "stop", "request": "first", "frameKey": "frame"]])
        precondition(bridge.isActive && bridge.request == "first" && bridge.checks == 1 && bridge.stops == 0)
        bridge.isActive = false
        bridge.requestExit()
        precondition(bridge.stops == 1 && bridge.request == nil)
        print("WebKit stop waits for inline confirmation")
    }
}
