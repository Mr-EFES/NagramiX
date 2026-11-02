import Foundation
import Display
import AccountContext
import TelegramPresentationData
import NagramiXMediaSettings
import NagramiXCore

func nagramiXRoundQualityTitle(_ quality: NagramiXRoundVideoSettings.Quality) -> String {
    switch quality { case .standard: return "Стандарт"; case .high: return "Высокое"; case .maximum: return "Максимум" }
}

private final class NagramiXRoundQualitySheetState {
    weak var sheet: ActionSheetController?
    let data: PresentationData
    let changed: () -> Void
    init(context: AccountContext, changed: @escaping () -> Void) {
        self.data = context.sharedContext.currentPresentationData.with { $0 }
        self.changed = changed
    }
    func render() {
        guard let sheet = self.sheet else { return }
        let value = NagramiXRoundVideoSettings.current
        let supported = NagramiXCinematicCapture.supports(value)
        var items: [ActionSheetItem] = [NagramiXOptionSheetItem(kind: .header(closeTitle: data.strings.nagramiXOptionSheetClose), title: "Настройка кружков", action: { [weak sheet] in sheet?.dismissAnimated() })]
        func header(_ title: String) { items.append(NagramiXOptionSheetItem(kind: .footer, title: title)) }
        func option(_ title: String, subtitle: String = "", selected: Bool, enabled: Bool = true, update: @escaping (inout NagramiXRoundVideoSettings) -> Void) {
            items.append(NagramiXOptionSheetItem(kind: .option(selected: selected, separator: false), title: title, subtitle: subtitle, enabled: enabled, action: { [weak self] in
                guard let self, enabled else { return }
                var next = NagramiXRoundVideoSettings.current
                guard next.enabled else { return }
                update(&next)
                guard !next.cinematic || NagramiXCinematicCapture.supports(next) else { return }
                NagramiXRoundVideoSettings.update(next)
                self.changed()
                self.render()
            }))
        }
        header("КАЧЕСТВО")
        for quality in NagramiXRoundVideoSettings.Quality.allCases {
            var candidate = value; candidate.quality = quality
            let rate = String(format: "%.1f", Double(quality.bitRate) / 1_000_000).replacingOccurrences(of: ".", with: ",")
            option("\(quality.rawValue)×\(quality.rawValue) · \(nagramiXRoundQualityTitle(quality))", subtitle: "\(value.frameRate.rawValue) FPS · \(rate) Мбит/с · \(value.codec == .h264 ? "H.264 (AVC)" : "H.265 (HEVC)")", selected: value.quality == quality, enabled: !value.cinematic || NagramiXCinematicCapture.supports(candidate), update: { $0.quality = quality })
        }
        header("ЧАСТОТА КАДРОВ")
        for fps in NagramiXRoundVideoSettings.FrameRate.allCases {
            var candidate = value; candidate.frameRate = fps
            option("\(fps.rawValue) кадров/с", selected: value.frameRate == fps, enabled: !value.cinematic || NagramiXCinematicCapture.supports(candidate), update: { $0.frameRate = fps })
        }
        header("КОДЕК")
        option("H.264 (AVC)", subtitle: "Стандартное сжатие", selected: value.codec == .h264, update: { $0.codec = .h264 })
        option("H.265 (HEVC)", subtitle: "Эффективное сжатие", selected: value.codec == .hevc, update: { $0.codec = .hevc })
        header("КИНОЭФФЕКТ")
        option("Включено", selected: value.cinematic && supported, enabled: supported, update: { $0.cinematic = true })
        option("Выключено", selected: !value.cinematic || !supported, update: { $0.cinematic = false })
        if !supported { items.append(NagramiXOptionSheetItem(kind: .footer, title: "Киноэффект недоступен для выбранных параметров или устройства. Требуются iOS 26 и поддерживаемые камеры.")) }
        sheet.setItemGroups([ActionSheetItemGroup(items: items)])
    }
}

func nagramiXRoundQualitySheet(context: AccountContext, changed: @escaping () -> Void) -> ActionSheetController {
    let state = NagramiXRoundQualitySheetState(context: context, changed: changed)
    let sheet = ActionSheetController(presentationData: state.data)
    state.sheet = sheet
    // The sheet retains its state; the state and item callbacks refer back weakly.
    sheet.dismissed = { [state] _ in state.sheet = nil }
    state.render()
    return sheet
}
