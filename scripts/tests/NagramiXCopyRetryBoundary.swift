import Foundation

// Only Postbox transaction storage is a boundary. The retry implementation is
// extracted unchanged, including its guards and StoreMessage construction.
struct Flags:OptionSet {let rawValue:Int;static let Failed=Self(rawValue:1);static let Incoming=Self(rawValue:2);static let Unsent=Self(rawValue:4)}
protocol MessageAttribute {}
struct OutgoingContentInfoMessageAttribute:MessageAttribute {struct Bits:OptionSet {let rawValue:Int;static let nagramiXCopy=Self(rawValue:1)};var flags:Bits}
struct RandomId:MessageAttribute {var value:Int64}
struct Owner {var id:Int}
struct Message {
    var id:Int;var flags:Flags;var attributes:[MessageAttribute]
    var globallyUniqueId:Int64?=42;var groupingKey:Int64?=100;var threadId:Int64?=7;var timestamp:Int32=10
    var tags=1,globalTags=2,localTags=3;var author:Owner?=Owner(id:5);var text="Caption";var media=[10,20]
}
enum EngineMessage {typealias Id=Int}
struct StoreMessage {
    let id:Int;let customStableId:Int?;let globallyUniqueId:Int64?;let groupingKey:Int64?;let threadId:Int64?;let timestamp:Int32
    let flags:Flags;let tags:Int;let globalTags:Int;let localTags:Int;let forwardInfo:Int?;let authorId:Int?;let text:String;let attributes:[MessageAttribute];let media:[Int]
}
enum Update {case skip,update(StoreMessage)}
final class Transaction {
    var messages:[Int:Message]=[:];var updates:[StoreMessage]=[]
    func updateMessage(_ id:Int,update:(Message)->Update) {
        guard let old=messages[id] else{return}
        if case let .update(value)=update(old){updates.append(value);var m=old;m.flags=value.flags;messages[id]=m}
    }
}
enum NoError {}
struct Signal<T,E> {let run:()->T;func start()->T {run()}}
final class Postbox {
    let storage=Transaction()
    func transaction<T>(_ f:@escaping(Transaction)->T)->Signal<T,NoError> {Signal {f(self.storage)}}
}
final class Account {let postbox=Postbox()}
// PRODUCTION_RETRY
@main struct RetryTests {
    static func main() {
        var checks=0
        func check(_ value:@autoclosure()->Bool,_ label:String){if !value(){fatalError("Copy retry regression: "+label)};checks+=1}
        let account=Account(),db=account.postbox.storage
        let copy=Message(id:1,flags:[.Failed],attributes:[OutgoingContentInfoMessageAttribute(flags:[.nagramiXCopy]),RandomId(value:9999)])
        db.messages[1]=copy
        db.messages[2]=Message(id:2,flags:[.Failed],attributes:[])
        db.messages[3]=Message(id:3,flags:[.Unsent],attributes:copy.attributes)
        db.messages[4]=Message(id:4,flags:[],attributes:copy.attributes)
        db.messages[5]=Message(id:5,flags:[.Failed,.Incoming],attributes:copy.attributes)
        nagramiXRetryCopiedMessages(account:account,messageIds:[1,1,2,3,4,5,6]).start()
        check(db.updates.count==1,"only rejected own copies retried once")
        let retry=db.updates[0]
        check(retry.id==copy.id && retry.globallyUniqueId==copy.globallyUniqueId,"pending identity preserved")
        check((retry.attributes.last as? RandomId)?.value==9999,"native RPC random_id preserved")
        check(retry.groupingKey==copy.groupingKey && retry.threadId==copy.threadId,"album and destination topic preserved")
        check(retry.media==copy.media && retry.text==copy.text,"retry retains complete payload")
        check(retry.flags==[.Unsent],"native outbox resumes existing message")
        nagramiXRetryCopiedMessages(account:account,messageIds:[1]).start()
        check(db.updates.count==1,"retry while pending cannot duplicate enqueue")
        print("Copy retry identity checks: \(checks)")
    }
}
