"""Полный ASR/Engine transport и настоящий сгенерированный RPC; сеть и media I/O — явные адаптеры."""
from pathlib import Path
import hashlib,json
from private_temporary_transcription_runtime import fixture as prior
from validate_quick_format import block
ROOT=Path(__file__).resolve().parents[1]
def fixture(source):
 c=prior(source).replace('@main struct PrivateTemporaryTranscriptionTests','struct PrivateTemporaryTranscriptionTests')
 c=c.replace('final class Account{let network=Network();','final class Account{struct RecordId {var int64:Int64=1};var id=RecordId();let network=Network();')
 c=c.replace('struct TranscribedAudioData {let flags:Int32=0;let transcriptionId:Int64=99;let text="Native ordinary transcript";let trialRemainsNum:Int32?=nil;let trialRemainsUntilDate:Int32?=nil}', 'struct TranscribedAudioData {var flags:Int32=0;var transcriptionId:Int64=99;var text:String="Native ordinary transcript";var trialRemainsNum:Int32?=nil;var trialRemainsUntilDate:Int32?=nil}')
 # The actual generated RPC builder executes with an explicit TL storage adapter.
 plan=json.loads((ROOT/'ios/premium_temporary_transcription_patches.json').read_text())
 name='premium_temporary_transcription/NativeRPC.inc'
 rpc=(ROOT/'ios'/name).read_text()
 assert hashlib.sha256(rpc.encode()).hexdigest()==plan['templates'][name]
 c+='\nextension Api.functions.messages {\n'+rpc+'\n}\n'
 c+=r'''
struct FunctionDescription {let object:TLObject}
struct Buffer {}
struct DeserializeFunctionResponse<T> {}
final class TLObject {let constructor:Int;var file:Api.InputFile?;var refs:[Int:TLObject]=[:];init(_ c:Int){constructor=c}}
func TLApiFunctionConstructorAt(_ index:Int)->Int {index}
func TLObjectAllocate(_ index:Int)->TLObject {TLObject(index)}
func tlStoreReference(_ object:TLObject,_ offset:Int,_ ref:TLObject) {object.refs[offset]=ref}
func tlFunction<T>(_ object:TLObject)->(FunctionDescription,Buffer,DeserializeFunctionResponse<T>) {(.init(object:object),.init(),.init())}
extension Api {
 enum InputFile {
  struct Cons_inputFile {let id:Int64;let parts:Int32;let name:String;let md5Checksum:String}
  struct Cons_inputFileBig {let id:Int64;let parts:Int32;let name:String}
  struct Cons_inputFileStoryDocument {}
  case inputFile(Cons_inputFile),inputFileBig(Cons_inputFileBig),inputFileStoryDocument(Cons_inputFileStoryDocument)
  var tlObject:TLObject {let o=TLObject(0);o.file=self;return o}
  var name:String {switch self {case let .inputFile(v):return v.name;case let .inputFileBig(v):return v.name;case .inputFileStoryDocument:return "story"}}
 }
}
enum MultipartUploadError:Error {case generic}
enum MultipartUploadResult {case progress(Float),inputFile(Api.InputFile),inputSecretFile}
enum MultipartUploadSource {case data(Data)}
enum UploadBoundary {
 static var uploads=0,bytes=0;static var afterUpload:(()->Void)?;static var fail=false;static var big=false;static var story=false
 static func reset(){uploads=0;bytes=0;afterUpload=nil;fail=false;big=false;story=false}
}
func multipartUpload(network:Network,postbox:Postbox,source:MultipartUploadSource,encrypt:Bool,tag:Int?,hintFileSize:Int64?,hintFileIsLarge:Bool,forceNoBigParts:Bool)->Signal<MultipartUploadResult,MultipartUploadError> {
 precondition(!encrypt && forceNoBigParts)
 if case let .data(data)=source {UploadBoundary.bytes=data.count}
 UploadBoundary.uploads+=1;UploadBoundary.afterUpload?()
 if UploadBoundary.fail{return .fail(.generic)}
 if UploadBoundary.story{return .single(.inputFile(.inputFileStoryDocument(.init())))}
 return Signal { subscriber in
  subscriber.putNext(.progress(0.5))
  subscriber.putNext(.inputFile(UploadBoundary.big ? .inputFileBig(.init(id:42,parts:1,name:"file.jpg")):.inputFile(.init(id:42,parts:1,name:"file.jpg",md5Checksum:"owned"))))
  subscriber.putCompletion();return EmptyDisposable
 }
}
final class FileNetworkState {
 var calls=0,cancellations=0;var flags:Int32=0;var text="Premium file transcript";var error:String?;var name="";var fields:[Int]=[];var constructor=0;var hold=false
 var callback:((Result<Api.messages.TranscribedAudio,RpcError>)->Void)?
 let started=DispatchSemaphore(value:0)
 func finish(){let f=callback;callback=nil;if let error {f?(.failure(RpcError(errorDescription:error)))}else{f?(.success(.transcribedAudio(.init(flags:flags,text:text))))}}
}
var fileNetworks:[ObjectIdentifier:FileNetworkState]=[:]
let fileNetworkLock=NSLock()
extension Network {
 var file:FileNetworkState {fileNetworkLock.lock();defer{fileNetworkLock.unlock()};let k=ObjectIdentifier(self);if let value=fileNetworks[k]{return value};let value=FileNetworkState();fileNetworks[k]=value;return value}
 func request(_ request:(FunctionDescription,Buffer,DeserializeFunctionResponse<Api.messages.TranscribedAudio>),automaticFloodWait:Bool)->Signal<Api.messages.TranscribedAudio,RpcError> {
  precondition(!automaticFloodWait)
  return Signal { s in
   let v=self.file;v.calls+=1;v.fields=request.0.object.refs.keys.sorted();v.constructor=request.0.object.constructor;v.name=request.0.object.refs[24]?.file?.name ?? ""
   v.callback={result in switch result {case let .success(x):s.putNext(x);s.putCompletion();case let .failure(x):s.putError(x)}}
   v.started.signal();if !v.hold {v.finish()}
   return ActionDisposable{v.cancellations+=1;v.callback=nil}
  }
 }
}
extension NagramiXTranscriptionCoordinator {func flushFileTests(){self.queue.sync {}}}
var asrChecks=0
func expectFile(_ value:Bool,_ label:String) {if !value{print("FAIL "+label);exit(91)};asrChecks+=1}
@main struct PremiumFileTranscriptionChecks {
 static var serial=10000
 static func configure(_ p:NagramiXTranscriptionProvider = .telegram,_ fallback:Bool=false,_ enabled:Bool=true) {
  NagramiXTranscriptionSettings.update{$0 = .init();$0.provider=p;$0.usesAccountDefaultProvider=false;$0.localFallback=fallback;$0.enabled=enabled;$0.language="en-US"}
 }
 static func context()->AccountContext {let c=AccountContext();c.engine.data.premium=true;return c}
 static func message(_ c:AccountContext,_ round:Bool=false,_ incoming:Bool=true,_ ttl:Int32?=viewOnceTimeout)->Message {
  let m=PrivateTemporaryTranscriptionTests.message(round:round,ttl:ttl,incoming:incoming);c.account.postbox.store.messages[m.id]=m;return m
 }
 // This command-line fixture has no UIKit event loop. Keep Foundation's main
 // notification queue running while waiting for the unchanged async operation.
 static func wait(_ s:DispatchSemaphore,_ label:String){
  let deadline=Date(timeIntervalSinceNow:5)
  while s.wait(timeout:.now()) != .success {
   guard Date()<deadline else {expectFile(false,label);return}
   _ = RunLoop.current.run(mode:.default,before:Date(timeIntervalSinceNow:0.005))
  }
  expectFile(true,label)
 }
 static func run(_ c:AccountContext,_ m:Message,_ menu:Bool=false,_ mutate:(()->Void)?=nil)->Result<String,NagramiXTranscriptionFailure> {
  let done=DispatchSemaphore(value:0);var result:Result<String,NagramiXTranscriptionFailure>?;var d:Disposable?
  if menu {NagramiXTranscriptionRuntime.toggleContext(context:c,messageId:m.id){result=$0;done.signal()}}
  else {d=NagramiXTranscriptionRuntime.transcribe(context:c,messageId:m.id).start(next:{result=$0;done.signal()})}
  mutate?();wait(done,"operation completes");d?.dispose();return result!
 }
 static func original(_ c:AccountContext,_ m:Message) {
  expectFile(c.account.network.transcriptions==0 && c.account.network.rates==0,"no original-message RPC")
  expectFile(!m.wasDeleted && m.minAutoremoveOrClearTimeout != nil,"original stays live")
  expectFile(m.attributes.compactMap{$0 as? ConsumableContentMessageAttribute}.allSatisfy{!$0.consumed},"original stays unopened")
  expectFile(m.attributes.compactMap{$0 as? AutoremoveTimeoutMessageAttribute}.allSatisfy{$0.countdownBeginTime==nil},"no countdown")
 }
 static func main() {
  let key="nagramix.transcription.configuration.v1";let old=UserDefaults.standard.object(forKey:key)
  defer{if let old{UserDefaults.standard.set(old,forKey:key)}else{UserDefaults.standard.removeObject(forKey:key)}}
  let path=URL(fileURLWithPath:"/tmp/nagramix-asr-boundary-audio.m4a");try! Data([1,2,3,4]).write(to:path);defer{try? FileManager.default.removeItem(at:path)}
  PrivateTemporaryTranscriptionTests.retained(true);NagramiXTranscriptionApple.authorized=false;AudioBoundary.provider=nil
  for round in [false,true] {for incoming in [false,true] {for menu in [false,true] {for fallback in [false,true] {
   configure(.telegram,fallback);UploadBoundary.reset();let c=context(),m=message(c,round,incoming)
   expectFile(NagramiXTranscriptionRuntime.handles(m,context:c),"temporary Premium uses file pipeline")
   expectFile(!NagramiXTranscriptionRuntime.canUseTelegram(m),"original remains blocked")
   let result=run(c,m,menu)
   expectFile(result == .success("Premium file transcript"),"Premium transcript returned")
   expectFile(c.account.network.file.calls==1 && UploadBoundary.uploads==1,"one file upload and ASR")
   expectFile(c.account.network.file.name=="voice.m4a" && c.account.network.file.fields==[24],"RPC contains only named file")
   expectFile(c.account.network.file.constructor==609,"actual generated method builder")
   expectFile(NagramiXTranscriptionRuntime.cached(m,context:c)=="Premium file transcript","Telegram file transcript cache")
   expectFile(AudioBoundary.provider==nil,"no Apple request or permission")
   original(c,m)
  }}}}
  for (rpc,error) in [("INPUT_METHOD_INVALID",NagramiXTranscriptionFailure.unavailableMedia),("PREMIUM_ACCOUNT_REQUIRED",.premiumRequired),("FLOOD_WAIT_30",.quota),("MSG_VOICE_TOO_LONG",.tooLarge),("OFFLINE",.network)] {
   configure();UploadBoundary.reset();let c=context(),m=message(c);c.account.network.file.error=rpc
   expectFile(run(c,m) == .failure(error),"server error propagated");expectFile(AudioBoundary.provider==nil,"server refusal never selects Apple");original(c,m)
  }
  for (flags,text,error) in [(Int32(1),"partial",NagramiXTranscriptionFailure.invalidResponse),(0," ",.noSpeech),(0,String(repeating:"x",count:100001),.invalidResponse)] {
   configure();let c=context(),m=message(c);c.account.network.file.flags=flags;c.account.network.file.text=text
   expectFile(run(c,m) == .failure(error),"incomplete response is not stored");expectFile(!NagramiXTranscriptionRuntime.hasTemporaryTranscript(m,context:c),"no false completed transcript");original(c,m)
  }
  configure();UploadBoundary.reset();let free=context(),fm=message(free);free.engine.data.premium=false
  expectFile(run(free,fm) == .failure(.premiumRequired),"Premium checked before upload");expectFile(UploadBoundary.uploads==0,"non-Premium does not upload");original(free,fm)
  configure(.telegram,false,false);let off=context(),om=message(off)
  expectFile(!NagramiXTranscriptionRuntime.handles(om,context:off),"saved OFF respected")
  expectFile(run(off,om) == .failure(.disabled),"no implicit Apple with master OFF")
  configure();UploadBoundary.reset();let changed=context(),cm=message(changed)
  UploadBoundary.afterUpload={NagramiXTranscriptionSettings.update{$0.enabled=false}}
  expectFile(run(changed,cm) == .failure(.cancelled),"setting change during upload cancels")
  expectFile(changed.account.network.file.calls==0,"no file RPC after setting changed");original(changed,cm);UploadBoundary.afterUpload=nil
  configure();let ordinary=context(),voice=message(ordinary,false,true,nil)
  expectFile(!NagramiXTranscriptionRuntime.handles(voice,context:ordinary),"ordinary Premium keeps native route")
  expectFile(run(ordinary,voice,true) == .success(""),"ordinary native request")
  expectFile(ordinary.account.network.transcriptions==1 && ordinary.account.network.file.calls==0,"ordinary uses original permitted native path")
  configure();UploadBoundary.reset();let secret=context(),sm=PrivateTemporaryTranscriptionTests.message(secret:true)
  secret.account.postbox.store.messages[sm.id]=sm
  expectFile(!NagramiXTranscriptionRuntime.handles(sm,context:secret),"secret chat is not silently exported")
  expectFile(run(secret,sm) == .failure(.disabled) && UploadBoundary.uploads==0,"no secret-chat upload")
  configure();UploadBoundary.reset();let cancelled=context(),cancelMessage=message(cancelled);cancelled.account.network.file.hold=true
  let cancelDisposable=NagramiXTranscriptionRuntime.transcribe(context:cancelled,messageId:cancelMessage.id).start()
  wait(cancelled.account.network.file.started,"cancel test reaches file RPC")
  cancelDisposable.dispose();NagramiXTranscriptionCoordinator.shared.flushFileTests()
  expectFile(cancelled.account.network.file.cancellations>0,"cancel disposes upload and network")
  cancelled.account.network.file.finish()
  expectFile(!NagramiXTranscriptionRuntime.hasTemporaryTranscript(cancelMessage,context:cancelled),"late cancelled result is not stored");original(cancelled,cancelMessage)
  configure();UploadBoundary.reset();let deleted=context(),dm=message(deleted)
  let archive=NagramiXMessageArchive();NagramiXMessageArchive.registered=archive
  archive.put(dm);archive.records[dm.id.descriptionKey]?.deletedAt=nil
  deleted.account.network.file.hold=true
  let deletionDone=DispatchSemaphore(value:0);var deletionResult:Result<String,NagramiXTranscriptionFailure>?
  let deletionDisposable=NagramiXTranscriptionRuntime.transcribe(context:deleted,messageId:dm.id).start(next:{deletionResult=$0;deletionDone.signal()})
  wait(deleted.account.network.file.started,"deletion test reaches file RPC")
  deleted.account.postbox.store.messages[dm.id]=nil;archive.records[dm.id.descriptionKey]?.deletedAt=777
  deleted.account.network.file.finish();wait(deletionDone,"deleted archive receives result")
  expectFile(deletionResult == .success("Premium file transcript"),"file result survives actual deletion")
  expectFile(archive.records[dm.id.descriptionKey]?.deletedAt==777,"ASR preserves actual deletion timestamp")
  expectFile(deleted.account.postbox.store.messages[dm.id]==nil,"ASR never resurrects deleted original")
  deletionDisposable.dispose();NagramiXMessageArchive.registered=nil
  configure(.apple);let apple=context(),am=message(apple)
  AudioBoundary.started=DispatchSemaphore(value:0);let appleDone=DispatchSemaphore(value:0);var appleResult:Result<String,NagramiXTranscriptionFailure>?
  let appleDisposable=NagramiXTranscriptionRuntime.transcribe(context:apple,messageId:am.id).start(next:{appleResult=$0;appleDone.signal()})
  wait(AudioBoundary.started,"explicit Apple still starts");AudioBoundary.finish(.success("chosen Apple"));wait(appleDone,"explicit Apple completes")
  expectFile(appleResult == .success("chosen Apple") && apple.account.network.file.calls==0,"manual provider is honored")
  appleDisposable.dispose();original(apple,am)
  print("PASS Premium file transcription checks: \(asrChecks)")
 }
}
'''
 c=c.replace('UserDefaults.standard','fileTestDefaults')
 c='import Foundation\nlet fileTestSuite="NagramiX.FileASR.Tests."+UUID().uuidString\nlet fileTestDefaults=UserDefaults(suiteName:fileTestSuite)!\n'+c
 marker='@main struct PremiumFileTranscriptionChecks'
 pos=c.index(' static func main() {',c.index(marker))+len(' static func main() {')
 c=c[:pos]+'''\n  defer {fileTestDefaults.removePersistentDomain(forName:fileTestSuite)}
  let mainQueueReady=DispatchSemaphore(value:0)
  DispatchQueue.global().async{OperationQueue.main.addOperation{mainQueueReady.signal()}}
  wait(mainQueueReady,"fixture services main queue while waiting")
'''+c[pos:]
 return c

def negatives(text):
 for name,old,new,label in [
  ('missing-file-route','if provider == .telegram {','if provider == .apple {','Premium transcript returned'),
  ('original-id-eligible','&& !nagramiXCanTranscribeTemporaryMedia(message)','&& nagramiXCanTranscribeTemporaryMedia(message)','original remains blocked'),
  ('partial-accepted','guard (value.flags & 1) == 0, value.text.utf16.count <= 100_000','guard value.text.utf16.count <= 100_000','incomplete response is not stored'),
  ('wrong-native-field','tlStoreReference(_tlObject, 24, file.tlObject)','tlStoreReference(_tlObject, 32, file.tlObject)','RPC contains only named file'),
 ]:
  assert old in text,name
  yield name,text.replace(old,new,1),'FAIL '+label
