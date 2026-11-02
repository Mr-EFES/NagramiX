import Foundation
#if canImport(FoundationNetworking)
import FoundationNetworking
#endif
@main struct Tests {
 static func main() throws {
  var c=NagramiXTranscriptionConfiguration();c.provider = .grok;c.language="ru-RU";c.cloudAllowed["grok"]=true
  let audio=Data([0x41,0x42,0x43]);let r=try NagramiXTranscriptionCloudCodec.request(configuration:c,key:"xai-personal",audio:audio)
  precondition(r.url?.absoluteString == "https://api.x.ai/v1/stt" && r.value(forHTTPHeaderField:"Authorization") == "Bearer xai-personal")
  let body=String(decoding:r.httpBody!,as:UTF8.self)
  precondition(body.contains("grok-voice-transcribe-2.0") && body.contains("name=\"language\"\r\n\r\nru") && body.contains("ABC"))
  precondition(!body.contains("response_format") && body.range(of:"name=\"model\"")!.lowerBound < body.range(of:"name=\"file\"")!.lowerBound)
  let text=try NagramiXTranscriptionCloudCodec.response(provider:.grok,status:200,data:Data("{\"text\":\"Привет\"}".utf8));precondition(text == "Привет")
  c.language="ru_RU"
  let underscore=try NagramiXTranscriptionCloudCodec.request(configuration:c,key:"xai-personal",audio:audio)
  precondition(String(decoding:underscore.httpBody!,as:UTF8.self).contains("name=\"language\"\r\n\r\nru\r\n"))
  c.cloudAllowed["grok"]=false
  do { _=try NagramiXTranscriptionCloudCodec.request(configuration:c,key:"xai-personal",audio:audio); fatalError("consent") } catch NagramiXTranscriptionFailure.cloudPermission {}
  let old=Data("{\"enabled\":true,\"automatic\":false,\"provider\":\"groq\",\"language\":\"ru-RU\",\"whisper\":\"base\",\"wifiOnly\":true,\"cloudAllowed\":{},\"models\":{},\"credentialRevision\":\"old\",\"revision\":\"old\"}".utf8)
  let decoded=try JSONDecoder().decode(NagramiXTranscriptionConfiguration.self,from:old);precondition(decoded.provider == .groq && decoded.whisper == .base)
  let all=NagramiXWhisperModel.allCases;precondition(all.count == 33 && Set(all.map(\.fileName)).count == 33 && all.allSatisfy {$0.sha256.count == 64 && $0.size > 0})
  print("PASS: Grok own-key / consent / multipart / legacy Groq configuration / pinned model catalog")
 }
}
