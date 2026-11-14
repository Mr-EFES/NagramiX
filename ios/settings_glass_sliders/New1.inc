import UIKit
import LegacyComponents
import NagramiXCore

class NagramiXLegacyGlassSliderView: TGPhotoEditorSliderView {
    private let glassThumbView = NagramiXGlassSliderThumbView(frame: .zero)
    private let trackBackgroundView = UIView()
    private let trackForegroundView = UIView()

    override init(frame: CGRect) {
        super.init(frame: frame)
        self.configureGlass()
    }

    required init?(coder: NSCoder) {
        super.init(coder: coder)
        self.configureGlass()
    }

    private func configureGlass() {
        self.isOpaque = false
        self.clipsToBounds = false
        self.backColor = .clear
        self.trackColor = .clear
        self.startColor = .clear
        self.knobImage = NagramiXGlassSliderThumbView.transparentImage
        self.trackBackgroundView.isUserInteractionEnabled = false
        self.trackForegroundView.isUserInteractionEnabled = false
        self.trackBackgroundView.layer.cornerRadius = 1.0
        self.trackForegroundView.layer.cornerRadius = 1.0
        self.insertSubview(self.trackBackgroundView, at: 0)
        self.insertSubview(self.trackForegroundView, at: 1)
        self.knobView?.addSubview(self.glassThumbView)
        self.knobView?.clipsToBounds = false
    }

    func updateAppearance(isDark: Bool, background: UIColor, foreground: UIColor) {
        self.trackBackgroundView.backgroundColor = background
        self.trackForegroundView.backgroundColor = foreground
        self.glassThumbView.update(isDark: isDark)
    }

    override func layoutSubviews() {
        super.layoutSubviews()
        guard let knobView = self.knobView else { return }
        let inset = NagramiXGlassSliderGeometry.thumbInset
        let trackFrame = CGRect(x: -inset, y: floor((self.bounds.height - 2.0) * 0.5), width: self.bounds.width + inset * 2.0, height: 2.0)
        self.trackBackgroundView.frame = trackFrame
        let filledWidth: CGFloat
        if self.value <= self.minimumValue {
            filledWidth = 0.0
        } else if self.value >= self.maximumValue {
            filledWidth = trackFrame.width
        } else {
            filledWidth = max(0.0, min(trackFrame.width, knobView.frame.midX - trackFrame.minX))
        }
        self.trackForegroundView.frame = CGRect(x: trackFrame.minX, y: trackFrame.minY, width: filledWidth, height: trackFrame.height)
        self.glassThumbView.frame = knobView.bounds
    }

    override func point(inside point: CGPoint, with event: UIEvent?) -> Bool {
        return self.bounds.insetBy(dx: -NagramiXGlassSliderGeometry.thumbInset, dy: 0.0).contains(point)
    }

}
