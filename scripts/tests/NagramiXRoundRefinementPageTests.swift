import Foundation

@main struct PageTests {
    static func main() {
        NagramiXRoundVideoSettings.update(.init(enabled: true))
        let page = PageHarness()
        let cells = page.table.cells
        var count = 0
        for quality in NagramiXRoundVideoSettings.Quality.allCases {
            for fps in NagramiXRoundVideoSettings.FrameRate.allCases {
                for supports in [false,true] {
                    for codec in NagramiXRoundVideoSettings.Codec.allCases {
                        page.cinematicModes = supports ? [quality.rawValue * 100 + 30:true] : [:]
                        let proposed = NagramiXRoundVideoSettings(enabled:true,quality:quality,frameRate:fps,codec:codec,cinematic:true)
                        page.commit(proposed)
                        let visible = fps == .standard && supports
                        precondition(page.showsCinematic == visible && page.numberOfSections(in:page.table) == (visible ? 4:3))
                        precondition(NagramiXRoundVideoSettings.current.cinematic == visible)
                        precondition(page.enabled(IndexPath(row:0,section:3),value:proposed) == visible)
                        precondition(page.table.offset == 71)
                        for (path,cell) in cells { precondition(page.table.cells[path] === cell) }
                        count += 1
                    }
                }
            }
        }
        // Явный выбор 60 не понижает FPS из-за прежнего CinematicON.
        page.cinematicModes = [640 * 100 + 30:true]
        page.commit(.init(enabled:true,quality:.maximum,cinematic:true))
        page.tableView(page.table,didSelectRowAt:IndexPath(row:1,section:1))
        precondition(NagramiXRoundVideoSettings.current.frameRate == .smooth && !NagramiXRoundVideoSettings.current.cinematic && !page.showsCinematic)
        // Устаревшее нажатие на уже скрытый раздел игнорируется.
        page.tableView(page.table,didSelectRowAt:IndexPath(row:0,section:3))
        precondition(!NagramiXRoundVideoSettings.current.cinematic)
        page.tableView(page.table,didSelectRowAt:IndexPath(row:0,section:1))
        precondition(page.showsCinematic)
        page.tableView(page.table,didSelectRowAt:IndexPath(row:0,section:3))
        precondition(NagramiXRoundVideoSettings.current.cinematic)
        page.tableView(page.table,didSelectRowAt:IndexPath(row:1,section:3))
        precondition(!NagramiXRoundVideoSettings.current.cinematic)
        let before = page.changes
        NagramiXRoundVideoSettings.update(.init(enabled:false))
        page.commit(.init(enabled:true,cinematic:true))
        precondition(!NagramiXRoundVideoSettings.current.enabled && page.changes == before)
        print("PASS: \(count) actual page transitions, conditional Cinematic30/device section, valid batch counts, retained cells/offset, Yes/No, 30↔60, stale hidden tap, master OFF")
    }
}
