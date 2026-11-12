import Foundation
import UIKit

public final class NagramiXSnowView: UIView {
    public enum Scope: Equatable { case header, messages }
    private let scope: Scope
    private let particles = CAEmitterLayer()
    private var observers: [NSObjectProtocol] = []
    private var visible = false
    private var foreground = true
    private var signature: [Double]?
    private static var images: [String: UIImage] = [:]

    public init(scope: Scope) {
        self.scope = scope
        super.init(frame: .zero)
        self.isUserInteractionEnabled = false
        self.isAccessibilityElement = false
        self.accessibilityElementsHidden = true
        self.clipsToBounds = true
        self.autoresizingMask = [.flexibleWidth, .flexibleHeight]
        self.particles.emitterShape = .rectangle
        self.particles.emitterMode = .volume
        self.particles.renderMode = .unordered
        self.particles.birthRate = 0.0
        self.particles.speed = 0.0
        self.particles.seed = UInt32.random(in: 0...UInt32.max)
        self.layer.addSublayer(self.particles)
        for name in [NagramiXSnowSettings.changedNotification, .NSProcessInfoPowerStateDidChange, UIAccessibility.reduceMotionStatusDidChangeNotification, UIApplication.willResignActiveNotification, UIApplication.didBecomeActiveNotification] {
            self.observers.append(NotificationCenter.default.addObserver(forName: name, object: nil, queue: .main) { [weak self] note in
                guard let self else { return }
                if note.name == UIApplication.willResignActiveNotification { self.foreground = false }
                if note.name == UIApplication.didBecomeActiveNotification { self.foreground = true }
                self.refresh()
            })
        }
        self.refresh()
    }

    required init?(coder: NSCoder) { return nil }
    deinit { for observer in self.observers { NotificationCenter.default.removeObserver(observer) } }

    public func setVisible(_ value: Bool) {
        guard self.visible != value else { return }
        self.visible = value
        self.refresh()
    }

    public func bind(to parent: UIView, above background: UIView? = nil) {
        if self.superview !== parent {
            self.removeFromSuperview()
            if let background, background.superview === parent { parent.insertSubview(self, aboveSubview: background) }
            else if background != nil { parent.insertSubview(self, at: 0) }
            else { parent.addSubview(self) }
        } else if background == nil {
            parent.bringSubviewToFront(self)
        }
        if self.frame != parent.bounds { self.frame = parent.bounds }
        self.refresh()
    }

    public override func didMoveToWindow() { super.didMoveToWindow(); self.refresh() }
    public override func layoutSubviews() { super.layoutSubviews(); self.refresh() }

    private func refresh() {
        let config = NagramiXSnowSettings.current
        let allowed = config.enabled && (self.scope == .header || config.inChats)
            && self.visible && self.foreground && self.window != nil
            && !ProcessInfo.processInfo.isLowPowerModeEnabled && !UIAccessibility.isReduceMotionEnabled
            && self.bounds.width.isFinite && self.bounds.height.isFinite && !self.bounds.isEmpty
        CATransaction.begin()
        CATransaction.setDisableActions(true)
        defer { CATransaction.commit() }
        self.isHidden = !allowed
        guard allowed else {
            self.particles.birthRate = 0.0
            self.particles.speed = 0.0
            self.particles.emitterCells = nil
            self.signature = nil
            return
        }
        self.particles.frame = self.bounds
        self.particles.emitterPosition = CGPoint(x: self.bounds.midX, y: self.bounds.midY)
        self.particles.emitterSize = self.bounds.size
        let reference = self.window?.bounds.size ?? self.bounds.size
        let area = self.scope == .header ? 1.0 : max(0.12, min(1.0, (self.bounds.width * self.bounds.height) / max(1.0, reference.width * reference.height)))
        let scale = max(1.0, self.traitCollection.displayScale)
        let signature = [Double(config.density), Double(area), Double(scale)]
        if self.signature != signature {
            let wasStopped = self.signature == nil
            self.signature = signature
            let total = Float(self.scope == .header ? 18.0 : 75.0 * Double(area)) * Float(config.density) / 100.0
            let lifetime: Float = self.scope == .header ? 2.05 : 4.0
            let cells = [CGFloat(2.5), CGFloat(1.0)].map { diameter -> CAEmitterCell in
                let cell = CAEmitterCell()
                cell.contents = Self.image(diameter: diameter, scale: scale).cgImage
                cell.contentsScale = scale
                cell.color = UIColor(white: 1.0, alpha: 0.9).cgColor
                cell.birthRate = total * 0.5
                cell.lifetime = lifetime
                cell.lifetimeRange = self.scope == .header ? 0.05 : 1.0
                cell.velocity = 44.0
                cell.velocityRange = 4.0
                cell.emissionLongitude = .pi / 2.0
                cell.emissionRange = .pi / 9.0 * 2.0
                cell.alphaSpeed = -1.0 / lifetime
                return cell
            }
            if wasStopped {
                self.particles.beginTime = self.layer.convertTime(CACurrentMediaTime(), from: nil)
                self.particles.timeOffset = 0.0
            }
            self.particles.emitterCells = cells
        }
        self.particles.speed = 1.0
        self.particles.birthRate = 1.0
    }

    private static func image(diameter: CGFloat, scale: CGFloat) -> UIImage {
        let key = "\(diameter):\(scale)"
        if let image = self.images[key] { return image }
        let side = ceil(diameter) + 2.0
        let format = UIGraphicsImageRendererFormat()
        format.opaque = false
        format.scale = scale
        let image = UIGraphicsImageRenderer(size: CGSize(width: side, height: side), format: format).image { renderer in
            renderer.cgContext.setFillColor(UIColor.white.cgColor)
            renderer.cgContext.fillEllipse(in: CGRect(x: (side - diameter) * 0.5, y: (side - diameter) * 0.5, width: diameter, height: diameter))
        }
        self.images[key] = image
        return image
    }
}
