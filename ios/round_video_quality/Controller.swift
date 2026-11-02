import Foundation
import UIKit
import AsyncDisplayKit
import Display
import AccountContext
import TelegramPresentationData
import NagramiXMediaSettings

func nagramiXRoundQualityTitle(_ quality: NagramiXRoundVideoSettings.Quality) -> String {
    switch quality { case .standard: return "Стандарт"; case .high: return "Высокая"; case .maximum: return "Максимум" }
}

final class NagramiXRoundQualityController: ViewController, UITableViewDataSource, UITableViewDelegate {
    private let table = UITableView(frame: .zero, style: .insetGrouped)
    private let presentationData: PresentationData
    private let changed: () -> Void
    init(context: AccountContext, changed: @escaping () -> Void) {
        self.presentationData = context.sharedContext.currentPresentationData.with { $0 }
        self.changed = changed
        super.init(navigationBarPresentationData: NavigationBarPresentationData(presentationData: self.presentationData))
        self.title = "Настройка кружков"
        self.table.dataSource = self
        self.table.delegate = self
        self.table.rowHeight = UITableView.automaticDimension
        self.table.estimatedRowHeight = 64
        self.table.backgroundColor = self.presentationData.theme.list.blocksBackgroundColor
        self.table.separatorColor = self.presentationData.theme.list.itemBlocksSeparatorColor
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
    }
    func numberOfSections(in tableView: UITableView) -> Int { return 3 }
    func tableView(_ tableView: UITableView, numberOfRowsInSection section: Int) -> Int { return section == 0 ? 3 : 2 }
    func tableView(_ tableView: UITableView, titleForHeaderInSection section: Int) -> String? { return ["КАЧЕСТВО", "ЧАСТОТА КАДРОВ", "КОДЕК"][section] }
    func tableView(_ tableView: UITableView, cellForRowAt indexPath: IndexPath) -> UITableViewCell {
        let value = NagramiXRoundVideoSettings.current
        let cell = UITableViewCell(style: .subtitle, reuseIdentifier: nil)
        cell.backgroundColor = self.presentationData.theme.list.itemBlocksBackgroundColor
        cell.textLabel?.textColor = self.presentationData.theme.list.itemPrimaryTextColor
        cell.detailTextLabel?.textColor = self.presentationData.theme.list.itemSecondaryTextColor
        cell.tintColor = self.presentationData.theme.list.itemAccentColor
        cell.textLabel?.numberOfLines = 0
        cell.detailTextLabel?.numberOfLines = 0
        cell.textLabel?.font = UIFont.preferredFont(forTextStyle: .body)
        cell.detailTextLabel?.font = UIFont.preferredFont(forTextStyle: .footnote)
        cell.textLabel?.adjustsFontForContentSizeCategory = true
        cell.detailTextLabel?.adjustsFontForContentSizeCategory = true
        let selected: Bool
        switch indexPath.section {
        case 0:
            let quality = NagramiXRoundVideoSettings.Quality.allCases[indexPath.row]
            cell.textLabel?.text = "\(quality.rawValue)×\(quality.rawValue) · \(nagramiXRoundQualityTitle(quality))"
            let rate = String(format: "%.1f", Double(quality.bitRate) / 1_000_000).replacingOccurrences(of: ".", with: ",")
            cell.detailTextLabel?.text = "\(value.frameRate.rawValue) FPS · \(rate) Мбит/с · \(value.codec == .h264 ? "H.264" : "HEVC")"
            selected = value.quality == quality
        case 1:
            let fps = NagramiXRoundVideoSettings.FrameRate.allCases[indexPath.row]
            cell.textLabel?.text = "\(fps.rawValue) кадров/с"
            selected = value.frameRate == fps
        default:
            let codec = NagramiXRoundVideoSettings.Codec.allCases[indexPath.row]
            cell.textLabel?.text = codec == .h264 ? "H.264" : "HEVC"
            cell.detailTextLabel?.text = codec == .h264 ? "Стандарт" : "Эффективное сжатие"
            selected = value.codec == codec
        }
        cell.accessoryType = selected ? .checkmark : .none
        if selected { cell.accessibilityTraits.insert(.selected) }
        return cell
    }
    func tableView(_ tableView: UITableView, didSelectRowAt indexPath: IndexPath) {
        var value = NagramiXRoundVideoSettings.current
        switch indexPath.section {
        case 0: value.quality = NagramiXRoundVideoSettings.Quality.allCases[indexPath.row]
        case 1: value.frameRate = NagramiXRoundVideoSettings.FrameRate.allCases[indexPath.row]
        default: value.codec = NagramiXRoundVideoSettings.Codec.allCases[indexPath.row]
        }
        NagramiXRoundVideoSettings.update(value)
        self.changed()
        self.table.reloadData()
    }
}
