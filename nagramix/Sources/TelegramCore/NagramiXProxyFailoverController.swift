import Foundation
import SwiftSignalKit
import MtProtoKit

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

/// Queue-confined state machine. Every callback carries a generation token,
/// therefore a stale timer can never override a manual proxy selection.
final class NagramiXProxyFailoverController {
    private enum Phase {
        case idle
        case waiting(origin: ProxyServerSettings, token: UInt64)
        case checking(origin: ProxyServerSettings, candidates: [ProxyServerSettings], index: Int, token: UInt64)
        case applying(origin: ProxyServerSettings, candidates: [ProxyServerSettings], index: Int, candidate: ProxyServerSettings, token: UInt64)
        case connecting(origin: ProxyServerSettings, candidates: [ProxyServerSettings], index: Int, candidate: ProxyServerSettings, token: UInt64)

        var expectedServer: ProxyServerSettings? {
            switch self {
            case let .applying(_, _, _, candidate, _), let .connecting(_, _, _, candidate, _):
                return candidate
            default:
                return nil
            }
        }
    }

    private static let sharedQueue = Queue(name: "org.nagramix.proxy-failover")
    private static weak var owner: NagramiXProxyFailoverController?
    private let queue = NagramiXProxyFailoverController.sharedQueue
    private var accountManager: AccountManager<TelegramAccountManagerTypes>?
    private var network: Network?
    private var settingsDisposable: Disposable?
    private var statusDisposable: Disposable?
    private var applyDisposable: Disposable?
    private var probeDisposable: MTDisposable?
    private var observer: NSObjectProtocol?
    private var timer: SwiftSignalKit.Timer?
    private var settings: ProxySettings = .defaultSettings
    private var status: ConnectionStatus = .waitingForNetwork
    private var phase: Phase = .idle
    private var generation: UInt64 = 0
    private var suppressedServer: ProxyServerSettings?

    init() {
    }

    func start(accountManager: AccountManager<TelegramAccountManagerTypes>, network: Network) {
        self.queue.async { [weak self] in
            guard let self else { return }
            self.stopInternal()
            self.accountManager = accountManager
            self.network = network
            self.settingsDisposable = (accountManager.sharedData(keys: [SharedDataKeys.proxySettings])
            |> deliverOn(self.queue)).start(next: { [weak self] data in
                self?.updateSettings(data.entries[SharedDataKeys.proxySettings]?.get(ProxySettings.self) ?? .defaultSettings)
            })
            self.statusDisposable = (network.connectionStatus
            |> deliverOn(self.queue)).start(next: { [weak self] status in
                self?.updateStatus(status)
            })
            self.observer = NotificationCenter.default.addObserver(forName: NagramiXNetworkSettingsBridge.changedNotification, object: nil, queue: nil, using: { [weak self] _ in
                self?.queue.async {
                    guard let self else { return }
                    if !NagramiXNetworkSettingsBridge.proxyAutoSwitchEnabled {
                        self.invalidate(suppressCurrent: false)
                    }
                    self.reevaluate()
                }
            })
        }
    }

    func stop() {
        self.queue.async { [weak self] in self?.stopInternal() }
    }

    private func stopInternal() {
        self.invalidate(suppressCurrent: false)
        self.settingsDisposable?.dispose()
        self.settingsDisposable = nil
        self.statusDisposable?.dispose()
        self.statusDisposable = nil
        if let observer = self.observer {
            NotificationCenter.default.removeObserver(observer)
            self.observer = nil
        }
        self.accountManager = nil
        self.network = nil
    }

    private func updateSettings(_ value: ProxySettings) {
        let previous = self.settings
        self.settings = value
        let activeChanged = previous.activeServer != value.activeServer
        let listChanged = previous.servers != value.servers
        if activeChanged || listChanged || previous.enabled != value.enabled {
            let expected = self.phase.expectedServer
            if !(activeChanged && expected == value.activeServer && !listChanged && value.enabled) {
                self.suppressedServer = nil
                self.invalidate(suppressCurrent: false)
            }
        }
        self.reevaluate()
    }

    private func updateStatus(_ value: ConnectionStatus) {
        self.status = value
        switch value {
        case .online:
            self.suppressedServer = nil
            self.invalidate(suppressCurrent: false)
        case let .connecting(_, hasProxyIssues):
            if hasProxyIssues {
                if case let .connecting(origin, candidates, index, candidate, token) = self.phase,
                   self.settings.activeServer == candidate,
                   token == self.generation {
                    // ConnectionsManager has confirmed that the candidate itself
                    // cannot establish a proxy connection. Do not wait for the
                    // secondary timeout and never retry this candidate in the
                    // same failover generation.
                    self.check(origin: origin, candidates: candidates, index: index + 1, token: token)
                }
            } else {
                switch self.phase {
                case .applying(_, _, _, _, _), .connecting(_, _, _, _, _):
                    break
                default:
                    self.suppressedServer = nil
                    self.invalidate(suppressCurrent: false)
                }
            }
        case .waitingForNetwork, .updating:
            // Interface changes are not proxy failures.
            self.suppressedServer = nil
            self.invalidate(suppressCurrent: false)
        }
        self.reevaluate()
    }

    private func reevaluate() {
        guard NagramiXNetworkSettingsBridge.proxyAutoSwitchEnabled,
              self.settings.enabled,
              let active = self.settings.activeServer else {
            self.invalidate(suppressCurrent: false)
            return
        }
        let servers = self.uniqueServers(self.settings.servers)
        guard servers.count > 1 else {
            self.invalidate(suppressCurrent: false)
            return
        }
        guard case let .connecting(_, hasIssues) = self.status, hasIssues,
              self.suppressedServer != active,
              case .idle = self.phase,
              NagramiXProxyFailoverController.owner == nil || NagramiXProxyFailoverController.owner === self else {
            return
        }
        NagramiXProxyFailoverController.owner = self
        self.generation &+= 1
        let token = self.generation
        self.phase = .waiting(origin: active, token: token)
        self.schedule(after: Double(NagramiXNetworkSettingsBridge.proxyAutoSwitchTimeout), token: token) { [weak self] in
            guard let self,
                  case let .waiting(origin, phaseToken) = self.phase,
                  phaseToken == token,
                  self.settings.activeServer == origin,
                  case let .connecting(_, stillFailing) = self.status,
                  stillFailing else { return }
            self.begin(origin: origin, servers: servers, token: token)
        }
    }

    private func begin(origin: ProxyServerSettings, servers: [ProxyServerSettings], token: UInt64) {
        guard token == self.generation, let index = servers.firstIndex(of: origin) else {
            self.invalidate(suppressCurrent: true)
            return
        }
        let candidates = (Array(servers[(index + 1)...]) + (index > 0 ? Array(servers[..<index]) : [])).filter { $0 != origin }
        guard !candidates.isEmpty else {
            self.invalidate(suppressCurrent: true)
            return
        }
        self.check(origin: origin, candidates: candidates, index: 0, token: token)
    }

    private func check(origin: ProxyServerSettings, candidates: [ProxyServerSettings], index: Int, token: UInt64) {
        guard token == self.generation, let network = self.network else { return }
        guard index < candidates.count else {
            self.invalidate(suppressCurrent: true)
            return
        }
        let candidate = candidates[index]
        self.phase = .checking(origin: origin, candidates: candidates, index: index, token: token)
        self.probeDisposable?.dispose()
        self.probeDisposable = nil
        self.schedule(after: 12.0, token: token) { [weak self] in
            guard let self else { return }
            self.probeDisposable?.dispose()
            self.probeDisposable = nil
            self.check(origin: origin, candidates: candidates, index: index + 1, token: token)
        }
        self.probeDisposable = MTProxyConnectivity.pingProxy(with: network.context, datacenterId: network.datacenterId, settings: candidate.mtProxySettings).start(next: { [weak self] result in
            self?.queue.async {
                guard let self, token == self.generation,
                      case let .checking(_, _, phaseIndex, phaseToken) = self.phase,
                      phaseIndex == index, phaseToken == token else { return }
                self.cancelTimer()
                self.probeDisposable?.dispose()
                self.probeDisposable = nil
                guard let status = result as? MTProxyConnectivityStatus, status.reachable else {
                    self.check(origin: origin, candidates: candidates, index: index + 1, token: token)
                    return
                }
                self.apply(origin: origin, candidates: candidates, index: index, candidate: candidate, token: token)
            }
        }, completed: { [weak self] in
            self?.queue.async {
                guard let self, token == self.generation,
                      case let .checking(_, _, phaseIndex, phaseToken) = self.phase,
                      phaseIndex == index, phaseToken == token else { return }
                self.cancelTimer()
                self.probeDisposable = nil
                self.check(origin: origin, candidates: candidates, index: index + 1, token: token)
            }
        })
    }

    private func apply(origin: ProxyServerSettings, candidates: [ProxyServerSettings], index: Int, candidate: ProxyServerSettings, token: UInt64) {
        guard token == self.generation, let accountManager = self.accountManager else { return }
        self.phase = .applying(origin: origin, candidates: candidates, index: index, candidate: candidate, token: token)
        self.applyDisposable?.dispose()
        self.applyDisposable = (updateProxySettingsInteractively(accountManager: accountManager, { current in
            var current = current
            current.enabled = true
            current.activeServer = candidate
            return current
        }) |> deliverOn(self.queue)).start(next: { [weak self] changed in
            guard let self, token == self.generation,
                  case let .applying(_, _, phaseIndex, phaseCandidate, phaseToken) = self.phase,
                  phaseIndex == index, phaseCandidate == candidate, phaseToken == token else { return }
            self.applyDisposable = nil
            if !changed && self.settings.activeServer != candidate {
                self.check(origin: origin, candidates: candidates, index: index + 1, token: token)
                return
            }
            self.phase = .connecting(origin: origin, candidates: candidates, index: index, candidate: candidate, token: token)
            self.schedule(after: 12.0, token: token) { [weak self] in
                guard let self else { return }
                if case .online = self.status, self.settings.activeServer == candidate {
                    self.invalidate(suppressCurrent: false)
                } else {
                    self.check(origin: origin, candidates: candidates, index: index + 1, token: token)
                }
            }
        })
    }

    private func schedule(after timeout: Double, token: UInt64, action: @escaping () -> Void) {
        self.cancelTimer()
        let timer = SwiftSignalKit.Timer(timeout: timeout, repeat: false, completion: { [weak self] in
            guard let self, token == self.generation else { return }
            self.timer = nil
            action()
        }, queue: self.queue)
        self.timer = timer
        timer.start()
    }

    private func cancelTimer() {
        self.timer?.invalidate()
        self.timer = nil
    }

    private func invalidate(suppressCurrent: Bool) {
        let active = self.settings.activeServer
        self.generation &+= 1
        self.cancelTimer()
        self.probeDisposable?.dispose()
        self.probeDisposable = nil
        self.applyDisposable?.dispose()
        self.applyDisposable = nil
        self.phase = .idle
        self.suppressedServer = suppressCurrent ? active : nil
        if NagramiXProxyFailoverController.owner === self {
            NagramiXProxyFailoverController.owner = nil
        }
    }

    private func uniqueServers(_ servers: [ProxyServerSettings]) -> [ProxyServerSettings] {
        var result: [ProxyServerSettings] = []
        var seen = Set<ProxyServerSettings>()
        for server in servers where seen.insert(server).inserted {
            result.append(server)
        }
        return result
    }
}
