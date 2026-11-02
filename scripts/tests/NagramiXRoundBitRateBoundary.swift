import Foundation

// UI controls, AVFoundation writer and delivery are boundaries. Native model,
// slider/page bodies, capture settings, snapshot and export bodies are inserted.
extension IndexPath {
    init(row: Int, section: Int) { self.init(indexes: [section, row]) }
    var section: Int { self[0] }
    var row: Int { self[1] }
}
enum Color: Equatable { case background, primary, secondary, accent }
enum Font { static func regular(_ size: CGFloat) -> CGFloat { size } }
struct ListTheme {
    var itemBlocksBackgroundColor = Color.background
    var itemPrimaryTextColor = Color.primary
    var itemSecondaryTextColor = Color.secondary
    var itemAccentColor = Color.accent
}
struct Theme { var list = ListTheme() }
struct PresentationData { var theme = Theme(); var listsFontSize: PresentationFontSize = .regular }
final class Label { var text: String?; var textColor: Color?; var numberOfLines = 1; var font: CGFloat = 0; var adjustsFontForContentSizeCategory = false }
final class Slider { var value: Float = 0; var isEnabled = true; var accessibilityValue: String? }
struct Traits: OptionSet {
    let rawValue: Int
    static let button = Traits(rawValue: 1), notEnabled = Traits(rawValue: 2), selected = Traits(rawValue: 4)
}
class UITableViewCell {
    enum Selection { case `default`, none }
    enum Accessory { case checkmark, none }
    var backgroundColor: Color?
    var textLabel: Label? = Label(), detailTextLabel: Label? = Label()
    var tintColor: Color?
    var selectionStyle: Selection = .default
    var accessoryType: Accessory = .none
    var accessibilityTraits: Traits = []
}
final class NagramiXRoundBitRateCell: UITableViewCell {
    let titleLabel = Label(), rateLabel = Label(), slider = Slider()
    var changed: ((Int) -> Void)?
    // CELL_METHODS
}
struct UIView { static func performWithoutAnimation(_ action: () -> Void) { action() } }
final class UITableView {
    enum Animation { case none }
    var sections: () -> Int = { 4 }
    var actions: [Int] = []
    var cells: [IndexPath: UITableViewCell] = [:]
    var offset = 71
    var indexPathsForVisibleRows: [IndexPath]? { cells.keys.filter { $0.section < sections() } }
    func cellForRow(at path: IndexPath) -> UITableViewCell? { cells[path] }
    func deselectRow(at path: IndexPath, animated: Bool) {}
    func insertSections(_ set: IndexSet, with: Animation) {
        precondition(set == IndexSet(integer: 4)); actions.append(1)
        for row in 0..<2 { cells[IndexPath(row: row, section: 4)] = UITableViewCell() }
    }
    func deleteSections(_ set: IndexSet, with: Animation) {
        precondition(set == IndexSet(integer: 4)); actions.append(-1)
        for row in 0..<2 { cells[IndexPath(row: row, section: 4)] = nil }
    }
    func performBatchUpdates(_ updates: () -> Void) {
        let before = sections(), events = actions.count
        updates()
        precondition(actions.count == events + 1 && sections() == before + actions.last!)
    }
}
final class PageHarness {
    let table = UITableView()
    let presentationData = PresentationData()
    var showsCinematic = false
    var cinematicModes: [Int: Bool] = [48030: true, 51230: true, 64030: true]
    var changes = 0
    lazy var changed: () -> Void = { [unowned self] in self.changes += 1 }
    init() {
        self.showsCinematic = self.shouldShowCinematic(NagramiXRoundVideoSettings.current)
        table.sections = { [unowned self] in self.numberOfSections(in: self.table) }
        for section in 0..<self.numberOfSections(in: table) {
            for row in 0..<(section == 0 ? 3 : (section == 1 ? 1 : 2)) {
                table.cells[IndexPath(row: row, section: section)] = section == 1 ? NagramiXRoundBitRateCell() : UITableViewCell()
            }
        }
        (table.cells[IndexPath(row: 0, section: 1)] as! NagramiXRoundBitRateCell).changed = { [weak self] rate in self?.updateBitRate(rate) }
        refreshVisibleRows()
    }
    // PAGE_METHODS
}

enum AVVideoCodecType: Equatable { case h264, hevc }
let AVVideoAverageBitRateKey = "average", AVVideoProfileLevelKey = "profile", AVVideoProfileLevelH264HighAutoLevel = "avc-high"
let AVVideoH264EntropyModeKey = "entropy", AVVideoH264EntropyModeCABAC = "cabac", kVTProfileLevel_HEVC_Main_AutoLevel = "hevc-main"
let AVVideoCodecKey = "codec", AVVideoWidthKey = "width", AVVideoHeightKey = "height", AVVideoCompressionPropertiesKey = "compression"
let AVVideoColorPropertiesKey = "color", AVVideoExpectedSourceFrameRateKey = "expected-fps"
let AVFormatIDKey = "audio-format", kAudioFormatMPEG4AAC = "aac", AVSampleRateKey = "sample-rate", AVEncoderBitRateKey = "audio-rate", AVNumberOfChannelsKey = "channels"
struct RoundVideoFrameProcessor {
    let quality: NagramiXRoundVideoSettings?
    var outputWidth: Int { quality?.quality.rawValue ?? 480 }
    var outputHeight: Int { outputWidth }
    static func videoColorProperties(from: Int) -> [String: Any] { [:] }
}
struct VideoFrame { let source = 0 }
final class AVAssetWriterInput {
    let outputSettings: [String: Any]
    var expectsMediaDataInRealTime = false
    init(mediaType: MediaType, outputSettings: [String: Any]) { self.outputSettings = outputSettings }
}
enum MediaType { case video }
final class Writer {
    var applies = true, adds = true
    var probed: [String: Any] = [:]
    var input: AVAssetWriterInput?
    func canApply(outputSettings: [String: Any], forMediaType: MediaType) -> Bool { probed = outputSettings; return applies }
    func canAdd(_ input: AVAssetWriterInput) -> Bool { adds }
    func add(_ input: AVAssetWriterInput) { self.input = input }
}
final class CaptureHarness {
    let processor: RoundVideoFrameProcessor
    let writer = Writer()
    var failed = false
    init(_ value: NagramiXRoundVideoSettings?) { processor = .init(quality: value) }
    func fail() { failed = true }
    func configure() {
        let assetWriter = writer, firstVideoFrame = VideoFrame()
        // CAPTURE_SETTINGS
    }
}
struct SnapshotSource {
    struct Node { let nagramiXQuality: NagramiXRoundVideoSettings? }
    let node: Node
    func tuning() -> [Int]? {
        return SNAPSHOT_EXPRESSION
    }
}
enum Preset { case videoMessage, story }
struct MediaEditorValues { var qualityPreset: Preset?; var nagramiXRoundTuning: [Int]? }
enum MediaEditorVideoExport {
    struct Configuration {
        var videoSettings: [String: Any]
        var audioSettings: [String: Any]
        var values: MediaEditorValues
        var frameRate: Float
        var preferredDuration: Double?
        var dimensions: CGSize { .init(width: videoSettings[AVVideoWidthKey] as! Int, height: videoSettings[AVVideoHeightKey] as! Int) }
    }
}
func export(_ values: MediaEditorValues) -> MediaEditorVideoExport.Configuration? {
    // EXPORT_BRANCH
    return nil
}
struct Transform { let b: CGFloat; let c: CGFloat }
func exportWriterSettings(configuration: MediaEditorVideoExport.Configuration, preferredTransform: Transform?, sourceFrameRate: Float) -> [String: Any] {
    // EXPORT_WRITER_SETTINGS
    return videoSettings
}
struct TuningEnvelope: Codable {
    let nagramiXRoundTuning: [Int]?
    enum CodingKeys: String, CodingKey { case nagramiXRoundTuning }
    init(_ tuning: [Int]?) { self.nagramiXRoundTuning = tuning }
    init(from decoder: Decoder) throws {
        let container = try decoder.container(keyedBy: CodingKeys.self)
        // DECODE_TUNING
    }
    func encode(to encoder: Encoder) throws {
        var container = encoder.container(keyedBy: CodingKeys.self)
        // ENCODE_TUNING
    }
}
