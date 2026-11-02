import Foundation
private var checks=0
private func check(_ value:@autoclosure()->Bool,_ label:String){checks+=1;if !value(){fatalError(label)}}
@main struct AppleTests {
 static func main()async{
  let url=URL(fileURLWithPath:"/tmp/public-test.m4a")
  func run(automatic:Bool=false,token:NagramiXTranscriptionCancellation=NagramiXTranscriptionCancellation())async->Result<String,NagramiXTranscriptionFailure>{await withCheckedContinuation{continuation in NagramiXTranscriptionApple.transcribe(url:url,language:"ru-RU",automatic:automatic,cancellation:token){continuation.resume(returning:$0)}}}
  check(NagramiXTranscriptionApple.available("ru-RU"),"Real local capability")
  check(!NagramiXTranscriptionApple.available("auto"),"No invented Apple auto language")
  if case .success("Дословно")=await run(){}else{fatalError("Verbatim final")}
  check(SFSpeechRecognizer.lastRequest?.requiresOnDeviceRecognition==true,"Never sends audio to Apple server")
  check(SFSpeechRecognizer.lastRequest?.shouldReportPartialResults==false,"No partial result stored as final")
  SFSpeechRecognizer.local=false
  if case .failure(.unavailable)=await run(){}else{fatalError("No unsupported fallback")}
  check(!NagramiXTranscriptionApple.available("ru-RU"),"Actual unsupported state")
  SFSpeechRecognizer.local=true;SFSpeechRecognizer.status = .notDetermined
  if case .failure(.permission)=await run(automatic:true){}else{fatalError("Automatic permission")}
  check(SFSpeechRecognizer.authorizations==0,"Automatic mode never prompts")
  if case .success=await run(){}else{fatalError("Manual authorization")};check(SFSpeechRecognizer.authorizations==1,"Explicit manual prompt")
  let cancelled=NagramiXTranscriptionCancellation();cancelled.cancel();let count=SFSpeechRecognizer.requests
  if case .failure(.cancelled)=await run(token:cancelled){}else{fatalError("Pre-cancel")};check(SFSpeechRecognizer.requests==count,"No recognizer after cancel")
  SFSpeechRecognizer.stall=true;let token=NagramiXTranscriptionCancellation();let task=Task{await run(token:token)}
  try? await Task.sleep(nanoseconds:100_000_000);token.cancel()
  if case .failure(.cancelled)=await task.value{}else{fatalError("Active cancel")};check(SFSpeechRecognitionTask.cancels>0,"Active native task canceled")
  print("PASS: \(checks) production legacy Speech wrapper checks at Apple boundary")
 }
}
