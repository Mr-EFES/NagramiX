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
        // Считаем только поддерживаемый интерфейсом Cinematic30, один раз.
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
        var candidate = value
        switch path.section {
        case 0:
            candidate.quality = NagramiXRoundVideoSettings.Quality.allCases[path.row]
            return !value.cinematic || self.supports(candidate)
        case 1:
            return true
        case 3:
            return self.shouldShowCinematic(value)
        default: return true
        }
    }
    func numberOfSections(in tableView: UITableView) -> Int { return self.showsCinematic ? 4 : 3 }
    func tableView(_ tableView: UITableView, numberOfRowsInSection section: Int) -> Int { return section == 0 ? 3 : 2 }
    func tableView(_ tableView: UITableView, titleForHeaderInSection section: Int) -> String? {
        return ["КАЧЕСТВО", "ЧАСТОТА КАДРОВ", "КОДЕК", "КИНОЭФФЕКТ"][section]
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
        let cell = UITableViewCell(style: .subtitle, reuseIdentifier: nil)
        self.configure(cell, at: indexPath)
        return cell
    }
    private func configure(_ cell: UITableViewCell, at indexPath: IndexPath) {
        let value = NagramiXRoundVideoSettings.current
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
            let rate = String(format: "%.1f", Double(quality.bitRate) / 1_000_000).replacingOccurrences(of: ".", with: ",")
            cell.textLabel?.text = "\(quality.rawValue)×\(quality.rawValue) · \(nagramiXRoundQualityTitle(quality))"
            cell.detailTextLabel?.text = "\(value.frameRate.rawValue) FPS · \(rate) Мбит/с · \(value.codec == .h264 ? "H.264 (AVC)" : "H.265 (HEVC)")"
            selected = value.quality == quality
        case 1:
            let fps = NagramiXRoundVideoSettings.FrameRate.allCases[indexPath.row]
            cell.textLabel?.text = "\(fps.rawValue) кадров/с"
            selected = value.frameRate == fps
        case 2:
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
    private func commit(_ proposed: NagramiXRoundVideoSettings) {
        guard NagramiXRoundVideoSettings.current.enabled else { return }
        var value = proposed
        if !self.shouldShowCinematic(value) { value.cinematic = false }
        let show = self.shouldShowCinematic(value)
        NagramiXRoundVideoSettings.update(value)
        UIView.performWithoutAnimation {
            if self.showsCinematic != show {
                self.table.performBatchUpdates({
                    self.showsCinematic = show
                    if show { self.table.insertSections(IndexSet(integer: 3), with: .none) }
                    else { self.table.deleteSections(IndexSet(integer: 3), with: .none) }
                })
            }
            for path in self.table.indexPathsForVisibleRows ?? [] {
                guard path.section < (self.showsCinematic ? 4 : 3) else { continue }
                if let cell = self.table.cellForRow(at: path) { self.configure(cell, at: path) }
            }
        }
        self.changed()
    }
    func tableView(_ tableView: UITableView, didSelectRowAt indexPath: IndexPath) {
        tableView.deselectRow(at: indexPath, animated: false)
        var value = NagramiXRoundVideoSettings.current
        guard value.enabled, self.enabled(indexPath, value: value) else { return }
        switch indexPath.section {
        case 0: value.quality = NagramiXRoundVideoSettings.Quality.allCases[indexPath.row]
        case 1:
            value.frameRate = NagramiXRoundVideoSettings.FrameRate.allCases[indexPath.row]
            if value.frameRate != .standard { value.cinematic = false }
        case 2: value.codec = NagramiXRoundVideoSettings.Codec.allCases[indexPath.row]
        default:
            value.cinematic = indexPath.row == 0
        }
        self.commit(value)
    }
}
