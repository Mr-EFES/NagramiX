import NagramiXCore
import Foundation
import UIKit
import AsyncDisplayKit
import Display
import ItemListUI
import AccountContext
import TelegramPresentationData
import NagramiXMediaSettings

func nagramiXRoundQualityTitle(_ quality: NagramiXRoundVideoSettings.Quality, strings: PresentationStrings) -> String {
    switch quality { case .standard: return strings.nagramiXUILocalized("Стандарт"); case .high: return strings.nagramiXUILocalized("Высокое"); case .maximum: return strings.nagramiXUILocalized("Максимум") }
}

func nagramiXRoundQualitySubtitle(_ value: NagramiXRoundVideoSettings, strings: PresentationStrings) -> String {
    return String(format: strings.nagramiXLocalized("NagramiX.RoundVideo.QualitySubtitle"), locale: Locale(identifier: strings.primaryComponent.languageCode), arguments: [String(value.frameRate.rawValue), value.codec == .h264 ? "H.264 (AVC)" : "H.265 (HEVC)"])
}

private final class NagramiXRoundBitRateCell: UITableViewCell {
    private let nagramiXStrings: PresentationStrings
    private let titleLabel = UILabel()
    private let slider = NagramiXGlassSlider(frame: .zero)
    private let levelLabels: [UILabel]
    private let stopViews = (0..<4).map { _ in UIView() }
    private let normalColor: UIColor
    private let accentColor: UIColor
    private let selectedColor: UIColor
    var changed: ((Int) -> Void)?

    init(presentationData: PresentationData) {
        self.nagramiXStrings = presentationData.strings
        self.accentColor = presentationData.theme.list.itemAccentColor
        self.normalColor = presentationData.theme.list.itemSecondaryTextColor
        self.selectedColor = presentationData.theme.list.itemPrimaryTextColor
        let base = presentationData.listsFontSize.itemListBaseFontSize
        self.levelLabels = NagramiXRoundVideoSettings.BitRateLevel.allCases.map { level in
            let label = UILabel()
            label.text = presentationData.strings.nagramiXLocalized(level.localizationKey)
            label.font = Font.regular(base * 13.0 / 17.0)
            label.textAlignment = .center
            label.numberOfLines = 0
            label.adjustsFontForContentSizeCategory = true
            label.isAccessibilityElement = false
            label.setContentCompressionResistancePriority(.defaultLow, for: .horizontal)
            return label
        }
        super.init(style: .default, reuseIdentifier: nil)
        self.selectionStyle = .none
        self.isAccessibilityElement = false
        self.backgroundColor = presentationData.theme.list.itemBlocksBackgroundColor
        self.titleLabel.font = Font.regular(base)
        self.titleLabel.textColor = self.selectedColor
        self.titleLabel.numberOfLines = 0
        self.titleLabel.adjustsFontForContentSizeCategory = true
        self.titleLabel.isAccessibilityElement = false
        self.slider.minimumValue = 0
        self.slider.maximumValue = Float(self.levelLabels.count - 1)
        self.slider.accessibilityStep = 1
        self.slider.isContinuous = true
        self.slider.updateAppearance(isDark: presentationData.theme.overallDarkAppearance, background: self.normalColor.withAlphaComponent(0.25), foreground: presentationData.theme.list.itemAccentColor)
        self.slider.accessibilityLabel = self.nagramiXStrings.nagramiXUILocalized("Битрейт")
        self.slider.addTarget(self, action: #selector(self.valueChanged), for: .valueChanged)
        self.slider.addTarget(self, action: #selector(self.sliderTrackingEnded), for: [.touchUpInside, .touchUpOutside, .touchCancel])
        let tap = UITapGestureRecognizer(target: self, action: #selector(self.sliderTapped(_:)))
        tap.cancelsTouchesInView = false
        self.slider.addGestureRecognizer(tap)
        for stop in self.stopViews {
            stop.isUserInteractionEnabled = false
            stop.isAccessibilityElement = false
            stop.layer.cornerRadius = 3
            self.slider.addSubview(stop)
        }
        let labels = UIStackView(arrangedSubviews: self.levelLabels)
        labels.axis = .horizontal
        labels.alignment = .top
        labels.distribution = .fillEqually
        let leadingSpace = UIView()
        let trailingSpace = UIView()
        let sliderContainer = UIStackView(arrangedSubviews: [leadingSpace, self.slider, trailingSpace])
        sliderContainer.axis = .horizontal
        self.slider.translatesAutoresizingMaskIntoConstraints = false
        let content = UIStackView(arrangedSubviews: [self.titleLabel, sliderContainer, labels])
        content.axis = .vertical
        content.spacing = 8
        content.translatesAutoresizingMaskIntoConstraints = false
        self.contentView.addSubview(content)
        NSLayoutConstraint.activate([
            content.leadingAnchor.constraint(equalTo: self.contentView.leadingAnchor, constant: 16),
            content.trailingAnchor.constraint(equalTo: self.contentView.trailingAnchor, constant: -16),
            content.topAnchor.constraint(equalTo: self.contentView.topAnchor, constant: 16),
            content.bottomAnchor.constraint(equalTo: self.contentView.bottomAnchor, constant: -16),
            sliderContainer.heightAnchor.constraint(equalToConstant: 44),
            leadingSpace.widthAnchor.constraint(equalTo: labels.widthAnchor, multiplier: 0.125, constant: -NagramiXGlassSliderGeometry.thumbDiameter * 0.5),
            trailingSpace.widthAnchor.constraint(equalTo: labels.widthAnchor, multiplier: 0.125, constant: -NagramiXGlassSliderGeometry.thumbDiameter * 0.5)
        ])
    }
    required init?(coder: NSCoder) { fatalError("init(coder:) has not been implemented") }

    override func layoutSubviews() {
        super.layoutSubviews()
        let track = self.slider.trackRect(forBounds: self.slider.bounds)
        for (index, stop) in self.stopViews.enumerated() {
            let thumb = self.slider.thumbRect(forBounds: self.slider.bounds, trackRect: track, value: Float(index))
            stop.frame = CGRect(x: thumb.midX - 3, y: thumb.midY - 3, width: 6, height: 6)
        }
    }
    func update(_ value: NagramiXRoundVideoSettings) {
        let title = self.nagramiXStrings.nagramiXLocalized(value.bitRateLevel.localizationKey)
        self.titleLabel.text = title
        let step = (value.bitRate - NagramiXRoundVideoSettings.minimumBitRate) / NagramiXRoundVideoSettings.bitRateStep
        if !self.slider.isTracking { self.slider.value = Float(step) }
        self.slider.isEnabled = value.enabled
        self.slider.accessibilityValue = title
        for (index, label) in self.levelLabels.enumerated() {
            label.textColor = index == step ? self.selectedColor : self.normalColor
            self.stopViews[index].backgroundColor = index <= step ? self.accentColor : self.normalColor.withAlphaComponent(0.35)
            self.stopViews[index].isHidden = index == step
        }
        self.setNeedsLayout()
    }
    @objc private func valueChanged() {
        guard self.slider.isEnabled, self.slider.value.isFinite else { return }
        let step = Int(min(3, max(0, self.slider.value.rounded())))
        self.slider.value = Float(step)
        self.changed?(NagramiXRoundVideoSettings.minimumBitRate + step * NagramiXRoundVideoSettings.bitRateStep)
    }
    @objc private func sliderTrackingEnded() {
        guard self.slider.isEnabled, self.slider.value.isFinite else { return }
        let step = Int(min(3, max(0, self.slider.value.rounded())))
        self.slider.setValue(Float(step), animated: true)
        self.changed?(NagramiXRoundVideoSettings.minimumBitRate + step * NagramiXRoundVideoSettings.bitRateStep)
    }
    @objc private func sliderTapped(_ gesture: UITapGestureRecognizer) {
        guard gesture.state == .ended, self.slider.isEnabled, !self.slider.isTracking else { return }
        let track = self.slider.trackRect(forBounds: self.slider.bounds)
        let lower = self.slider.thumbRect(forBounds: self.slider.bounds, trackRect: track, value: self.slider.minimumValue).midX
        let upper = self.slider.thumbRect(forBounds: self.slider.bounds, trackRect: track, value: self.slider.maximumValue).midX
        guard abs(upper - lower) > 0 else { return }
        let fraction = min(1, max(0, (gesture.location(in: self.slider).x - lower) / (upper - lower)))
        self.slider.setValue(self.slider.minimumValue + Float(fraction) * (self.slider.maximumValue - self.slider.minimumValue), animated: false)
        self.valueChanged()
    }
}

private enum NagramiXRoundQualitySection: Int {
    case quality, frameRate, bitRate, codec, cinematic
}

private struct NagramiXRoundSegmentOption {
    let title: String
    let subtitle: String?
    let selected: Bool
    let enabled: Bool
}

// Keep quality names whole without reducing their font or moving other groups.
private func nagramiXRoundQualityUsesVerticalLayout(availableWidth: CGFloat, minimumOptionWidth: CGFloat, count: Int) -> Bool {
    guard availableWidth > 0, count > 0 else { return false }
    let rowWidth = max(0, availableWidth - 8)
    let requiredWidth = minimumOptionWidth * CGFloat(count) + CGFloat(max(0, count - 1))
    return rowWidth < requiredWidth
}

private final class NagramiXRoundSegmentButton: UIButton {
    private let surface: UIVisualEffectView
    private let nameLabel = UILabel()
    private let detailLabel = UILabel()
    private let checkView = UIImageView(image: UIImage(systemName: "checkmark"))
    var pressed: (() -> Void)?

    init(presentationData: PresentationData, singleLineLabels: Bool = false) {
        if #available(iOS 26.0, *) {
            let effect = UIGlassEffect(style: .clear)
            effect.isInteractive = false
            self.surface = UIVisualEffectView(effect: effect)
        } else {
            self.surface = UIVisualEffectView(effect: UIBlurEffect(style: presentationData.theme.overallDarkAppearance ? .systemUltraThinMaterialDark : .systemUltraThinMaterialLight))
        }
        super.init(frame: .zero)
        self.isAccessibilityElement = true
        self.surface.isUserInteractionEnabled = false
        self.surface.accessibilityElementsHidden = true
        self.surface.clipsToBounds = true
        self.surface.layer.cornerCurve = .continuous
        self.surface.layer.borderWidth = 0.7
        self.surface.layer.borderColor = presentationData.theme.list.itemAccentColor.withAlphaComponent(0.35).cgColor
        self.surface.contentView.backgroundColor = presentationData.theme.list.itemAccentColor.withAlphaComponent(0.14)
        self.addSubview(self.surface)
        self.surface.translatesAutoresizingMaskIntoConstraints = false
        let labels = UIStackView(arrangedSubviews: [self.nameLabel, self.detailLabel])
        labels.axis = .vertical
        labels.spacing = 3
        labels.isUserInteractionEnabled = false
        labels.accessibilityElementsHidden = true
        self.addSubview(labels)
        self.addSubview(self.checkView)
        labels.translatesAutoresizingMaskIntoConstraints = false
        self.checkView.translatesAutoresizingMaskIntoConstraints = false
        self.checkView.isUserInteractionEnabled = false
        self.checkView.isAccessibilityElement = false
        self.checkView.contentMode = .scaleAspectFit
        self.checkView.tintColor = presentationData.theme.list.itemAccentColor
        self.checkView.preferredSymbolConfiguration = UIImage.SymbolConfiguration(pointSize: 16, weight: .semibold)
        self.nameLabel.font = Font.regular(presentationData.listsFontSize.itemListBaseFontSize)
        self.nameLabel.textColor = presentationData.theme.list.itemPrimaryTextColor
        self.detailLabel.font = Font.regular(floor(presentationData.listsFontSize.itemListBaseFontSize * 13.0 / 17.0))
        self.detailLabel.textColor = presentationData.theme.list.itemSecondaryTextColor
        for label in [self.nameLabel, self.detailLabel] {
            label.numberOfLines = singleLineLabels ? 1 : 0
            label.textAlignment = .center
            label.adjustsFontForContentSizeCategory = true
            label.setContentCompressionResistancePriority(.required, for: .vertical)
            if singleLineLabels {
                label.setContentCompressionResistancePriority(.required, for: .horizontal)
            }
        }
        if singleLineLabels { labels.alignment = .center }
        var constraints = [
            self.surface.leadingAnchor.constraint(equalTo: self.leadingAnchor),
            self.surface.trailingAnchor.constraint(equalTo: self.trailingAnchor),
            self.surface.topAnchor.constraint(equalTo: self.topAnchor),
            self.surface.bottomAnchor.constraint(equalTo: self.bottomAnchor),
            labels.leadingAnchor.constraint(equalTo: self.leadingAnchor, constant: 8),
            labels.topAnchor.constraint(equalTo: self.topAnchor, constant: 12),
            labels.bottomAnchor.constraint(equalTo: self.bottomAnchor, constant: -12),
            self.checkView.widthAnchor.constraint(equalToConstant: 16),
            self.checkView.heightAnchor.constraint(equalToConstant: 20),
            self.heightAnchor.constraint(greaterThanOrEqualToConstant: 52)
        ]
        constraints += [
            labels.trailingAnchor.constraint(equalTo: self.checkView.leadingAnchor, constant: -4),
            self.checkView.trailingAnchor.constraint(equalTo: self.trailingAnchor, constant: -8),
            self.checkView.centerYAnchor.constraint(equalTo: self.centerYAnchor)
        ]
        NSLayoutConstraint.activate(constraints)
        self.addTarget(self, action: #selector(tapped), for: .touchUpInside)
    }
    required init?(coder: NSCoder) { fatalError("init(coder:) has not been implemented") }

    var minimumUnwrappedWidth: CGFloat {
        // Reserve the same 8 + 4 + 16 + 8pt text/checkmark insets in every state.
        return max(self.nameLabel.intrinsicContentSize.width,
                   self.detailLabel.intrinsicContentSize.width) + 36
    }

    override func layoutSubviews() {
        super.layoutSubviews()
        self.surface.layer.cornerRadius = min(20, self.bounds.height * 0.5)
    }
    override var isHighlighted: Bool {
        didSet { self.alpha = self.isEnabled ? (self.isHighlighted ? 0.65 : 1) : 0.4 }
    }
    func update(_ option: NagramiXRoundSegmentOption) {
        self.nameLabel.text = option.title
        self.detailLabel.text = option.subtitle
        self.detailLabel.isHidden = option.subtitle == nil
        self.isEnabled = option.enabled
        self.isSelected = option.selected
        self.alpha = option.enabled ? 1 : 0.4
        self.surface.isHidden = !option.selected
        self.checkView.alpha = option.selected ? 1 : 0
        self.accessibilityLabel = option.title
        self.accessibilityValue = option.subtitle
        self.accessibilityTraits = .button
        if option.selected { self.accessibilityTraits.insert(.selected) }
        if !option.enabled { self.accessibilityTraits.insert(.notEnabled) }
    }
    @objc private func tapped() {
        guard self.isEnabled else { return }
        self.pressed?()
    }
}

private final class NagramiXRoundSegmentCell: UITableViewCell {
    private let buttons: [NagramiXRoundSegmentButton]
    private let row: UIStackView
    private let qualityLayout: Bool
    private var separators: [UIView] = []
    var changed: ((Int) -> Void)?

    init(presentationData: PresentationData, count: Int, qualityLayout: Bool = false) {
        self.qualityLayout = qualityLayout
        self.buttons = (0 ..< count).map { _ in NagramiXRoundSegmentButton(presentationData: presentationData, singleLineLabels: qualityLayout) }
        self.row = UIStackView(arrangedSubviews: self.buttons)
        super.init(style: .default, reuseIdentifier: nil)
        self.selectionStyle = .none
        self.backgroundColor = presentationData.theme.list.itemBlocksBackgroundColor
        self.isAccessibilityElement = false
        let row = self.row
        row.axis = .horizontal
        row.distribution = .fillEqually
        row.spacing = 1
        self.contentView.addSubview(row)
        row.translatesAutoresizingMaskIntoConstraints = false
        NSLayoutConstraint.activate([
            row.leadingAnchor.constraint(equalTo: self.contentView.leadingAnchor, constant: 4),
            row.trailingAnchor.constraint(equalTo: self.contentView.trailingAnchor, constant: -4),
            row.topAnchor.constraint(equalTo: self.contentView.topAnchor, constant: 4),
            row.bottomAnchor.constraint(equalTo: self.contentView.bottomAnchor, constant: -4)
        ])
        for (index, button) in self.buttons.enumerated() {
            button.pressed = { [weak self] in self?.changed?(index) }
            if index > 0 {
                let separator = UIView()
                separator.backgroundColor = presentationData.theme.list.itemBlocksSeparatorColor
                separator.isUserInteractionEnabled = false
                separator.isAccessibilityElement = false
                self.separators.append(separator)
                self.contentView.insertSubview(separator, belowSubview: row)
                separator.translatesAutoresizingMaskIntoConstraints = false
                NSLayoutConstraint.activate([
                    separator.centerXAnchor.constraint(equalTo: button.leadingAnchor),
                    separator.widthAnchor.constraint(equalToConstant: 1 / max(1, self.traitCollection.displayScale)),
                    separator.topAnchor.constraint(equalTo: row.topAnchor, constant: 8),
                    separator.bottomAnchor.constraint(equalTo: row.bottomAnchor, constant: -8)
                ])
            }
        }
    }
    required init?(coder: NSCoder) { fatalError("init(coder:) has not been implemented") }

    private func updateRowAxis(for availableWidth: CGFloat) {
        guard self.qualityLayout, availableWidth > 0 else { return }
        let minimumWidth = self.buttons.map { $0.minimumUnwrappedWidth }.max() ?? 0
        let vertical = nagramiXRoundQualityUsesVerticalLayout(availableWidth: availableWidth, minimumOptionWidth: minimumWidth, count: self.buttons.count)
        let axis: NSLayoutConstraint.Axis = vertical ? .vertical : .horizontal
        if self.row.axis != axis {
            self.row.axis = axis
            self.contentView.invalidateIntrinsicContentSize()
            self.setNeedsLayout()
        }
        for separator in self.separators { separator.isHidden = vertical }
    }

    override func systemLayoutSizeFitting(_ targetSize: CGSize, withHorizontalFittingPriority horizontalFittingPriority: UILayoutPriority, verticalFittingPriority: UILayoutPriority) -> CGSize {
        self.updateRowAxis(for: targetSize.width)
        return super.systemLayoutSizeFitting(targetSize, withHorizontalFittingPriority: horizontalFittingPriority, verticalFittingPriority: verticalFittingPriority)
    }

    override func layoutSubviews() {
        super.layoutSubviews()
        self.updateRowAxis(for: self.contentView.bounds.width)
    }

    func update(_ options: [NagramiXRoundSegmentOption], availableWidth: CGFloat = 0) {
        precondition(options.count == self.buttons.count)
        for (button, option) in zip(self.buttons, options) { button.update(option) }
        self.updateRowAxis(for: availableWidth > 0 ? availableWidth : self.contentView.bounds.width)
    }
}

final class NagramiXRoundQualityController: ViewController, UITableViewDataSource, UITableViewDelegate {
    private let table = UITableView(frame: .zero, style: .insetGrouped)
    private let presentationData: PresentationData
    private let changed: () -> Void
    private var showsCinematic = false
    private var cinematicModes: [Int: Bool] = [:]

    init(context: AccountContext, changed: @escaping () -> Void) {
        self.presentationData = context.sharedContext.currentPresentationData.with { $0 }
        self.changed = changed
        super.init(navigationBarPresentationData: NavigationBarPresentationData(presentationData: self.presentationData))
        self.statusBar.statusBarStyle = self.presentationData.theme.rootController.statusBarStyle.style
        self.title = self.presentationData.strings.nagramiXUILocalized("Настройка кружков")
        self.table.contentInsetAdjustmentBehavior = .never
        self.table.rowHeight = UITableView.automaticDimension
        self.table.estimatedRowHeight = 64
        self.table.sectionHeaderHeight = UITableView.automaticDimension
        self.table.estimatedSectionHeaderHeight = 40
        self.table.backgroundColor = self.presentationData.theme.list.blocksBackgroundColor
        self.table.separatorColor = self.presentationData.theme.list.itemBlocksSeparatorColor
        self.table.overrideUserInterfaceStyle = self.presentationData.theme.overallDarkAppearance ? .dark : .light
        for quality in NagramiXRoundVideoSettings.Quality.allCases {
            let settings = NagramiXRoundVideoSettings(enabled: true, quality: quality, frameRate: .standard, cinematic: true)
            self.cinematicModes[quality.rawValue * 100 + 30] = NagramiXCinematicCapture.supports(settings)
        }
        var current = NagramiXRoundVideoSettings.current
        if current.cinematic && !self.supports(current) {
            current.cinematic = false
            NagramiXRoundVideoSettings.update(current)
            self.changed()
        }
        self.showsCinematic = self.shouldShowCinematic(current)
        self.table.dataSource = self
        self.table.delegate = self
    }
    required init(coder: NSCoder) { fatalError("init(coder:) has not been implemented") }

    override func loadDisplayNode() {
        self.displayNode = ASDisplayNode()
        self.displayNode.backgroundColor = self.presentationData.theme.list.blocksBackgroundColor
        self.displayNode.view.addSubview(self.table)
        self.displayNodeDidLoad()
    }
    override func containerLayoutUpdated(_ layout: ContainerViewLayout, transition: ContainedViewLayoutTransition) {
        super.containerLayoutUpdated(layout, transition: transition)
        let navigationBarHeight = self.navigationLayout(layout: layout).navigationFrame.maxY
        let previousWidth = self.table.bounds.width
        self.table.frame = CGRect(origin: .zero, size: layout.size)
        self.table.contentInset.top = navigationBarHeight
        self.table.contentInset.bottom = layout.intrinsicInsets.bottom
        self.table.scrollIndicatorInsets = self.table.contentInset
        if previousWidth != layout.size.width {
            UIView.performWithoutAnimation { self.table.reloadData() }
        }
    }
    private func supports(_ value: NagramiXRoundVideoSettings) -> Bool {
        return self.cinematicModes[value.quality.rawValue * 100 + value.frameRate.rawValue] == true
    }
    private func shouldShowCinematic(_ value: NagramiXRoundVideoSettings) -> Bool {
        return value.frameRate == .standard && self.supports(value)
    }
    private func options(_ section: NagramiXRoundQualitySection, value: NagramiXRoundVideoSettings) -> [NagramiXRoundSegmentOption] {
        let strings = self.presentationData.strings
        switch section {
        case .quality:
            return NagramiXRoundVideoSettings.Quality.allCases.map { quality in
                var candidate = value
                candidate.quality = quality
                return NagramiXRoundSegmentOption(title: nagramiXRoundQualityTitle(quality, strings: strings), subtitle: "\(quality.rawValue)×\(quality.rawValue)", selected: value.quality == quality, enabled: value.enabled && (!value.cinematic || self.supports(candidate)))
            }
        case .frameRate:
            return NagramiXRoundVideoSettings.FrameRate.allCases.map { fps in
                NagramiXRoundSegmentOption(title: strings.nagramiXUILocalized("\(fps.rawValue) кадров/с"), subtitle: nil, selected: value.frameRate == fps, enabled: value.enabled)
            }
        case .codec:
            return NagramiXRoundVideoSettings.Codec.allCases.map { codec in
                let title = codec == .h264 ? "H.264 (AVC)" : "H.265 (HEVC)"
                let subtitle = codec == .h264 ? strings.nagramiXUILocalized("Стандартное сжатие") : strings.nagramiXUILocalized("Эффективное сжатие")
                return NagramiXRoundSegmentOption(title: title, subtitle: subtitle, selected: value.codec == codec, enabled: value.enabled)
            }
        case .cinematic:
            return [true, false].map { cinematic in
                NagramiXRoundSegmentOption(title: cinematic ? strings.nagramiXUILocalized("Да") : strings.nagramiXUILocalized("Нет"), subtitle: nil, selected: value.cinematic == cinematic, enabled: value.enabled && self.shouldShowCinematic(value))
            }
        case .bitRate: return []
        }
    }
    func numberOfSections(in tableView: UITableView) -> Int { return self.showsCinematic ? 5 : 4 }
    func tableView(_ tableView: UITableView, numberOfRowsInSection section: Int) -> Int {
        return 1
    }
    func tableView(_ tableView: UITableView, titleForHeaderInSection section: Int) -> String? {
        return [self.presentationData.strings.nagramiXUILocalized("КАЧЕСТВО"), self.presentationData.strings.nagramiXUILocalized("ЧАСТОТА КАДРОВ"), self.presentationData.strings.nagramiXUILocalized("БИТРЕЙТ"), self.presentationData.strings.nagramiXUILocalized("КОДЕК"), self.presentationData.strings.nagramiXUILocalized("КИНОЭФФЕКТ")][section].uppercased()
    }
    func tableView(_ tableView: UITableView, viewForHeaderInSection section: Int) -> UIView? {
        let header = tableView.dequeueReusableHeaderFooterView(withIdentifier: "RoundHeader")
            ?? UITableViewHeaderFooterView(reuseIdentifier: "RoundHeader")
        var content = UIListContentConfiguration.groupedHeader()
        content.text = self.tableView(tableView, titleForHeaderInSection: section)
        content.textProperties.font = Font.regular(self.presentationData.listsFontSize.itemListBaseHeaderFontSize)
        content.textProperties.color = self.presentationData.theme.list.sectionHeaderTextColor
        content.textProperties.numberOfLines = 0
        header.contentConfiguration = content
        return header
    }
    func tableView(_ tableView: UITableView, cellForRowAt indexPath: IndexPath) -> UITableViewCell {
        let section = NagramiXRoundQualitySection(rawValue: indexPath.section)!
        if section == .bitRate {
            let cell = NagramiXRoundBitRateCell(presentationData: self.presentationData)
            cell.changed = { [weak self] bitRate in self?.updateBitRate(bitRate) }
            self.configure(cell, at: indexPath)
            return cell
        }
        let count = self.options(section, value: NagramiXRoundVideoSettings.current).count
        let cell = NagramiXRoundSegmentCell(presentationData: self.presentationData, count: count, qualityLayout: section == .quality)
        cell.changed = { [weak self] index in self?.select(section, index: index) }
        self.configure(cell, at: indexPath)
        return cell
    }
    private func configure(_ cell: UITableViewCell, at indexPath: IndexPath) {
        let value = NagramiXRoundVideoSettings.current
        if let cell = cell as? NagramiXRoundBitRateCell { cell.update(value); return }
        guard let section = NagramiXRoundQualitySection(rawValue: indexPath.section), let cell = cell as? NagramiXRoundSegmentCell else { return }
        let availableWidth = max(0, self.table.bounds.width - self.table.layoutMargins.left - self.table.layoutMargins.right)
        cell.update(self.options(section, value: value), availableWidth: availableWidth)
    }
    private func refreshVisibleRows() {
        for path in self.table.indexPathsForVisibleRows ?? [] {
            guard path.section < (self.showsCinematic ? 5 : 4) else { continue }
            if let cell = self.table.cellForRow(at: path) { self.configure(cell, at: path) }
        }
    }
    private func commit(_ proposed: NagramiXRoundVideoSettings) {
        guard NagramiXRoundVideoSettings.current.enabled else { self.refreshVisibleRows(); return }
        var value = proposed
        if !self.shouldShowCinematic(value) { value.cinematic = false }
        let show = self.shouldShowCinematic(value)
        NagramiXRoundVideoSettings.update(value)
        UIView.performWithoutAnimation {
            if self.showsCinematic != show {
                self.table.performBatchUpdates({
                    self.showsCinematic = show
                    if show { self.table.insertSections(IndexSet(integer: 4), with: .none) }
                    else { self.table.deleteSections(IndexSet(integer: 4), with: .none) }
                })
            }
            self.refreshVisibleRows()
        }
        self.changed()
    }
    private func updateBitRate(_ bitRate: Int) {
        var value = NagramiXRoundVideoSettings.current
        let previous = value.bitRate
        value.bitRate = bitRate
        guard value.enabled else { self.refreshVisibleRows(); return }
        guard value.bitRate != previous else { return }
        self.commit(value)
    }
    func tableView(_ tableView: UITableView, didSelectRowAt indexPath: IndexPath) {
        tableView.deselectRow(at: indexPath, animated: false)
    }
    private func select(_ section: NagramiXRoundQualitySection, index: Int) {
        var value = NagramiXRoundVideoSettings.current
        let options = self.options(section, value: value)
        guard value.enabled, options.indices.contains(index), options[index].enabled else { self.refreshVisibleRows(); return }
        switch section {
        case .quality: value.quality = NagramiXRoundVideoSettings.Quality.allCases[index]
        case .frameRate:
            value.frameRate = NagramiXRoundVideoSettings.FrameRate.allCases[index]
            if value.frameRate != .standard { value.cinematic = false }
        case .codec: value.codec = NagramiXRoundVideoSettings.Codec.allCases[index]
        case .cinematic: value.cinematic = index == 0
        case .bitRate: return
        }
        self.commit(value)
    }
}
