@main enum RoundSendLayoutTests {
    static func main() {
        // On a 390pt phone the former 24pt time label occupied the native cover button.
        let oldTrackTop: CGFloat = 688
        let oldTime = CGRect(x: 16, y: oldTrackTop - 28, width: 358, height: 24)
        let oldCover = CGRect(x: 130, y: oldTrackTop - 1 - 26, width: 130, height: 26)
        precondition(oldTime.intersects(oldCover))

        let screens = [CGSize(width: 320, height: 568), CGSize(width: 375, height: 667),
                       CGSize(width: 390, height: 844), CGSize(width: 430, height: 932),
                       CGSize(width: 667, height: 375), CGSize(width: 844, height: 390),
                       CGSize(width: 768, height: 1024)]
        var layouts = 0
        for size in screens {
            let landscape = size.width > size.height
            let top: CGFloat = landscape ? 44 : 72
            let track = CGRect(x: landscape ? 64 : 9, y: size.height - (landscape ? 58 : 156),
                               width: size.width - (landscape ? 136 : 18), height: 39)
            for hasCover in [false, true] {
                for hasTime in [false, true] {
                    for scale: CGFloat in [1, 1.6, 2.8] {
                        let width = track.width - 12
                        let timeWidth = track.width - 128
                        let title = ceil(21 * scale)
                        let hint = ceil(17 * scale) * ceil(198 * scale / width)
                        let time = hasTime ? ceil(17 * scale) * ceil(130 * scale / timeWidth) : 0
                        let coverHeight = max(44, 8 + ceil(17 * scale) * ceil(175 * scale / (width - 50)))
                        let cover = hasCover ? CGSize(width: min(width, ceil(175 * scale) + 50), height: coverHeight) : .zero
                        let rows = NagramiXRoundSendRows(track: track, top: top, previewLimit: size, textWidth: width,
                            timeWidth: timeWidth, titleHeight: title, hintHeight: hint, timeHeight: time, coverSize: cover)
                        precondition(rows.preview.height == rows.preview.width && rows.preview.width > 0)
                        precondition(rows.preview.minY >= top && rows.preview.midX == track.midX)
                        let frames = [rows.title, rows.preview, rows.hint, rows.time, rows.cover, track].filter { !$0.isEmpty }
                        for (above, below) in zip(frames, frames.dropFirst()) {
                            precondition(above.maxY <= below.minY)
                        }
                        if hasCover { precondition(rows.cover.maxY == track.minY - 4 && rows.cover.height >= 44) }
                        if hasTime { precondition(rows.time.height == time && rows.time.midY == rows.controlsY) }
                        let mute = CGRect(x: track.minX + 7, y: rows.controlsY - 20, width: 40, height: 40)
                        let counter = CGRect(x: track.maxX - 55, y: rows.controlsY - 16.5, width: 64, height: 38)
                        for side in [mute, counter] {
                            precondition(!side.intersects(rows.time) || rows.time.isEmpty)
                            precondition(!side.intersects(rows.cover) || rows.cover.isEmpty)
                            precondition(!side.intersects(rows.preview))
                        }
                        if !landscape && scale == 1 {
                            precondition(!rows.title.isEmpty && !rows.hint.isEmpty)
                        }
                        layouts += 1
                    }
                }
            }
        }
        print("PASS: original collision reproduced; \(layouts) portrait, landscape, multiline and optional-control layouts")
    }
}
