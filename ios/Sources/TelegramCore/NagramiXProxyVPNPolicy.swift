import Foundation
import Darwin
import CFNetwork
import Network
import SwiftSignalKit

// iOS exposes no general third-party VPN status API. Treat an up, addressed
// tunnel listed by the system's scoped network configuration as a VPN signal.
// This is detection, not access to or modification of a VPN configuration.
public enum NagramiXProxyVPNPolicy {
    private static let monitor = NagramiXProxyVPNMonitor()

    public static var bypassed: Bool {
        return self.monitor.current.with { $0 }
    }

    public static func bypassedSignal() -> Signal<Bool, NoError> {
        return self.monitor.promise.get()
    }
}

private final class NagramiXProxyVPNMonitor {
    private static let preferenceKey = "nagramix.network.avoidProxyWithVPN"
    let current: Atomic<Bool>
    let promise: ValuePromise<Bool>
    private let queue = Queue(name: "org.nagramix.proxy-vpn-policy")
    private let pathQueue = DispatchQueue(label: "org.nagramix.proxy-vpn-path")
    private var pathMonitor: NWPathMonitor?
    private var timer: SwiftSignalKit.Timer?
    private var inForeground = true
    private var observers: [NSObjectProtocol] = []

    private static var enabled: Bool {
        return UserDefaults.standard.object(forKey: self.preferenceKey) as? Bool ?? false
    }

    init() {
        let value = Self.enabled && Self.hasActiveTunnel()
        self.current = Atomic(value: value)
        self.promise = ValuePromise(value, ignoreRepeated: true)
        self.observers.append(NotificationCenter.default.addObserver(forName: Notification.Name("NagramiXSettingsChanged"), object: nil, queue: nil, using: { [weak self] _ in
            self?.queue.async { self?.refresh() }
        }))
        for (name, foreground) in [("UIApplicationDidEnterBackgroundNotification", false), ("UIApplicationWillEnterForegroundNotification", true)] {
            self.observers.append(NotificationCenter.default.addObserver(forName: Notification.Name(name), object: nil, queue: nil, using: { [weak self] _ in
                self?.queue.async {
                    guard let self else { return }
                    self.inForeground = foreground
                    self.refresh()
                }
            }))
        }
        self.queue.async { [weak self] in self?.refresh() }
    }

    deinit {
        self.pathMonitor?.cancel()
        self.timer?.invalidate()
        for observer in self.observers { NotificationCenter.default.removeObserver(observer) }
    }

    private func refresh() {
        let enabled = Self.enabled
        if enabled && self.pathMonitor == nil {
            let monitor = NWPathMonitor()
            monitor.pathUpdateHandler = { [weak self] _ in
                self?.queue.async { self?.refresh() }
            }
            self.pathMonitor = monitor
            monitor.start(queue: self.pathQueue)
        } else if !enabled {
            self.pathMonitor?.cancel()
            self.pathMonitor = nil
        }
        // A tunnel can become addressed after the route callback. Recheck only
        // while this opt-in setting is enabled and the application is foreground.
        if enabled && self.inForeground && Bundle.main.infoDictionary?["NSExtension"] == nil {
            if self.timer == nil {
                let timer = SwiftSignalKit.Timer(timeout: 2.0, repeat: true, completion: { [weak self] in self?.refresh() }, queue: self.queue)
                self.timer = timer
                timer.start()
            }
        } else {
            self.timer?.invalidate()
            self.timer = nil
        }
        let value = enabled && Self.hasActiveTunnel()
        if self.current.swap(value) != value { self.promise.set(value) }
    }

    private static func hasActiveTunnel() -> Bool {
        guard let settings = CFNetworkCopySystemProxySettings()?.takeRetainedValue() as? [String: Any],
              let scoped = settings["__SCOPED__"] as? [String: Any] else { return false }
        var interfaces: UnsafeMutablePointer<ifaddrs>?
        guard getifaddrs(&interfaces) == 0, let first = interfaces else { return false }
        defer { freeifaddrs(first) }
        var cursor: UnsafeMutablePointer<ifaddrs>? = first
        while let entry = cursor {
            defer { cursor = entry.pointee.ifa_next }
            guard let namePointer = entry.pointee.ifa_name, let address = entry.pointee.ifa_addr else { continue }
            let name = String(cString: namePointer)
            guard name.hasPrefix("utun") || name.hasPrefix("ipsec") || name.hasPrefix("ppp"), scoped[name] != nil else { continue }
            let flags = entry.pointee.ifa_flags
            guard flags & UInt32(IFF_UP) != 0, flags & UInt32(IFF_RUNNING) != 0 else { continue }
            let family = Int32(address.pointee.sa_family)
            guard family == AF_INET || family == AF_INET6 else { continue }
            var host = [CChar](repeating: 0, count: Int(NI_MAXHOST))
            let result = host.withUnsafeMutableBufferPointer { buffer in
                return getnameinfo(address, socklen_t(address.pointee.sa_len), buffer.baseAddress, socklen_t(buffer.count), nil, 0, NI_NUMERICHOST)
            }
            guard result == 0 else { continue }
            let value = host.withUnsafeBufferPointer { buffer -> String in
                guard let base = buffer.baseAddress else { return "" }
                return String(cString: base)
            }.lowercased()
            // Ignore empty, loopback and IPv6 link-local-only tunnel remnants.
            let ipv6LinkLocal = family == AF_INET6 && ["fe8", "fe9", "fea", "feb"].contains(where: { value.hasPrefix($0) })
            if !value.isEmpty && value != "0.0.0.0" && value != "::" && value != "::1" && !value.hasPrefix("127.") && !ipv6LinkLocal {
                return true
            }
        }
        return false
    }
}
