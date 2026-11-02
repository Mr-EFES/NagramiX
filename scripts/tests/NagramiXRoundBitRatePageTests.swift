@main struct RoundBitRatePageTests {
    static func main() {
        var checks = 0
        func check(_ condition: @autoclosure () -> Bool, _ message: String) {
            checks += 1
            if !condition() { FileHandle.standardError.write(Data(("FAIL: " + message + "\n").utf8)); exit(1) }
        }
        func select(_ page: PageHarness, _ section: Int, _ row: Int) {
            page.tableView(page.table, didSelectRowAt: IndexPath(row: row, section: section))
        }
        NagramiXRoundVideoSettings.update(.init(enabled: true, quality: .maximum, bitRate: 1_300_000))
        let page = PageHarness(), table = page.table
        let sliderCell = table.cells[IndexPath(row: 0, section: 1)] as! NagramiXRoundBitRateCell
        let identities = table.cells.filter { $0.key.section < 4 }.mapValues(ObjectIdentifier.init)
        check(page.numberOfSections(in: table) == 5, "supported 30 FPS has quality/bitrate/FPS/codec/cinematic sections")
        check((0..<5).map { page.tableView(table, titleForHeaderInSection: $0)! } == ["КАЧЕСТВО","БИТРЕЙТ","ЧАСТОТА КАДРОВ","КОДЕК","КИНОЭФФЕКТ"], "bitrate appears exactly after quality")
        check((0..<5).map { page.tableView(table, numberOfRowsInSection: $0) } == [3,1,2,2,2], "slider has a single dedicated row")
        for step in 0...10 {
            sliderCell.slider.value = Float(step) + (step == 10 ? 0 : 0.2)
            sliderCell.valueChanged()
            let value = NagramiXRoundVideoSettings.current
            check(value.bitRate == 1_000_000 + step * 100_000, "slider must persist every 100 kbps step")
            check(sliderCell.slider.value == Float(step), "slider snaps to discrete step")
            check(sliderCell.rateLabel.text == "\(1000 + step * 100)", "right label shows kbps as in reference")
            check(sliderCell.titleLabel.text == "Битрейт: \(nagramiXRoundBitRateText(value.bitRate)) Мбит/с", "slider title shows matching Mbps")
            check(sliderCell.slider.accessibilityValue == "\(nagramiXRoundBitRateText(value.bitRate)) Мбит/с", "VoiceOver reports bitrate")
            for row in 0..<3 {
                let subtitle = table.cells[IndexPath(row: row, section: 0)]!.detailTextLabel!.text!
                check(subtitle.contains("\(nagramiXRoundBitRateText(value.bitRate)) Мбит/с"), "all quality subtitles use the chosen bitrate")
            }
            check(table.actions.isEmpty && table.offset == 71, "slider updates preserve sections and scroll position")
            check(identities.allSatisfy { ObjectIdentifier(table.cells[$0.key]!) == $0.value }, "dragging does not recreate visible cells")
        }
        let changes = page.changes
        sliderCell.valueChanged()
        select(page, 1, 0)
        check(page.changes == changes, "same step and tapping slider row are no-op")
        let outliers: [Float] = [-100, 100, .nan, .infinity]
        for input in outliers {
            let before = NagramiXRoundVideoSettings.current
            sliderCell.slider.value = input; sliderCell.valueChanged()
            if input.isFinite { check(NagramiXRoundVideoSettings.current.bitRate == (input < 0 ? 1_000_000 : 2_000_000), "slider clamps finite outliers") }
            else { check(NagramiXRoundVideoSettings.current == before, "nonfinite slider values never reach encoder") }
        }
        sliderCell.slider.value = 7; sliderCell.valueChanged()
        select(page, 0, 1)
        check(NagramiXRoundVideoSettings.current.quality == .high && NagramiXRoundVideoSettings.current.bitRate == 1_700_000,
              "quality changes preserve independent chosen bitrate")
        select(page, 3, 1)
        check(NagramiXRoundVideoSettings.current.codec == .hevc && NagramiXRoundVideoSettings.current.bitRate == 1_700_000, "codec selector maps to HEVC, preserves bitrate")
        check(table.cells[IndexPath(row: 1, section: 3)]!.accessoryType == .checkmark, "HEVC checkmark displayed")
        check(table.cells[IndexPath(row: 0, section: 0)]!.detailTextLabel!.text!.contains("H.265 (HEVC)"), "quality subtitle agrees with actual selected codec")
        select(page, 4, 0)
        check(NagramiXRoundVideoSettings.current.cinematic, "supported 30 FPS enables cinematic")
        select(page, 2, 1)
        check(NagramiXRoundVideoSettings.current.frameRate == .smooth && !NagramiXRoundVideoSettings.current.cinematic, "60 FPS disables cinematic")
        check(page.numberOfSections(in: table) == 4 && table.actions == [-1], "60 FPS hides only cinematic section 4")
        let beforeStale = NagramiXRoundVideoSettings.current
        select(page, 4, 0); select(page, 0, 3); select(page, 2, 9); select(page, 9, 0)
        check(NagramiXRoundVideoSettings.current == beforeStale, "stale/invalid rows cannot corrupt selection")
        select(page, 2, 0)
        check(page.numberOfSections(in: table) == 5 && table.actions == [-1,1], "return to 30 FPS inserts only cinematic section")
        check(NagramiXRoundVideoSettings.current.bitRate == 1_700_000 && NagramiXRoundVideoSettings.current.codec == .hevc, "FPS round trip preserves bitrate/codec")
        page.cinematicModes[51230] = false
        select(page, 0, 1)
        check(page.numberOfSections(in: table) == 4, "unsupported device/mode hides cinematic")
        let saved = NagramiXRoundVideoSettings.current
        var off = saved; off.enabled = false
        NagramiXRoundVideoSettings.update(off)
        let beforeOff = page.changes
        sliderCell.slider.value = 2; sliderCell.valueChanged()
        select(page, 0, 0); select(page, 2, 1); select(page, 3, 0)
        check(NagramiXRoundVideoSettings.current == off && page.changes == beforeOff, "master OFF never writes a stale settings selection")
        check(!sliderCell.slider.isEnabled && sliderCell.slider.value == 7, "OFF drag restores saved step and disables slider")
        var on = off; on.enabled = true; NagramiXRoundVideoSettings.update(on)
        let reopened = PageHarness()
        let reopenedCell = reopened.table.cells[IndexPath(row: 0, section: 1)] as! NagramiXRoundBitRateCell
        check(reopenedCell.slider.value == 7 && reopenedCell.rateLabel.text == "1700", "Back/reopen retains slider bitrate")
        check(table.offset == 71 && identities.allSatisfy { ObjectIdentifier(table.cells[$0.key]!) == $0.value }, "all parameter changes preserve existing rows and offset")
        print("PASS: \(checks) actual slider/page/settings/codec/FPS/cinematic/stale-action checks; UIKit layout boundary")
    }
}
