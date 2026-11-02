import Foundation

extension IndexPath {
    init(row: Int, section: Int) { self.init(indexes: [section,row]) }
    var section: Int { self[0] }; var row: Int { self[1] }
}
struct UIView { static func performWithoutAnimation(_ f: () -> Void) { f() } }
final class Cell { var value: NagramiXRoundVideoSettings? }
final class UITableView {
    enum Animation { case none }
    var sections: () -> Int = { 3 }
    var actions: [Int] = []
    var cells: [IndexPath:Cell] = [:]
    var offset = 71
    var indexPathsForVisibleRows: [IndexPath]? { cells.keys.filter { $0.section < sections() } }
    func cellForRow(at path: IndexPath) -> Cell? { cells[path] }
    func deselectRow(at path: IndexPath, animated: Bool) {}
    func insertSections(_ sections: IndexSet, with: Animation) {
        precondition(sections == IndexSet(integer: 3)); actions.append(1)
        for row in 0..<2 { cells[IndexPath(row: row, section: 3)] = Cell() }
    }
    func deleteSections(_ sections: IndexSet, with: Animation) {
        precondition(sections == IndexSet(integer: 3)); actions.append(-1)
        for row in 0..<2 { cells[IndexPath(row: row, section: 3)] = nil }
    }
    func performBatchUpdates(_ updates: () -> Void) {
        let before = sections(), events = actions.count
        updates()
        precondition(actions.count == events+1 && sections() == before+actions.last!)
    }
}
final class PageHarness {
    var showsCinematic = false
    var cinematicModes: [Int:Bool] = [:]
    let table = UITableView()
    var changes = 0
    lazy var changed: () -> Void = { [unowned self] in changes += 1 }
    init() {
        table.sections = { [unowned self] in numberOfSections(in: table) }
        for section in 0..<3 {
            for row in 0..<(section == 0 ? 3 : 2) { table.cells[IndexPath(row:row,section:section)] = Cell() }
        }
    }
    func configure(_ cell: Cell, at path: IndexPath) { cell.value = NagramiXRoundVideoSettings.current }
    // PAGE_METHODS
}
