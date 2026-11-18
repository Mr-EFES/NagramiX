@main struct RoundQualitySheetNavigationTests {
    static func main() {
        let initial = chatMediaEditorRoundVideoValues(base())
        var received: [[Int]] = []
        let sheet = nagramiXRoundQualitySheet(presentationData: PresentationData(), values: initial) {
            received.append($0)
        }
        let host = sheet.actionSheetNode.itemGroupsContainerNode
        func rows() -> [NagramiXRoundQualitySheetItem] {
            return host.displayed.map { $0 as! NagramiXRoundQualitySheetItem }
        }

        check(rows().isEmpty && host.layouts == 0, "opening before presentation defers layout")
        sheet.appear()
        check(rows().count == 6, "four parameters and Apply are visible on initial presentation")
        let fieldTitles = rows().dropFirst().dropLast().map(\.title)
        check(rows().dropFirst().dropLast().allSatisfy { $0.kind == .parameter && $0.action != nil }, "all field rows are actionable")
        check(rows()[0].back == nil && rows()[0].close != nil, "main sheet shows only Close in the header")

        rows()[1].action?()
        check(rows().count == 4, "options are laid out before the next tap")
        check(rows()[0].title == fieldTitles[0] && rows()[0].back != nil, "resolution page has its own heading and Back")
        check(rows().dropFirst().map(\.value) == ["480 × 480", "512 × 512", "640 × 640"], "all three resolutions are selectable")
        check(rows().dropFirst().allSatisfy { $0.kind == .option && $0.action != nil } && rows().filter(\.selected).count == 1, "options show a single current choice")
        rows()[2].action?()
        check(rows().count == 6 && rows()[1].value.contains("512 × 512"), "selection immediately returns to the updated parameter sheet")
        rows()[1].action?()
        check(rows()[2].selected, "reopening reflects the pending selection")
        rows()[0].back?()
        check(rows().count == 6 && rows()[1].value.contains("512 × 512"), "Back keeps the current draft")
        check(received.isEmpty, "choosing or backing out does not apply the draft")

        for (index, optionCount, picked) in [(2, 5, 4), (3, 3, 2), (4, 3, 2), (1, 4, 3)] {
            rows()[index].action?()
            check(rows().count == optionCount && rows()[0].title == fieldTitles[index - 1] && rows().filter(\.selected).count == 1, "each options page lays out a current selection and a field heading")
            rows()[picked].action?()
            check(rows().count == 6, "selection returns to the complete sheet")
        }
        check(rows()[1].value.contains("640 × 640") && rows()[3].value.contains("HEVC"), "summary shows new values")
        let apply = rows().last
        check(apply?.kind == .apply, "apply remains available after editing all fields")
        apply?.action?()
        apply?.action?()
        check(received == [[640, 60, 1, 1_300_000]] && sheet.closes == 1, "Apply commits the four settings once")
        check(nagramiXRoundVideoQualityCode(side: initial.nagramiXRoundTuning![0]) == "SD" && nagramiXRoundVideoQualityCode(side: 512) == "HQ" && nagramiXRoundVideoQualityCode(side: received[0][0]) == "MAX", "toolbar reflects the committed resolution")

        let cancelled = nagramiXRoundQualitySheet(presentationData: PresentationData(), values: initial) { received.append($0) }
        cancelled.appear()
        let cancelledHost = cancelled.actionSheetNode.itemGroupsContainerNode
        (cancelledHost.displayed[1] as! NagramiXRoundQualitySheetItem).action?()
        (cancelledHost.displayed[3] as! NagramiXRoundQualitySheetItem).action?()
        (cancelledHost.displayed[4] as! NagramiXRoundQualitySheetItem).action?()
        let lastOptions = cancelledHost.displayed.map { $0 as! NagramiXRoundQualitySheetItem }
        lastOptions[0].close?()
        lastOptions[2].action?()
        check(cancelled.closes == 1 && received.count == 1, "Close from a field discards the draft and late actions")
        print("PASS four options pages, relayout, selection, Back, Close, Apply and SD/HQ/MAX")
    }
}
