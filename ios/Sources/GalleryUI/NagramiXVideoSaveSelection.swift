import Foundation
import Postbox
import TelegramCore
import SaveToCameraRoll

// Playback may prefer software-decoded AV1. Photos needs a system-compatible
// file; this selection does not change the player or its quality preferences.
func nagramiXVideoSaveSource(original: FileMediaReference, quality: Int) -> FileMediaReference {
    var best: (priority: Int, file: TelegramMediaFile)?
    for file in original.media.alternativeRepresentations {
        for attribute in file.attributes {
            guard case let .Video(_, size, _, _, _, codec) = attribute,
                  Int(min(size.width, size.height)) == quality,
                  let priority = NagramiXVideoSavePolicy.codecPriority(codec) else { continue }
            if best == nil || priority < best!.priority {
                best = (priority, file)
            }
        }
    }
    return best.map { original.withMedia($0.file) } ?? original
}
