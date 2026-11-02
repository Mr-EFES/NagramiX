import Foundation
import UIKit
import AVFoundation
import UIKitRuntimeUtils
import NagramiXMediaSettings

// Only explicitly opted-in chat/media layers use this adapter. Other secure
// UI, paid previews and one-time media keep their native protection.
private final class NagramiXCaptureProtectionRegistry {
    static let shared = NagramiXCaptureProtectionRegistry()

    private struct Entry {
        weak var layer: CALayer?
        let required: Bool
        let allowsBypass: Bool
        let video: Bool
    }
    private var entries: [ObjectIdentifier: Entry] = [:]
    private var registrations = 0
    private var bypass = NagramiXPrivacySettings.current.bypassScreenshots
    private var observer: NSObjectProtocol?

    private init() {
        self.observer = NotificationCenter.default.addObserver(forName: NagramiXPrivacySettings.changedNotification, object: nil, queue: .main) { [weak self] _ in
            guard let self else { return }
            let bypass = NagramiXPrivacySettings.current.bypassScreenshots
            guard bypass != self.bypass else { return }
            self.bypass = bypass
            self.entries = self.entries.filter { $0.value.layer != nil }
            for entry in self.entries.values { self.apply(entry) }
        }
    }

    deinit {
        if let observer = self.observer { NotificationCenter.default.removeObserver(observer) }
    }

    func update(_ layer: CALayer, required: Bool, allowsBypass: Bool, video: Bool) {
        assert(Thread.isMainThread)
        self.registrations &+= 1
        if self.registrations % 64 == 0 {
            self.entries = self.entries.filter { $0.value.layer != nil }
        }
        let entry = Entry(layer: layer, required: required, allowsBypass: allowsBypass, video: video)
        self.entries[ObjectIdentifier(layer)] = entry
        self.apply(entry)
    }

    private func apply(_ entry: Entry) {
        guard let layer = entry.layer else { return }
        let required = NagramiXPrivacySettings.current.requiresScreenshotProtection(entry.required, allowsBypass: entry.allowsBypass)
        if entry.video {
            if #available(iOS 13.0, *), let layer = layer as? AVSampleBufferDisplayLayer {
                layer.preventsCapture = required
            }
        } else {
            setLayerDisableScreenshots(layer, required)
        }
    }
}

public func nagramiXSetLayerDisableScreenshots(_ layer: CALayer, _ required: Bool, allowsBypass: Bool = true) {
    NagramiXCaptureProtectionRegistry.shared.update(layer, required: required, allowsBypass: allowsBypass, video: false)
}

public func nagramiXSetVideoCaptureProtection(_ layer: AVSampleBufferDisplayLayer, _ required: Bool, allowsBypass: Bool) {
    NagramiXCaptureProtectionRegistry.shared.update(layer, required: required, allowsBypass: allowsBypass, video: true)
}
