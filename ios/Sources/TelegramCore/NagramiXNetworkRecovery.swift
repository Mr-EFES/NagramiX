import Foundation
import SwiftSignalKit

/// One recovery lease per account directory and process role. A replacement
/// network retires the previous lease before its queued work can change proxies.
final class NagramiXNetworkRecovery: Disposable {
    private struct Key: Hashable {
        let basePath: String
        let allowsFailover: Bool
    }
    private final class WeakOwner {
        weak var value: NagramiXNetworkRecovery?
        let token: UUID
        init(_ value: NagramiXNetworkRecovery) { self.value = value; self.token = value.token }
    }
    private static let lock = NSLock()
    private static var owners: [Key: WeakOwner] = [:]
    private static let queue = Queue(name: "org.nagramix.network-recovery")

    private let key: Key
    private let token = UUID()
    private let valid = Atomic<Bool>(value: true)
    private let disposalStarted = Atomic<Bool>(value: false)
    private let keepsConnection = Atomic<Bool>(value: false)
    private weak var network: Network?
    private let failover = NagramiXProxyFailoverController()
    private var keepDisposable: Disposable?
    private var observer: NSObjectProtocol?
    private let reconnect = MetaDisposable()

    static func attach(basePath: String, accountManager: AccountManager<TelegramAccountManagerTypes>, network: Network, allowsFailover: Bool) -> NagramiXNetworkRecovery {
        let recovery = NagramiXNetworkRecovery(basePath: basePath, network: network, allowsFailover: allowsFailover)
        self.lock.lock()
        let previous = self.owners[recovery.key]?.value
        // The queued controller stop is not an admission barrier. Revoke the
        // old lease synchronously, including transactions already in Postbox.
        if let previous { _ = previous.valid.swap(false); _ = previous.keepsConnection.swap(false) }
        self.owners[recovery.key] = WeakOwner(recovery)
        self.lock.unlock()
        previous?.dispose()
        self.queue.async { [weak recovery, weak network] in
            guard let recovery, let network, recovery.valid.with({ $0 }) else { return }
            recovery.begin(accountManager: accountManager, network: network)
        }
        return recovery
    }

    private init(basePath: String, network: Network, allowsFailover: Bool) {
        self.key = Key(basePath: basePath, allowsFailover: allowsFailover)
        self.network = network
    }

    private func begin(accountManager: AccountManager<TelegramAccountManagerTypes>, network: Network) {
        self.observer = NotificationCenter.default.addObserver(forName: Notification.Name("NagramiXDnsSettingsChanged"), object: nil, queue: nil) { [weak self] _ in
            Self.queue.async { [weak self] in
                guard let self, self.valid.with({ $0 }), let network = self.network else { return }
                let valid = self.valid
                self.reconnect.set(network.reconnectForNagramiXDnsChange(shouldApply: { valid.with { $0 } }))
            }
        }
        let valid = self.valid
        let keepsConnection = self.keepsConnection
        self.keepDisposable = (network.shouldKeepConnection.get()
        |> distinctUntilChanged
        |> deliverOn(Self.queue)).start(next: { [weak self, weak network] keep in
            guard let self, let network, valid.with({ $0 }) else { return }
            _ = keepsConnection.swap(keep)
            guard self.key.allowsFailover else { return }
            if keep {
                self.failover.start(accountManager: accountManager, network: network, isCurrentNetwork: {
                    valid.with { $0 } && keepsConnection.with { $0 }
                })
            } else {
                self.failover.stop()
            }
        })
    }

    func dispose() {
        guard !self.disposalStarted.swap(true) else { return }
        _ = self.valid.swap(false)
        _ = self.keepsConnection.swap(false)
        self.unregister()
        Self.queue.async { self.cleanup() }
    }

    private func unregister() {
        Self.lock.lock()
        if Self.owners[self.key]?.token == self.token { Self.owners.removeValue(forKey: self.key) }
        Self.lock.unlock()
    }

    private func cleanup() {
        self.keepDisposable?.dispose(); self.keepDisposable = nil
        self.reconnect.dispose()
        if let observer = self.observer { NotificationCenter.default.removeObserver(observer) }
        self.observer = nil
        self.failover.stop()
    }

    deinit {
        // Account-owned disposables normally stop us first. This fallback must
        // not enqueue a closure retaining an object already in deinit.
        _ = self.valid.swap(false)
        _ = self.keepsConnection.swap(false)
        self.unregister()
        self.cleanup()
    }
}
