import Foundation
// Apple API signatures follow the linked iOS 26 documentation. This is an
// execution boundary for ownership/cancellation, not an SDK compatibility test.
struct SpeechResult { let isFinal:Bool;let text:AttributedString }
final class SpeechTranscriber {
 struct Preset { static let transcription=Self() }
 static var isAvailable=true
 static var installed:[Locale]=[Locale(identifier:"en-US")]
 static var supported:[Locale]=[Locale(identifier:"en-US"),Locale(identifier:"ru-RU")]
 static var installedLocales:[Locale]{get async{installed}}
 static var supportedLocales:[Locale]{get async{supported}}
 let results:AsyncThrowingStream<SpeechResult,Error>
 let continuation:AsyncThrowingStream<SpeechResult,Error>.Continuation
 init(locale:Locale,preset:Preset){var captured:AsyncThrowingStream<SpeechResult,Error>.Continuation!;results=AsyncThrowingStream{captured=$0};continuation=captured}
}
final class AVAudioFile { init(forReading url:URL)throws{} }
final class SpeechAnalyzer {
 static var stall=false;static var cancels=0
 let modules:[SpeechTranscriber]
 init(modules:[SpeechTranscriber]){self.modules=modules}
 func start(inputAudioFile file:AVAudioFile,finishAfterFile:Bool=false)async throws{
  if !Self.stall {for module in modules {module.continuation.yield(.init(isFinal:false,text:AttributedString("partial ignored")));module.continuation.yield(.init(isFinal:true,text:AttributedString("Дословная речь")));module.continuation.finish()}}
 }
 func cancelAndFinishNow()async{Self.cancels+=1;for module in modules{module.continuation.finish(throwing:CancellationError())}}
}
final class AssetInstallationRequest{static var installs=0;func downloadAndInstall()async throws{Self.installs+=1}}
enum AssetInventory{static func assetInstallationRequest(supporting modules:[SpeechTranscriber])async throws->AssetInstallationRequest?{AssetInstallationRequest()}}
enum NagramiXTranscriptionApple{static var legacyCalls=0;static func legacy(url:URL,language:String,automatic:Bool,cancellation:NagramiXTranscriptionCancellation,completion:@escaping(Result<String,NagramiXTranscriptionFailure>)->Void){legacyCalls+=1;completion(.failure(.unavailable))}}
