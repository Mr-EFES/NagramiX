import Foundation

// Linux CoreFoundation traps when adjoining distinct custom NSObject attribute
// values. Attributed runs are a boundary here; native NSString UTF-16 lengths,
// production helpers/state and pinned Atomic/Disposable execute unchanged.
public class NSAttributedString {
    struct Key: Hashable { let rawValue: String; init(_ value: String) { rawValue=value } }
    var storage: String
    var cells: [[Key: Any]]
    var string: String { storage }
    var length: Int { (storage as NSString).length }
    init(string: String, attributes: [Key: Any] = [:]) {
        storage=string; cells=Array(repeating:attributes,count:(string as NSString).length)
    }
    init(attributedString: NSAttributedString) { storage=attributedString.storage; cells=attributedString.cells }
    func attribute(_ key: Key, at: Int, effectiveRange: UnsafeMutablePointer<NSRange>?) -> Any? { cells[at][key] }
    func enumerateAttribute(_ key: Key, in range: NSRange, using action: (Any?,NSRange,UnsafeMutablePointer<ObjCBool>)->Void) {
        func equal(_ a: Any?,_ b: Any?) -> Bool {
            if a == nil && b == nil { return true }
            if let a=a as? NSObject,let b=b as? NSObject { return a.isEqual(b) }
            return false
        }
        var index=range.location, stop=ObjCBool(false)
        while index<range.location+range.length {
            let value=cells[index][key]; var end=index+1
            while end<range.location+range.length && equal(value,cells[end][key]) { end += 1 }
            withUnsafeMutablePointer(to:&stop) { action(value,NSRange(location:index,length:end-index),$0) }
            if stop.boolValue { return }; index=end
        }
    }
}
final class NSMutableAttributedString: NSAttributedString {
    func append(_ text: NSAttributedString) { storage += text.storage; cells += text.cells }
    func addAttribute(_ key: Key, value: Any, range: NSRange) {
        precondition(range.location>=0 && range.location+range.length<=length)
        for index in range.location..<(range.location+range.length) { cells[index][key]=value }
    }
}

struct PeerId: Equatable { let value: Int }
struct MessageId: Equatable { let peerId: PeerId; let namespace: Int32; let id: Int32 }
struct MediaId: Equatable { let namespace: Int32; let id: Int64 }
enum Namespaces { enum Media { static let CloudFile: Int32 = 0 } }
public final class TelegramMediaFile { let fileId: MediaId; init(_ id: Int64, namespace: Int32 = 0) { fileId = MediaId(namespace: namespace, id: id) } }
enum EntityType: Equatable { case emoji(Int64), bold, spoiler, italic }
struct MessageTextEntity: Equatable { let range: Range<Int>; let type: EntityType }
final class ChatTextInputTextCustomEmojiAttribute: NSObject {
    let interactivelySelectedFromPackId: Int64?
    let fileId: Int64
    let file: TelegramMediaFile?
    let custom: Int?
    let enableAnimation: Bool
    init(interactivelySelectedFromPackId: Int64?, fileId: Int64, file: TelegramMediaFile?, custom: Int? = nil, enableAnimation: Bool = true) {
        self.interactivelySelectedFromPackId=interactivelySelectedFromPackId; self.fileId=fileId; self.file=file
        self.custom=custom; self.enableAnimation=enableAnimation
    }
    // Match the native attribute's identity equality; adjacent same-ID emoji
    // are distinct attachments, never one merged attribute run.
    override func isEqual(_ object: Any?) -> Bool {
        guard let other=object as? ChatTextInputTextCustomEmojiAttribute else { return false }
        return self === other
    }
}
let instantPagePreviewCustomEmoji = NSAttributedString.Key("TelegramInstantPagePreviewCustomEmoji")
enum ChatTextInputAttributes { static let customEmoji = NSAttributedString.Key("customEmoji") }
final class Queue { static func mainQueue() -> Queue { Queue() }; func async(_ action: @escaping ()->Void) { fatalError("test supplies deterministic scheduler") } }

final class Scheduler {
    var work: [()->Void] = []
    func schedule(_ action: @escaping ()->Void) { work.append(action) }
    func drain() { while !work.isEmpty { work.removeFirst()() } }
}
final class Resolver {
    var ids: [[Int64]] = []
    var completions: [([Int64: TelegramMediaFile])->Void] = []
    var cancelled = 0
    var immediate: [Int64: TelegramMediaFile]?
    func request(_ ids: [Int64], completion: @escaping ([Int64: TelegramMediaFile])->Void) -> Disposable {
        self.ids.append(ids); completions.append(completion)
        if let immediate { completion(immediate) }
        return ActionDisposable { [weak self] in self?.cancelled += 1 }
    }
}
