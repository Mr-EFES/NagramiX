import Foundation
import XCTest
import Postbox
@testable import TelegramCore

final class NagramiXEditHistoryTests: XCTestCase {
    func testManyVersionsSurviveLocalSerializationWithoutTruncation() throws {
        var versions: [NagramiXMessageRevision] = []
        for i in 0 ..< 2000 {
            NagramiXMessageRevision.appendIfChanged(.init(text: "Версия \(i) 📝\n" + String(repeating: "Длинный текст ", count: 300), entities: [], timestamp: Int32(100 + i)), to: &versions)
        }
        let restored = try JSONDecoder().decode([NagramiXMessageRevision].self, from: JSONEncoder().encode(versions))
        XCTAssertEqual(restored, versions)
        XCTAssertEqual(restored.count, 2000)
        XCTAssertTrue(restored.first!.text.hasPrefix("Версия 0 "))
        XCTAssertTrue(restored.last!.text.hasPrefix("Версия 1999 "))
    }

    func testConsecutiveSyncDuplicatesDoNotEraseRepeatedVersions() {
        var versions: [NagramiXMessageRevision] = []
        for (text, time) in [("A", 100), ("A", 101), ("B", 101), ("A", 101)] {
            NagramiXMessageRevision.appendIfChanged(.init(text: text, entities: [], timestamp: Int32(time)), to: &versions)
        }
        XCTAssertEqual(versions.map { $0.text }, ["A", "B", "A"])
        XCTAssertEqual(versions.map { $0.timestamp }, [100, 101, 101])
    }

    func testFormattingOnlyEditAndEmptyCaptionSurviveRoundTrip() throws {
        let bold = MessageTextEntity(range: 0 ..< 4, type: .Bold)
        var versions: [NagramiXMessageRevision] = []
        for version in [NagramiXMessageRevision(text: "Тест 👋", entities: [], timestamp: 100),
                        NagramiXMessageRevision(text: "Тест 👋", entities: [bold], timestamp: 101),
                        NagramiXMessageRevision(text: "", entities: [], timestamp: 102)] {
            NagramiXMessageRevision.appendIfChanged(version, to: &versions)
        }
        XCTAssertEqual(versions.count, 3)
        XCTAssertEqual(try JSONDecoder().decode([NagramiXMessageRevision].self, from: JSONEncoder().encode(versions)), versions)
        XCTAssertEqual(versions[1].entities, [bold])
        XCTAssertEqual(versions.last?.text, "")
    }
}
