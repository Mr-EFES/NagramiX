import Foundation
import UIKit
import AsyncDisplayKit
import Display
import ItemListUI
import AccountContext
import TelegramPresentationData
import NagramiXMediaSettings

func nagramiXRoundQualityTitle(_ quality: NagramiXRoundVideoSettings.Quality) -> String {
    switch quality { case .standard: return "Стандарт"; case .high: return "Высокое"; case .maximum: return "Максимум" }
}

private func nagramiXRoundBitRateText(_ value: Int) -> String {
    return "\(value / 1_000_000),\((value % 1_000_000) / 100_000)"
}

private final class NagramiXRoundBitRateCell: UITableViewCell {
    private let titleLabel = UILabel()
    private let rateLabel = UILabel()
    private let slider = UISlider()
    var changed: ((Int) -> Void)?

    init(presentationData: PresentationData) {
        super.init(style: .default, reuseIdentifier: nil)
        self.selectionStyle = .none
        self.isAccessibilityElement = false
        self.backgroundColor = presentationData.theme.list.itemBlocksBackgroundColor
        let base = presentationData.listsFontSize.itemListBaseFontSize
        self.titleLabel.font = Font.regular(base)
        self.titleLabel.textColor = presentationData.theme.list.itemPrimaryTextColor
        self.titleLabel.numberOfLines = 0
        self.titleLabel.adjustsFontForContentSizeCategory = true
        self.titleLabel.setContentCompressionResistancePriority(.defaultLow, for: .horizontal)
        self.rateLabel.font = Font.regular(floor(base * 15.0 / 17.0))
        self.rateLabel.textColor = presentationData.theme.list.itemSecondaryTextColor
        self.rateLabel.adjustsFontForContentSizeCategory = true
        self.rateLabel.setContentCompressionResistancePriority(.required, for: .horizontal)
        self.titleLabel.isAccessibilityElement = false
        self.rateLabel.isAccessibilityElement = false
        self.slider.minimumValue = 0
        self.slider.maximumValue = 10
        self.slider.isContinuous = true
        self.slider.minimumTrackTintColor = presentationData.theme.list.itemAccentColor
        self.slider.maximumTrackTintColor = presentationData.theme.list.itemSecondaryTextColor.withAlphaComponent(0.25)
        self.slider.accessibilityLabel = "Битрейт"
        self.slider.addTarget(self, action: #selector(self.valueChanged), for: .valueChanged)
        let labels = UIStackView(arrangedSubviews: [self.titleLabel, self.rateLabel])
        labels.axis = .horizontal
        labels.alignment = .center
        labels.spacing = 12
        let content = UIStackView(arrangedSubviews: [labels, self.slider])
        content.axis = .vertical
        content.spacing = 12
        content.translatesAutoresizingMaskIntoConstraints = false
        self.contentView.addSubview(content)
        NSLayoutConstraint.activate([
            content.leadingAnchor.constraint(equalTo: self.contentView.leadingAnchor, constant: 20),
            content.trailingAnchor.constraint(equalTo: self.contentView.trailingAnchor, constant: -20),
            content.topAnchor.constraint(equalTo: self.contentView.topAnchor, constant: 16),
            content.bottomAnchor.constraint(equalTo: self.contentView.bottomAnchor, constant: -16)
        ])
    }
    required init?(coder: NSCoder) { fatalError("init(coder:) has not been implemented") }

    func update(_ value: NagramiXRoundVideoSettings) {
        let rate = nagramiXRoundBitRateText(value.bitRate)
        self.titleLabel.text = "Битрейт: \(rate) Мбит/с"
        self.rateLabel.text = "\(value.bitRate / 1000)"
        self.slider.value = Float((value.bitRate - NagramiXRoundVideoSettings.minimumBitRate) / NagramiXRoundVideoSettings.bitRateStep)
        self.slider.isEnabled = value.enabled
        self.slider.accessibilityValue = "\(rate) Мбит/с"
    }
    @objc private func valueChanged() {
        guard self.slider.value.isFinite else { return }
        let step = Int(min(10, max(0, self.slider.value.rounded())))
        self.slider.value = Float(step)
        self.changed?(NagramiXRoundVideoSettings.minimumBitRate + step * NagramiXRoundVideoSettings.bitRateStep)
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
        self.title = "Настройка кружков"
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
        return ["КАЧЕСТВО", "БИТРЕЙТ", "ЧАСТОТА КАДРОВ", "КОДЕК", "КИНОЭФФЕКТ"][section]
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
            cell.textLabel?.text = "\(quality.rawValue)×\(quality.rawValue) · \(nagramiXRoundQualityTitle(quality))"
            cell.detailTextLabel?.text = "\(value.frameRate.rawValue) FPS · \(nagramiXRoundBitRateText(value.bitRate)) Мбит/с · \(value.codec == .h264 ? "H.264 (AVC)" : "H.265 (HEVC)")"
            selected = value.quality == quality
        case 2:
            let fps = NagramiXRoundVideoSettings.FrameRate.allCases[indexPath.row]
            cell.textLabel?.text = "\(fps.rawValue) кадров/с"
            selected = value.frameRate == fps
        case 3:
            let codec = NagramiXRoundVideoSettings.Codec.allCases[indexPath.row]
            cell.textLabel?.text = codec == .h264 ? "H.264 (AVC)" : "H.265 (HEVC)"
            cell.detailTextLabel?.text = codec == .h264 ? "Стандартное сжатие" : "Эффективное сжатие"
            selected = value.codec == codec
        default:
            cell.textLabel?.text = indexPath.row == 0 ? "Да" : "Нет"
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
        guard value.enabled, value.bitRate != previous else { self.refreshVisibleRows(); return }
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
