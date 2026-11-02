import Foundation

@main struct FormattingVisualTests {
    static func main() {
        // The previous complete formatting suite now executes the NEW extracted
        // toggle/ownership methods against the real new geometry helper.
        QuickFormattingTests.main()
        if CommandLine.arguments.count > 1 { return }
        var checks = 0
        func check(_ value: @autoclosure () -> Bool, _ message: String) { precondition(value(),message); checks += 1 }
        let inputView = NagramiXFormattingKeyboard(title:"Formatting",height:353)
        for value in [CGFloat.nan, CGFloat.infinity, -1, 0, 353.2] { inputView.updateHeight(value) }
        check(inputView.intrinsicContentSize.height == 353 && inputView.intrinsicInvalidations == 0,"invalid/jittering sizes do not trigger keyboard relayout")
        inputView.updateHeight(216)
        check(inputView.frame.height == 216 && inputView.frame.width == 393 && inputView.intrinsicContentSize.height == 216,"native input view updates exactly its height without adding safe area")
        check(inputView.intrinsicInvalidations == 1 && inputView.layoutInvalidations == 1,"one actual height change invalidates layout once")
        let portrait = CGSize(width:440,height:956), landscape = CGSize(width:956,height:440)
        var metrics = NagramiXFormattingKeyboardGeometry()
        metrics.update(container:portrait,keyboardHeight:353,standardHeight:346,canMeasureSystem:true,interactive:false)
        check(metrics.height == 353,"actual native height wins over the fallback")
        metrics.update(container:portrait,keyboardHeight:44,standardHeight:346,canMeasureSystem:true,interactive:false)
        check(metrics.height == 353,"hardware accessory bar must not shrink the panel")
        metrics.update(container:portrait,keyboardHeight:150,standardHeight:346,canMeasureSystem:true,interactive:true)
        check(metrics.height == 353,"interactive drag must not poison the stable keyboard height")
        metrics.update(container:portrait,keyboardHeight:320,standardHeight:346,canMeasureSystem:false,interactive:false)
        check(metrics.height == 353,"custom keyboard cannot feed its own size back")
        metrics.update(container:portrait,keyboardHeight:0,standardHeight:346,canMeasureSystem:true,interactive:false)
        check(metrics.height == 353,"hidden keyboard does not erase the last stable measurement")
        metrics.update(container:landscape,keyboardHeight:353,standardHeight:209,canMeasureSystem:false,interactive:false)
        check(metrics.height == 209,"rotation uses native oriented fallback, not portrait height")
        metrics.update(container:landscape,keyboardHeight:216,standardHeight:209,canMeasureSystem:true,interactive:false)
        check(metrics.height == 216,"landscape learns its own real keyboard height")
        metrics.update(container:portrait,keyboardHeight:nil,standardHeight:346,canMeasureSystem:false,interactive:false)
        check(metrics.height == 353,"rotation back restores this width's stable measurement")
        for value in [CGFloat.nan,CGFloat.infinity,-1,50,2000] {
            metrics.update(container:portrait,keyboardHeight:value,standardHeight:346,canMeasureSystem:true,interactive:false)
            check(metrics.height == 353,"invalid keyboard observation ignored")
        }
        for width in stride(from:320,through:720,by:10) {
            metrics.update(container:CGSize(width:CGFloat(width),height:1000),keyboardHeight:350,standardHeight:330,canMeasureSystem:true,interactive:false)
            check(metrics.cachedWidthCount <= 4,"native width cache remains bounded")
        }
        metrics.update(container:CGSize(width:CGFloat.nan,height:1000),keyboardHeight:350,standardHeight:330,canMeasureSystem:true,interactive:false)
        check(metrics.height == nil,"invalid container cannot produce an unsafe frame")
        var initial = NagramiXFormattingKeyboardGeometry()
        initial.update(container:portrait,keyboardHeight:nil,standardHeight:346,canMeasureSystem:false,interactive:false)
        check(initial.height == 346,"opening before the software keyboard uses the native layout fallback")
        initial.update(container:portrait,keyboardHeight:nil,standardHeight:CGFloat.nan,canMeasureSystem:false,interactive:false)
        check(initial.height == nil,"missing valid geometry cannot fabricate a hardcoded height")
        // Execute the production grid on normal/old/narrow/rotated sizes and
        // larger captions: non-overlap, readable fitting and internal scrolling.
        for width in [CGFloat(288),304,343,359,377,424,552,940] {
            for height in [CGFloat(80),120,180,263,300] {
                for label in [CGFloat(24),40,60,64,100,160] {
                    for large in [false,true] {
                        let grid = NagramiXFormattingGrid.layout(size:CGSize(width:width,height:height),count:10,minimumLabelWidth:label,minimumKeyHeight:large ? 94 : 64,accessibility:large)
                        check(grid.frames.count == 10 && grid.columns > 0 && grid.columns <= 5,"all ten actions laid out")
                        check(grid.contentSize.width == width && grid.contentSize.height >= height - 0.01,"scroll geometry stays within the keyboard width")
                        for (i,frame) in grid.frames.enumerated() {
                            check(frame.width >= 0 && frame.height >= 60 && frame.minX >= 0 && frame.maxX <= width + 0.01 && frame.maxY <= grid.contentSize.height + 0.01,"finite touch targets are contained")
                            if grid.columns > (large ? 1 : 2) { check(frame.width - 4 >= label - 0.01,"one-line caption has measured space") }
                            for other in grid.frames.prefix(i) { check(!frame.intersects(other),"format keys must never overlap") }
                        }
                    }
                }
            }
        }
        let selected = NagramiXFormattingGrid.layout(size:CGSize(width:424,height:263),count:10,minimumLabelWidth:64,minimumKeyHeight:64,accessibility:false)
        check(selected.columns == 5 && selected.frames[5].minY > selected.frames[0].maxY,"chosen five-by-two layout on Pro Max")
        let oldPhone = NagramiXFormattingGrid.layout(size:CGSize(width:304,height:196),count:10,minimumLabelWidth:64,minimumKeyHeight:64,accessibility:false)
        check(oldPhone.columns == 4,"compact phone stays readable rather than wrapping captions")
        NagramiXFormattingSettings.setEnabled(true)
        let panel = FormattingPanel()
        let editor = panel.richTextInputNode!
        panel.nagramiXUpdateFormattingKeyboardGeometry(container:portrait,keyboardHeight:353,standardHeight:346,interactive:false,isTextInput:true)
        let selection = NSRange(location:1,length:2)
        editor.content = NSAttributedString(string:"А😀Б текст");editor.selectedRange = selection
        let layouts = panel.layoutRequests
        panel.nagramiXToggleFormatting()
        check(panel.nagramiXFormattingKeyboard?.preferredHeight == 353,"input view gets native height before assignment")
        check(panel.layoutRequests == layouts,"toggle must not force a competing immediate chat layout")
        for _ in 0..<40 {
            panel.nagramiXUpdateFormattingKeyboardGeometry(container:portrait,keyboardHeight:320,standardHeight:346,interactive:false,isTextInput:true)
            check(panel.nagramiXFormattingKeyboard?.preferredHeight == 353,"active panel height remains stable across native layouts")
            panel.nagramiXToggleFormatting();panel.nagramiXToggleFormatting()
            check(editor.selectedRange == selection && editor.isInputFirstResponder,"rapid switches preserve selection and first responder")
            check(panel.layoutRequests == layouts,"rapid switches do not move composer via immediate layout")
        }
        panel.nagramiXUpdateFormattingKeyboardGeometry(container:landscape,keyboardHeight:353,standardHeight:209,interactive:false,isTextInput:true)
        check(panel.nagramiXFormattingKeyboard?.preferredHeight == 209,"active rotation uses oriented native fallback")
        let foreign = UIView();panel.nagramiXCloseFormatting(reload:true);editor.keyboardInputView = foreign
        panel.nagramiXUpdateFormattingKeyboardGeometry(container:portrait,keyboardHeight:500,standardHeight:346,interactive:false,isTextInput:true)
        check(panel.nagramiXFormattingGeometry.height == 353,"foreign custom input view does not become a system-keyboard measurement")
        UserDefaults.standard.removeObject(forKey:"nagramix.messages.quickFormatting")
        print("PASS \(checks) native-height/grid/toggle visual integration checks")
    }
}
