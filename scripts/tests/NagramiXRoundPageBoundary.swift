import Foundation

extension IndexPath {
    init(row: Int, section: Int) { self.init(indexes: [section, row]) }
    var section: Int { self[0] }
    var row: Int { self[1] }
}
struct UIView { static func performWithoutAnimation(_ f: () -> Void) { f() } }
final class PageCell { var value: NagramiXRoundVideoSettings? }
final class PageTable {
    let paths = (0..<4).flatMap { section in (0..<(section == 0 ? 3 : 2)).map { IndexPath(row: $0, section: section) } }
    var cells: [IndexPath: PageCell] = [:]
    var indexPathsForVisibleRows: [IndexPath]? { paths }
    var contentOffset = CGPoint(x: 0, y: 173)
    init() { for path in paths { cells[path] = PageCell() } }
    func cellForRow(at path: IndexPath) -> PageCell? { cells[path] }
}
struct PixelDimensions: Equatable { let width: Int; let height: Int }
struct TelegramMediaVideoFlags: OptionSet {
    let rawValue: Int
    static let instantRoundVideo = Self(rawValue: 1)
    static let supportsStreaming = Self(rawValue: 2)
    static let isSilent = Self(rawValue: 4)
}
enum TelegramMediaFileAttribute {
    case FileName(fileName: String)
    case Video(duration: Double, size: PixelDimensions, flags: TelegramMediaVideoFlags, preloadSize: Int?, coverTime: Double?, videoCodec: String?)
}
final class SourceNode { var nagramiXQuality: NagramiXRoundVideoSettings? }
