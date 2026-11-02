import Foundation
@main struct Tests {
 static func main() {
  let defaults = UserDefaults(suiteName: UUID().uuidString)!
  precondition(!NagramiXRoundVideoSettings.read(from: defaults).cinematic)
  for quality in NagramiXRoundVideoSettings.Quality.allCases {
   for codec in NagramiXRoundVideoSettings.Codec.allCases {
    var value = NagramiXRoundVideoSettings(enabled: true, quality: quality, frameRate: .smooth, codec: codec, cinematic: true)
    NagramiXRoundVideoSettings.update(value, in: defaults)
    precondition(NagramiXRoundVideoSettings.read(from: defaults) == value)
    let resolved = value.resolved(supports60FPS: false, in: defaults)
    precondition(resolved.frameRate == .standard && resolved.cinematic && resolved.quality == quality && resolved.codec == codec)
    value = resolved; value.enabled = false
    NagramiXRoundVideoSettings.update(value, in: defaults)
    precondition(NagramiXRoundVideoSettings.read(from: defaults).cinematic)
   }
  }
  print("PASS: cinematic default OFF, persistence, FPS fallback preserves effect/quality/codec, master OFF preserves preference")
 }
}
