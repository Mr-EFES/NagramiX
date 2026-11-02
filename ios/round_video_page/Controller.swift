import Foundation
import UIKit
import AsyncDisplayKit
import Display
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
    private var cinematicModes: [Int: Bool] = [:]

    init(context: AccountContext, changed: @escaping () -> Void) {
        self.presentationData = context.sharedContext.currentPresentationData.with { $0 }
        self.changed = changed
        super.init(navigationBarPresentationData: NavigationBarPresentationData(presentationData: self.presentationData))
        self.title = "Настройка кружков"
        self.table.dataSource = self
        self.table.delegate = self
        self.table.contentInsetAdjustmentBehavior = .never
        self.table.rowHeight = UITableView.automaticDimension
        self.table.estimatedRowHeight = 64
        self.table.backgroundColor = self.presentationData.theme.list.blocksBackgroundColor
        self.table.separatorColor = self.presentationData.theme.list.itemBlocksSeparatorColor
        self.table.overrideUserInterfaceStyle = self.presentationData.theme.overallDarkAppearance ? .dark : .light
        // Доступность камер не пересчитывается при каждом обновлении галочки.
        for quality in NagramiXRoundVideoSettings.Quality.allCases {
            for fps in NagramiXRoundVideoSettings.FrameRate.allCases {
                let settings = NagramiXRoundVideoSettings(enabled: true, quality: quality, frameRate: fps, cinematic: true)
                self.cinematicModes[quality.rawValue * 100 + fps.rawValue] = NagramiXCinematicCapture.supports(settings)
            }
        }
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
    private func enabled(_ path: IndexPath, value: NagramiXRoundVideoSettings) -> Bool {
        var candidate = value
        switch path.section {
        case 0:
            candidate.quality = NagramiXRoundVideoSettings.Quality.allCases[path.row]
            return !value.cinematic || self.supports(candidate)
        case 1:
            candidate.frameRate = NagramiXRoundVideoSettings.FrameRate.allCases[path.row]
            return !value.cinematic || self.supports(candidate)
        case 3 where path.row == 0:
            if self.supports(candidate) { return true }
            candidate.frameRate = .standard
            return self.supports(candidate)
        default: return true
        }
    }
    func numberOfSections(in tableView: UITableView) -> Int { return 4 }
    func tableView(_ tableView: UITableView, numberOfRowsInSection section: Int) -> Int { return section == 0 ? 3 : 2 }
    func tableView(_ tableView: UITableView, titleForHeaderInSection section: Int) -> String? {
        return ["КАЧЕСТВО", "ЧАСТОТА КАДРОВ", "КОДЕК", "КИНОЭФФЕКТ"][section]
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
        cell.textLabel?.font = UIFont.preferredFont(forTextStyle: .body)
        cell.detailTextLabel?.font = UIFont.preferredFont(forTextStyle: .footnote)
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
            cell.textLabel?.text = indexPath.row == 0 ? "Включено" : "Выключено"
            selected = value.cinematic == (indexPath.row == 0)
        }
        cell.accessoryType = selected ? .checkmark : .none
        if selected { cell.accessibilityTraits.insert(.selected) }
    }
    private func commit(_ value: NagramiXRoundVideoSettings) {
        guard NagramiXRoundVideoSettings.current.enabled else { return }
        NagramiXRoundVideoSettings.update(value)
        // Меняем содержимое существующих ячеек, сохраняя страницу и scroll offset.
        UIView.performWithoutAnimation {
            for path in self.table.indexPathsForVisibleRows ?? [] {
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
        case 1: value.frameRate = NagramiXRoundVideoSettings.FrameRate.allCases[indexPath.row]
        case 2: value.codec = NagramiXRoundVideoSettings.Codec.allCases[indexPath.row]
        default:
            value.cinematic = indexPath.row == 0
            if value.cinematic && !self.supports(value) {
                value.frameRate = .standard
                guard self.supports(value) else { return }
                let proposal = value
                let original = NagramiXRoundVideoSettings.current
                let alert = UIAlertController(title: "Киноэффект", message: "Для выбранной камеры киноэффект доступен при 30 FPS. Переключить частоту кадров на 30 FPS и включить киноэффект?", preferredStyle: .alert)
                alert.overrideUserInterfaceStyle = self.table.overrideUserInterfaceStyle
                alert.addAction(UIAlertAction(title: "Отмена", style: .cancel))
                alert.addAction(UIAlertAction(title: "Включить при 30 FPS", style: .default, handler: { [weak self] _ in
                    guard NagramiXRoundVideoSettings.current == original else { return }
                    self?.commit(proposal)
                }))
                self.present(alert, animated: true)
                return
            }
        }
        self.commit(value)
    }
}
