import Foundation
import UIKit

// Decorative CA animations leave the text, caret, model transform and layout intact.
public final class NagramiXTypingAnimation {
    private final class Target {
        weak var view: UIView?
        init(_ view: UIView) { self.view = view }
    }
    private var targets: [Target] = []
    private var observers: [NSObjectProtocol] = []
    private var lastTimestamp: Double = -Double.greatestFiniteMagnitude
    private var glowLayer: CALayer?
    private var glowSize: CGSize = .zero
    private var glowColor: UIColor?
    private var glowScale: CGFloat = 0.0
    private static let keys = ["nagramix.typing.scale", "nagramix.typing.offset", "nagramix.typing.shake", "nagramix.typing.glow"]

    public init() {
        for name in [NagramiXTypingSettings.changedNotification, .NSProcessInfoPowerStateDidChange, UIAccessibility.reduceMotionStatusDidChangeNotification, UIApplication.didEnterBackgroundNotification] {
            self.observers.append(NotificationCenter.default.addObserver(forName: name, object: nil, queue: .main) { [weak self] _ in self?.stop() })
        }
    }

    deinit {
        for observer in self.observers { NotificationCenter.default.removeObserver(observer) }
        self.stop()
    }

    public func stop() {
        for target in self.targets {
            for key in Self.keys { target.view?.layer.removeAnimation(forKey: key) }
        }
        self.targets.removeAll()
        self.glowLayer?.removeAnimation(forKey: Self.keys[3])
        self.glowLayer?.removeFromSuperlayer()
        self.lastTimestamp = -Double.greatestFiniteMagnitude
    }

    public func play(target: UIView, companions: [UIView] = [], color: UIColor) {
        let value = NagramiXTypingSettings.current
        guard value.enabled, !ProcessInfo.processInfo.isLowPowerModeEnabled, !UIAccessibility.isReduceMotionEnabled,
              target.window != nil, !target.bounds.isEmpty else { self.stop(); return }
        let timestamp = CACurrentMediaTime()
        guard timestamp - self.lastTimestamp >= value.minimumInterval else { return }
        self.stop()
        self.lastTimestamp = timestamp
        let views = [target] + (value.preset == .panelWave ? companions : [])
        self.targets = views.map(Target.init)
        let intensity = value.intensity / 100.0
        switch value.preset {
        case .pulse:
            self.animate(target.layer, path: "transform.scale", values: [0.0, 0.02 + 0.06 * intensity, 0.0], key: 0, duration: value.duration)
        case .wave, .panelWave:
            for view in views { self.animate(view.layer, path: "transform.translation.y", values: [0.0, -(1.0 + 4.0 * intensity), 0.0], key: 1, duration: value.duration) }
        case .shake:
            let amount = 1.0 + 3.0 * intensity
            self.animate(target.layer, path: "transform.translation.x", values: [0.0, -amount, amount, -amount * 0.5, 0.0], key: 2, duration: value.duration)
        case .neon:
            self.glow(around: target, color: color, strength: value.glow / 100.0, duration: value.duration)
        case .custom:
            self.animate(target.layer, path: "transform.scale", values: [0.0, 0.04 * value.scale / 100.0 * intensity, 0.0], key: 0, duration: value.duration)
            self.animate(target.layer, path: "transform.translation.y", values: [0.0, -4.0 * value.offset / 100.0 * intensity, 0.0], key: 1, duration: value.duration)
            if value.glow > 0.0 { self.glow(around: target, color: color, strength: value.glow / 100.0 * intensity, duration: value.duration) }
        }
    }

    private func animate(_ layer: CALayer, path: String, values: [Double], key: Int, duration: Double) {
        let animation = CAKeyframeAnimation(keyPath: path)
        animation.values = values
        animation.duration = duration
        animation.isAdditive = true
        animation.timingFunction = CAMediaTimingFunction(name: .easeInEaseOut)
        layer.add(animation, forKey: Self.keys[key])
    }

    private func glow(around target: UIView, color: UIColor, strength: Double, duration: Double) {
        guard let parent = target.superview else { return }
        let layer: CALayer
        if let current = self.glowLayer { layer = current }
        else { layer = CALayer(); layer.opacity = 0.0; self.glowLayer = layer }
        if layer.superlayer !== parent.layer { layer.removeFromSuperlayer(); parent.layer.insertSublayer(layer, below: target.layer) }
        let size = target.bounds.size
        let padding: CGFloat = 12.0
        let scale = max(1.0, target.traitCollection.displayScale)
        if self.glowSize != size || self.glowColor?.isEqual(color) != true || self.glowScale != scale {
            self.glowSize = size; self.glowColor = color; self.glowScale = scale
            let format = UIGraphicsImageRendererFormat()
            format.scale = scale
            format.opaque = false
            layer.contents = UIGraphicsImageRenderer(size: CGSize(width: size.width + padding * 2.0, height: size.height + padding * 2.0), format: format).image { renderer in
                let context = renderer.cgContext
                context.setShadow(offset: .zero, blur: padding * 0.8, color: color.cgColor)
                context.setFillColor(color.withAlphaComponent(0.6).cgColor)
                context.addPath(UIBezierPath(roundedRect: CGRect(x: padding, y: padding, width: size.width, height: size.height), cornerRadius: min(size.height * 0.5, 20.0)).cgPath)
                context.fillPath()
            }.cgImage
            layer.contentsScale = scale
        }
        layer.frame = target.frame.insetBy(dx: -padding, dy: -padding)
        let animation = CAKeyframeAnimation(keyPath: "opacity")
        animation.values = [0.0, 0.25 + 0.6 * strength, 0.0]
        animation.duration = duration * 1.4
        layer.add(animation, forKey: Self.keys[3])
    }
}
