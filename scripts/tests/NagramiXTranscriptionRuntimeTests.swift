import Foundation
private var checks=0
private func check(_ value:@autoclosure()->Bool,_ text:String){checks+=1;if !value(){fatalError(text)}}
private func wait(_ value:DispatchSemaphore){check(value.wait(timeout:.now()+5) == .success,"Callback timeout")}
@main struct TranscriptionRuntimeTests{
 static func main()throws{
  let context=AccountContext();let peer=PeerId(value:9)
  func message(_ id:Int32=1,namespace:Int32=0,peerId:PeerId?=nil)->Message{Message(MessageId(peerId:peerId ?? peer,namespace:namespace,id:id),TelegramMediaFile("audio-\(id)"))}
  func configure(_ provider:NagramiXTranscriptionProvider = .apple,automatic:Bool=false){NagramiXTranscriptionSettings.update{$0 = .init();$0.enabled=true;$0.automatic=automatic;$0.provider=provider;$0.cloudAllowed[provider.rawValue]=provider.cloud}}
  configure()
  check(NagramiXTranscriptionRuntime.handles(message()),"Independent engine eligibility without Premium")
  check(!NagramiXTranscriptionRuntime.handles(message(namespace:1)),"No scheduled/local/archive namespace")
  check(!NagramiXTranscriptionRuntime.handles(message(peerId:PeerId(namespace:2,value:9))),"No secret chat")
  let protected=message();protected.protected=true;check(NagramiXTranscriptionRuntime.file(protected)==nil,"Protected media excluded")
  protected.protected=false;protected.containsSecretMedia=true;check(NagramiXTranscriptionRuntime.file(protected)==nil,"View-once excluded")
  protected.containsSecretMedia=false;protected.isSelfExpiring=true;check(NagramiXTranscriptionRuntime.file(protected)==nil,"Expiring media excluded")
  protected.isSelfExpiring=false;(protected.media[0] as! TelegramMediaFile).isVoice=false;check(NagramiXTranscriptionRuntime.file(protected)==nil,"Ordinary audio excluded")
  (protected.media[0] as! TelegramMediaFile).isInstantVideo=true;check(NagramiXTranscriptionRuntime.file(protected) != nil,"Video circle eligible")
  try Data([1,2,3]).write(to:URL(fileURLWithPath:"/tmp/nagramix-asr-boundary-audio.m4a"))
  defer{try? FileManager.default.removeItem(atPath:"/tmp/nagramix-asr-boundary-audio.m4a")}
  var nextId:Int32=10
  func run(provider:NagramiXTranscriptionProvider = .apple,mutate:(Message)->Void={_ in},recognized:Bool=true,automatic:Bool=false,expected:NagramiXTranscriptionFailure?=nil)->Message{
   configure(provider,automatic:automatic);nextId+=1;let message=message(nextId);context.account.postbox.store.messages[message.id]=message
   let complete=DispatchSemaphore(value:0);var result:Result<String,NagramiXTranscriptionFailure>?
   let disposable=NagramiXTranscriptionRuntime.transcribe(context:context,messageId:message.id,automatic:automatic).start(next:{result=$0;complete.signal()})
   if recognized{wait(AudioBoundary.started);check(AudioBoundary.provider==provider,"Exact selected recognizer");mutate(message);AudioBoundary.finish(.success("Дословная речь"))}
   wait(complete);disposable.dispose()
   if let expected{if case let .failure(error)=result{check(error==expected,"Correct runtime error")}else{fatalError("Expected failure \(expected)")}}
   else{if case .success("Дословная речь")=result{}else{fatalError("Expected transcript")}}
   return message
  }
  let first=run(mutate:{$0.attributes.append(DerivedDataMessageAttribute(data:["other":CodableEntry("preserved")!]))})
  check(NagramiXTranscriptionRuntime.cached(first)=="Дословная речь","Per-resource cache stamp")
  check(first.attributes.compactMap{$0 as? DerivedDataMessageAttribute}.first?.data["other"]?.get(String.self)=="preserved","Preserve other derived data")
  let attr=first.attributes.compactMap{$0 as? AudioTranscriptionMessageAttribute}.first!
  check(attr.id==0&&attr.didRate && !attr.isPending,"Local result never rated on Telegram")
  let preparations=NagramiXTranscriptionMedia.preparations;let cached=DispatchSemaphore(value:0)
  let cachedDisposable=NagramiXTranscriptionRuntime.transcribe(context:context,messageId:first.id).start(next:{_ in cached.signal()});wait(cached);cachedDisposable.dispose()
  check(NagramiXTranscriptionMedia.preparations==preparations,"Cache avoids repeat ASR/network")
  _=run(mutate:{_ in NagramiXTranscriptionSettings.update{$0.enabled=false}},expected:.cancelled)
  check(context.account.postbox.store.updates==1,"OFF prevents late write")
  _=run(mutate:{_ in NagramiXTranscriptionSettings.update{$0.language="en-US"}},expected:.cancelled)
  check(context.account.postbox.store.updates==1,"Language change prevents late write")
  _=run(mutate:{$0.media=[TelegramMediaFile("replaced")]},expected:.cancelled)
  check(context.account.postbox.store.updates==1,"Replaced source prevents write")
  _=run(mutate:{context.account.postbox.store.messages[$0.id]=nil},expected:.cancelled)
  check(context.account.postbox.store.updates==1,"Deleted message is not recreated")
  context.engine.resources.complete=false
  let fetches=context.engine.resources.fetches
  _=run(recognized:false,automatic:true,expected:.unavailableMedia)
  check(context.engine.resources.fetches==fetches,"Automatic mode never downloads audio")
  context.engine.resources.complete=true
  NagramiXTranscriptionApple.authorized=false
  _=run(recognized:false,automatic:true,expected:.permission);NagramiXTranscriptionApple.authorized=true
  NagramiXWhisperModels.shared.ready=false
  _=run(provider:.whisper,recognized:false,expected:.missingModel);NagramiXWhisperModels.shared.ready=true
  _=run(provider:.whisper)
  for provider in [NagramiXTranscriptionProvider.groq,.gemini,.chatgpt]{_=run(provider:provider)}
  configure(.telegram);check(!NagramiXTranscriptionRuntime.handles(message()),"Telegram keeps stock quota gates")
  NagramiXTranscriptionSettings.update{$0.enabled=false}
  print("PASS: \(checks) complete production runtime checks at media / Speech / Postbox boundaries")
 }
}
