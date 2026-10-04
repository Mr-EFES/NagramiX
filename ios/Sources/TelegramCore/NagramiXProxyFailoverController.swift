import Foundation
import SwiftSignalKit

private enum NagramiXNetworkSettingsBridge {
    static let changedNotification = Notification.Name("NagramiXSettingsChanged")
    static var proxyAutoSwitchEnabled: Bool {
        return UserDefaults.standard.object(forKey: "nagramix.network.proxyAutoSwitchEnabled") as? Bool ?? false
    }
    static var proxyAutoSwitchTimeout: Int {
        let value = UserDefaults.standard.integer(forKey: "nagramix.network.proxyAutoSwitchTimeout")
        return [15, 30, 60].contains(value) ? value : 15
    }
}

/// Queue-confined failover. A generation guards timers and queued transactions
/// against manual selection, disabling proxies, or deleting a reserve.
final class NagramiXProxyFailoverController {
    private enum Phase {
        case idle
        case waiting(token: UInt64)
        case awaitingReserve(token: UInt64)
        case applying(candidate: ProxyServerSettings, token: UInt64)
        case connecting(candidate: ProxyServerSettings, token: UInt64)

        var expectedServer: ProxyServerSettings? {
            switch self {
            case let .applying(candidate, _), let .connecting(candidate, _): return candidate
            default: return nil
            }
        }
    }

    private static let sharedQueue = Queue(name: "org.nagramix.proxy-failover")
    private static weak var owner: NagramiXProxyFailoverController?
    private let queue = NagramiXProxyFailoverController.sharedQueue
    private var accountManager: AccountManager<TelegramAccountManagerTypes>?
    private var network: Network?
    private var healthMonitor: ProxyServersStatuses?
    private var healthDisposable: Disposable?
    private var healthSnapshotDisposable: Disposable?
    private var configuredTimeout = NagramiXNetworkSettingsBridge.proxyAutoSwitchTimeout
    private var settingsDisposable: Disposable?
    private var statusDisposable: Disposable?
    private var applyDisposable: Disposable?
    private var observer: NSObjectProtocol?
    private var lifecycleObservers: [NSObjectProtocol] = []
    private var inForeground = true
    private var cancellation = Atomic<Bool>(value: false)
    private var timer: SwiftSignalKit.Timer?
    private var healthStatuses: [ProxyServerSettings: ProxyServerStatus] = [:]
    private var settings: ProxySettings = .defaultSettings
    private var status: ConnectionStatus = .waitingForNetwork
    private var phase: Phase = .idle
    private var generation: UInt64 = 0

    func start(accountManager: AccountManager<TelegramAccountManagerTypes>, network: Network) {
        self.queue.async { [weak self] in
            guard let self else { return }
            self.stopInternal()
            self.accountManager = accountManager
            self.network = network
            self.lifecycleObservers.append(NotificationCenter.default.addObserver(forName: Notification.Name("NagramiXProxySelectionRequested"), object: nil, queue: nil, using: { [weak self] _ in
                self?.queue.async {
                    self?.invalidate()
                    self?.reevaluate()
                }
            }))
            for (name, foreground) in [("UIApplicationDidEnterBackgroundNotification", false), ("UIApplicationWillEnterForegroundNotification", true)] {
                self.lifecycleObservers.append(NotificationCenter.default.addObserver(forName: Notification.Name(name), object: nil, queue: nil, using: { [weak self] _ in
                    self?.queue.async {
                        guard let self else { return }
                        self.inForeground = foreground
                        self.invalidate()
                        self.reevaluate()
                    }
                }))
            }
            let proxySettings = accountManager.sharedData(keys: [SharedDataKeys.proxySettings])
            |> map { $0.entries[SharedDataKeys.proxySettings]?.get(ProxySettings.self) ?? .defaultSettings }
            let monitor = ProxyServersStatuses(network: network, servers: proxySettings |> map { $0.servers }, refreshEnabled: proxySettings |> map { $0.enabled }, activeServer: proxySettings |> map { $0.activeServer })
            self.healthMonitor = monitor
            _ = network.nagramiXProxyStatuses.swap(monitor)
            self.healthDisposable = (monitor.statuses() |> deliverOn(self.queue)).start(next: { [weak self] statuses in
                guard let self else { return }
                self.healthStatuses = statuses
                if !self.needsConnection {
                    self.invalidate()
                } else if case .awaitingReserve = self.phase {
                    self.selectVerifiedReserve(token: self.generation)
                } else {
                    self.reevaluate()
                }
            })
            self.settingsDisposable = (proxySettings |> deliverOn(self.queue)).start(next: { [weak self] value in
                self?.updateSettings(value)
            })
            self.statusDisposable = (network.connectionStatus |> deliverOn(self.queue)).start(next: { [weak self] value in
                self?.updateStatus(value)
            })
            self.observer = NotificationCenter.default.addObserver(forName: NagramiXNetworkSettingsBridge.changedNotification, object: nil, queue: nil, using: { [weak self] _ in
                self?.queue.async {
                    guard let self else { return }
                    let timeout = NagramiXNetworkSettingsBridge.proxyAutoSwitchTimeout
                    if !NagramiXNetworkSettingsBridge.proxyAutoSwitchEnabled || timeout != self.configuredTimeout {
                        self.invalidate()
                    }
                    self.configuredTimeout = timeout
                    self.reevaluate()
                }
            })
        }
    }

    func stop() {
        self.queue.async { self.stopInternal() }
    }

    private func stopInternal() {
        self.invalidate()
        self.healthDisposable?.dispose()
        self.healthDisposable = nil
        if let network = self.network, let monitor = self.healthMonitor {
            _ = network.nagramiXProxyStatuses.modify { $0 === monitor ? nil : $0 }
        }
        self.healthMonitor?.stop()
        self.healthMonitor = nil
        self.settingsDisposable?.dispose()
        self.settingsDisposable = nil
        self.statusDisposable?.dispose()
        self.statusDisposable = nil
        if let observer = self.observer { NotificationCenter.default.removeObserver(observer) }
        self.observer = nil
        for observer in self.lifecycleObservers { NotificationCenter.default.removeObserver(observer) }
        self.lifecycleObservers.removeAll()
        self.settings = .defaultSettings
        self.status = .waitingForNetwork
        self.accountManager = nil
        self.network = nil
        self.healthStatuses.removeAll()
    }

    private var needsConnection: Bool {
        switch self.status {
        case .connecting, .updating: return true
        case let .online(proxyAddress):
            // MTProto reports proxySettings.ip. An old direct/other-proxy
            // online event must not cancel the newly selected proxy's deadline.
            guard let active = self.settings.activeServer, proxyAddress == active.host,
                  let health = self.healthStatuses[active], case .available = health else { return true }
            return false
        case .waitingForNetwork: return false
        }
    }

    private var enabled: Bool {
        return self.inForeground && self.settings.enabled && NagramiXNetworkSettingsBridge.proxyAutoSwitchEnabled
    }

    private func updateSettings(_ value: ProxySettings) {
        let previous = self.settings
        self.settings = value
        let activeChanged = previous.activeServer != value.activeServer
        let listChanged = previous.servers != value.servers
        if activeChanged || listChanged || previous.enabled != value.enabled {
            if !(activeChanged && self.phase.expectedServer == value.activeServer && !listChanged && value.enabled) {
                self.invalidate()
            }
        }
        self.reevaluate()
    }

    private func updateStatus(_ value: ConnectionStatus) {
        self.status = value
        switch value {
        case .online:
            if !self.needsConnection { self.invalidate() }
        case .waitingForNetwork:
            // No route: retain the selection, cancel failover, do not cycle.
            self.invalidate()
        case .connecting, .updating:
            // Both appear as Connecting in the UI. Repeated events and changes
            // between these states must not restart the user's deadline.
            break
        }
        self.reevaluate()
    }

    private func reevaluate() {
        guard self.enabled, self.settings.activeServer != nil,
              Set(self.settings.servers).count > 1 else {
            self.invalidate()
            return
        }
        guard self.needsConnection, case .idle = self.phase,
              Self.owner == nil || Self.owner === self else { return }
        Self.owner = self
        self.generation &+= 1
        let token = self.generation
        self.cancellation = Atomic<Bool>(value: false)
        self.phase = .waiting(token: token)
        Logger.shared.log("NagramiX", "Proxy connection deadline armed: timeout=\(self.configuredTimeout)")
        self.schedule(after: Double(self.configuredTimeout), token: token) { [weak self] in
            guard let self, self.enabled, self.needsConnection,
                  case let .waiting(phaseToken) = self.phase, phaseToken == token else { return }
            self.deadlineExpired(token: token)
        }
    }

    private func deadlineExpired(token: UInt64) {
        guard token == self.generation, self.enabled, self.needsConnection else { return }
        Logger.shared.log("NagramiX", "Proxy deadline expired; selecting a verified reserve")
        if let active = self.settings.activeServer { self.healthMonitor?.markUnavailable(active) }
        self.phase = .awaitingReserve(token: token)
        self.selectVerifiedReserve(token: token)
    }

    private func selectVerifiedReserve(token: UInt64) {
        guard token == self.generation, self.enabled, self.needsConnection,
              case .awaitingReserve = self.phase, let monitor = self.healthMonitor,
              let active = self.settings.activeServer else { return }
        self.healthSnapshotDisposable?.dispose()
        self.healthSnapshotDisposable = (monitor.availableServers() |> take(1) |> deliverOn(self.queue)).start(next: { [weak self] available in
            guard let self, token == self.generation, self.enabled, self.needsConnection,
                  case .awaitingReserve = self.phase, self.settings.activeServer == active else { return }
            self.healthSnapshotDisposable = nil
            var seen = Set<ProxyServerSettings>()
            let servers = self.settings.servers.filter { seen.insert($0).inserted }
            guard let index = servers.firstIndex(of: active) else { self.invalidate(); return }
            let candidates = Array(servers.dropFirst(index + 1)) + Array(servers.prefix(index))
            if let candidate = candidates.first(where: { available.contains($0) }) {
                self.apply(candidate: candidate, expected: active, token: token)
            } else {
                // No successful fresh ping: keep the current selection and
                // await the shared bounded checker. Never select an unchecked
                // server or add a serial 12-second probe after the deadline.
                monitor.refreshIfNeeded()
            }
        })
    }

    private func apply(candidate: ProxyServerSettings, expected: ProxyServerSettings, token: UInt64) {
        guard token == self.generation, let accountManager = self.accountManager else { return }
        Logger.shared.log("NagramiX", "Switching to a proxy with a fresh successful ping")
        self.phase = .applying(candidate: candidate, token: token)
        self.applyDisposable?.dispose()
        let cancellation = self.cancellation
        self.applyDisposable = (updateProxySettingsInteractively(accountManager: accountManager, { current in
            guard !cancellation.with({ $0 }), NagramiXNetworkSettingsBridge.proxyAutoSwitchEnabled, current.enabled,
                  current.activeServer == expected, current.servers.contains(candidate) else { return current }
            var current = current
            current.activeServer = candidate
            return current
        }) |> deliverOn(self.queue)).start(next: { [weak self] changed in
            guard let self, token == self.generation,
                  case let .applying(phaseCandidate, phaseToken) = self.phase,
                  phaseCandidate == candidate, phaseToken == token else { return }
            self.applyDisposable = nil
            guard changed || self.settings.activeServer == candidate else { self.invalidate(); self.reevaluate(); return }
            self.phase = .connecting(candidate: candidate, token: token)
            self.schedule(after: Double(self.configuredTimeout), token: token) { [weak self] in
                guard let self, self.enabled,
                      case let .connecting(phaseCandidate, phaseToken) = self.phase,
                      phaseCandidate == candidate, phaseToken == token else { return }
                if self.needsConnection {
                    self.deadlineExpired(token: token)
                } else {
                    self.invalidate()
                }
            }
        })
    }

    private func schedule(after timeout: Double, token: UInt64, action: @escaping () -> Void) {
        self.timer?.invalidate()
        let timer = SwiftSignalKit.Timer(timeout: timeout, repeat: false, completion: { [weak self] in
            guard let self, token == self.generation else { return }
            self.timer = nil
            action()
        }, queue: self.queue)
        self.timer = timer
        timer.start()
    }

    private func invalidate() {
        _ = self.cancellation.swap(true)
        self.generation &+= 1
        self.timer?.invalidate()
        self.timer = nil
        self.healthSnapshotDisposable?.dispose()
        self.healthSnapshotDisposable = nil
        self.applyDisposable?.dispose()
        self.applyDisposable = nil
        self.phase = .idle
        if Self.owner === self { Self.owner = nil }
    }
}
