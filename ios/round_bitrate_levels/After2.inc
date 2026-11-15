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
        self.table.frame = CGRect(origin: .zero, size: layout.size)
        self.table.contentInset.top = navigationBarHeight
        self.table.contentInset.bottom = layout.intrinsicInsets.bottom
        self.table.scrollIndicatorInsets = self.table.contentInset
    }
    private func supports(_ value: NagramiXRoundVideoSettings) -> Bool {
        return self.cinematicModes[value.quality.rawValue * 100 + value.frameRate.rawValue] == true
    }
    private func shouldShowCinematic(_ value: NagramiXRoundVideoSettings) -> Bool {
        return value.frameRate == .standard && self.supports(value)
    }
    private func enabled(_ path: IndexPath, value: NagramiXRoundVideoSettings) -> Bool {
        guard path.section >= 0, path.section < (self.showsCinematic ? 5 : 4), path.row >= 0,
              path.row < (path.section == 0 ? 3 : (path.section == 1 ? 1 : 2)) else { return false }
        var candidate = value
        switch path.section {
        case 0:
            candidate.quality = NagramiXRoundVideoSettings.Quality.allCases[path.row]
            return !value.cinematic || self.supports(candidate)
        case 4: return self.shouldShowCinematic(value)
        default: return true
        }
    }
    func numberOfSections(in tableView: UITableView) -> Int { return self.showsCinematic ? 5 : 4 }
    func tableView(_ tableView: UITableView, numberOfRowsInSection section: Int) -> Int {
        return section == 0 ? 3 : (section == 1 ? 1 : 2)
    }
    func tableView(_ tableView: UITableView, titleForHeaderInSection section: Int) -> String? {
        return [self.presentationData.strings.nagramiXUILocalized("КАЧЕСТВО"), self.presentationData.strings.nagramiXUILocalized("БИТРЕЙТ"), self.presentationData.strings.nagramiXUILocalized("ЧАСТОТА КАДРОВ"), self.presentationData.strings.nagramiXUILocalized("КОДЕК"), self.presentationData.strings.nagramiXUILocalized("КИНОЭФФЕКТ")][section]
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
        if indexPath.section == 1 {
            let cell = NagramiXRoundBitRateCell(presentationData: self.presentationData)
            cell.changed = { [weak self] bitRate in self?.updateBitRate(bitRate) }
            self.configure(cell, at: indexPath)
            return cell
        }
        let cell = UITableViewCell(style: .subtitle, reuseIdentifier: nil)
        self.configure(cell, at: indexPath)
        return cell
    }
    private func configure(_ cell: UITableViewCell, at indexPath: IndexPath) {
        let value = NagramiXRoundVideoSettings.current
        if let cell = cell as? NagramiXRoundBitRateCell { cell.update(value); return }
        let available = self.enabled(indexPath, value: value)
        cell.backgroundColor = self.presentationData.theme.list.itemBlocksBackgroundColor
        cell.textLabel?.textColor = available ? self.presentationData.theme.list.itemPrimaryTextColor : self.presentationData.theme.list.itemSecondaryTextColor
        cell.detailTextLabel?.textColor = self.presentationData.theme.list.itemSecondaryTextColor
        cell.tintColor = self.presentationData.theme.list.itemAccentColor
        cell.textLabel?.numberOfLines = 0
        cell.detailTextLabel?.numberOfLines = 0
        cell.textLabel?.font = Font.regular(self.presentationData.listsFontSize.itemListBaseFontSize)
        cell.detailTextLabel?.font = Font.regular(floor(self.presentationData.listsFontSize.itemListBaseFontSize * 15.0 / 17.0))
        cell.textLabel?.adjustsFontForContentSizeCategory = true
        cell.detailTextLabel?.adjustsFontForContentSizeCategory = true
        cell.detailTextLabel?.text = nil
        cell.selectionStyle = available ? .default : .none
        cell.accessibilityTraits = available ? .button : [.button, .notEnabled]
        let selected: Bool
        switch indexPath.section {
        case 0:
            let quality = NagramiXRoundVideoSettings.Quality.allCases[indexPath.row]
            cell.textLabel?.text = "\(quality.rawValue)×\(quality.rawValue) · \(nagramiXRoundQualityTitle(quality, strings: self.presentationData.strings))"
            cell.detailTextLabel?.text = nagramiXRoundQualitySubtitle(value, strings: self.presentationData.strings)
            selected = value.quality == quality
        case 2:
            let fps = NagramiXRoundVideoSettings.FrameRate.allCases[indexPath.row]
            cell.textLabel?.text = self.presentationData.strings.nagramiXUILocalized("\(fps.rawValue) кадров/с")
            selected = value.frameRate == fps
        case 3:
            let codec = NagramiXRoundVideoSettings.Codec.allCases[indexPath.row]
            cell.textLabel?.text = codec == .h264 ? "H.264 (AVC)" : "H.265 (HEVC)"
            cell.detailTextLabel?.text = codec == .h264 ? self.presentationData.strings.nagramiXUILocalized("Стандартное сжатие") : self.presentationData.strings.nagramiXUILocalized("Эффективное сжатие")
            selected = value.codec == codec
        default:
            cell.textLabel?.text = indexPath.row == 0 ? self.presentationData.strings.nagramiXUILocalized("Да") : self.presentationData.strings.nagramiXUILocalized("Нет")
            selected = value.cinematic == (indexPath.row == 0)
        }
        cell.accessoryType = selected ? .checkmark : .none
        if selected { cell.accessibilityTraits.insert(.selected) }
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
        var value = NagramiXRoundVideoSettings.current
        guard value.enabled, self.enabled(indexPath, value: value) else { return }
        switch indexPath.section {
        case 0: value.quality = NagramiXRoundVideoSettings.Quality.allCases[indexPath.row]
        case 1: return
        case 2:
            value.frameRate = NagramiXRoundVideoSettings.FrameRate.allCases[indexPath.row]
            if value.frameRate != .standard { value.cinematic = false }
        case 3: value.codec = NagramiXRoundVideoSettings.Codec.allCases[indexPath.row]
        default: value.cinematic = indexPath.row == 0
        }
        self.commit(value)
    }
}
