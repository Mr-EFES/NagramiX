import UIKit

public struct NagramiXGlassSliderGeometry {
    public static let thumbDiameter: CGFloat = 28.0
    // The native legacy control puts its thumb center 7pt from each edge.
    public static let thumbInset: CGFloat = thumbDiameter * 0.5 - 7.0
    public let left: CGFloat
    public let right: CGFloat
    public var width: CGFloat { max(1.0, self.right - self.left) }

    public init(width: CGFloat, leftInset: CGFloat, rightInset: CGFloat) {
        self.left = leftInset + 16.0
        self.right = max(self.left + 1.0, width - rightInset - 15.0)
    }

    public func sliderFrame(headerHeight: CGFloat) -> CGRect {
        return self.sliderFrame(y: headerHeight + 14.0)
    }

    public func sliderFrame(y: CGFloat) -> CGRect {
        return CGRect(x: self.left + Self.thumbInset, y: y, width: max(1.0, self.width - Self.thumbInset * 2.0), height: 44.0)
    }
}

public final class NagramiXGlassSliderThumbView: UIView {
    private let effectView: UIVisualEffectView?
    private let sheenLayer = CAGradientLayer()
    private let rimLayer = CAShapeLayer()
    private var currentIsDark: Bool?

    public static let transparentImage: UIImage = {
        let size = CGSize(width: NagramiXGlassSliderGeometry.thumbDiameter, height: NagramiXGlassSliderGeometry.thumbDiameter)
        let format = UIGraphicsImageRendererFormat()
        format.opaque = false
        return UIGraphicsImageRenderer(size: size, format: format).image { context in
            context.cgContext.clear(CGRect(origin: .zero, size: size))
        }
    }()

    public override init(frame: CGRect) {
        if #available(iOS 26.0, *) {
            let effect = UIGlassEffect(style: .clear)
            effect.isInteractive = false
            self.effectView = UIVisualEffectView(effect: effect)
        } else {
            self.effectView = nil
        }
        super.init(frame: frame)
        self.isOpaque = false
        self.isUserInteractionEnabled = false
        self.isAccessibilityElement = false
        self.accessibilityElementsHidden = true
        if let effectView = self.effectView {
            effectView.isUserInteractionEnabled = false
            effectView.clipsToBounds = true
            self.addSubview(effectView)
        }
        self.sheenLayer.startPoint = CGPoint(x: 0.15, y: 0.0)
        self.sheenLayer.endPoint = CGPoint(x: 0.85, y: 1.0)
        self.sheenLayer.masksToBounds = true
        self.sheenLayer.locations = [0.0, 0.38, 0.7, 1.0]
        self.layer.addSublayer(self.sheenLayer)
        self.rimLayer.fillColor = UIColor.clear.cgColor
        self.rimLayer.lineWidth = 0.7
        self.layer.addSublayer(self.rimLayer)
        self.layer.shadowColor = UIColor.black.cgColor
        self.layer.shadowOffset = CGSize(width: 0.0, height: 1.0)
        self.layer.shadowRadius = 2.0
        self.update(isDark: true)
    }

    public required init?(coder: NSCoder) {
        return nil
    }

    public func update(isDark: Bool) {
        guard self.currentIsDark != isDark else { return }
        self.currentIsDark = isDark
        self.effectView?.overrideUserInterfaceStyle = isDark ? .dark : .light
        // The center remains transparent, including the older-system fallback.
        self.backgroundColor = UIColor(white: isDark ? 1.0 : 0.0, alpha: 0.025)
        self.sheenLayer.colors = [0.18, 0.015, 0.0, 0.12].map { UIColor(white: 1.0, alpha: $0).cgColor }
        self.rimLayer.strokeColor = UIColor(white: 1.0, alpha: isDark ? 0.7 : 0.9).cgColor
        self.layer.shadowOpacity = isDark ? 0.3 : 0.18
    }

    public override func layoutSubviews() {
        super.layoutSubviews()
        guard self.bounds.width > 1.0, self.bounds.height > 1.0 else { return }
        CATransaction.begin()
        CATransaction.setDisableActions(true)
        let radius = min(self.bounds.width, self.bounds.height) * 0.5
        self.layer.cornerRadius = radius
        self.effectView?.frame = self.bounds
        self.effectView?.layer.cornerRadius = radius
        self.sheenLayer.frame = self.bounds
        self.sheenLayer.cornerRadius = radius
        self.rimLayer.frame = self.bounds
        self.rimLayer.path = UIBezierPath(ovalIn: self.bounds.insetBy(dx: 0.5, dy: 0.5)).cgPath
        self.layer.shadowPath = UIBezierPath(ovalIn: self.bounds).cgPath
        CATransaction.commit()
    }
}

/// Native control semantics with the same glass decoration as percentage rows.
public final class NagramiXGlassSlider: UISlider {
    /// Opt-in for discrete controls. Other sliders retain native VoiceOver steps.
    public var accessibilityStep: Float?

    public override func accessibilityIncrement() {
        guard let step = self.accessibilityStep, step.isFinite, step > 0 else {
            super.accessibilityIncrement()
            return
        }
        self.adjustAccessibilityValue(by: step)
    }

    public override func accessibilityDecrement() {
        guard let step = self.accessibilityStep, step.isFinite, step > 0 else {
            super.accessibilityDecrement()
            return
        }
        self.adjustAccessibilityValue(by: -step)
    }

    private func adjustAccessibilityValue(by delta: Float) {
        guard self.isEnabled, self.value.isFinite else { return }
        let value = min(self.maximumValue, max(self.minimumValue, self.value + delta))
        guard value != self.value else { return }
        self.setValue(value, animated: true)
        self.sendActions(for: .valueChanged)
    }

    private let glassThumbView = NagramiXGlassSliderThumbView(frame: .zero)
    private let trackBackgroundView = UIView()
    private let trackForegroundView = UIView()

    public override init(frame: CGRect) {
        super.init(frame: frame)
        self.configureGlass()
    }

    public required init?(coder: NSCoder) {
        super.init(coder: coder)
        self.configureGlass()
    }

    private func configureGlass() {
        self.isOpaque = false
        self.minimumTrackTintColor = .clear
        self.maximumTrackTintColor = .clear
        self.setThumbImage(NagramiXGlassSliderThumbView.transparentImage, for: .normal)
        self.setThumbImage(NagramiXGlassSliderThumbView.transparentImage, for: .highlighted)
        self.setThumbImage(NagramiXGlassSliderThumbView.transparentImage, for: .disabled)
        for track in [self.trackBackgroundView, self.trackForegroundView] {
            track.isUserInteractionEnabled = false
            track.isAccessibilityElement = false
            track.layer.cornerRadius = 1.0
            self.addSubview(track)
        }
        self.addSubview(self.glassThumbView)
    }

    public func updateAppearance(isDark: Bool, background: UIColor, foreground: UIColor) {
        self.trackBackgroundView.backgroundColor = background
        self.trackForegroundView.backgroundColor = foreground
        self.glassThumbView.update(isDark: isDark)
        self.setNeedsLayout()
    }

    public override var intrinsicContentSize: CGSize {
        let size = super.intrinsicContentSize
        return CGSize(width: size.width, height: max(44.0, size.height))
    }

    public override var value: Float {
        didSet { self.setNeedsLayout() }
    }

    public override var isEnabled: Bool {
        didSet { self.setNeedsLayout() }
    }

    public override func setValue(_ value: Float, animated: Bool) {
        if animated { self.layoutIfNeeded() }
        super.setValue(value, animated: false)
        self.setNeedsLayout()
        if animated {
            // The native thumb is clear. Animate its decoration and track together.
            UIView.animate(withDuration: 0.2, delay: 0.0, options: [.beginFromCurrentState, .allowUserInteraction], animations: {
                self.layoutIfNeeded()
            }, completion: nil)
        }
    }

    public override func layoutSubviews() {
        super.layoutSubviews()
        let nativeTrack = self.trackRect(forBounds: self.bounds)
        let thumb = self.thumbRect(forBounds: self.bounds, trackRect: nativeTrack, value: self.value)
        self.glassThumbView.frame = thumb
        let track = CGRect(x: thumb.width * 0.5, y: floor((self.bounds.height - 2.0) * 0.5), width: max(0.0, self.bounds.width - thumb.width), height: 2.0)
        self.trackBackgroundView.frame = track
        let range = self.maximumValue - self.minimumValue
        let fraction = range > 0 && self.value.isFinite ? CGFloat(min(1.0, max(0.0, (self.value - self.minimumValue) / range))) : 0.0
        let isRTL = self.effectiveUserInterfaceLayoutDirection == .rightToLeft
        let filled = track.width * fraction
        self.trackForegroundView.frame = CGRect(x: isRTL ? track.maxX - filled : track.minX, y: track.minY, width: filled, height: track.height)
        for decoration in [self.glassThumbView, self.trackBackgroundView, self.trackForegroundView] {
            decoration.alpha = self.isEnabled ? 1.0 : 0.35
        }
    }
}
