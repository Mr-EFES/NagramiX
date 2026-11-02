@main struct Tests {
    static var checks=0
    static func check(_ value: @autoclosure ()->Bool,_ label: String) { checks += 1;precondition(value(),label) }
    static func main() {
        let person=EnginePeer(firstName:"Анастасия Владимировна",lastName:"Длинная Фамилия")
        let pin=PinHost()
        let old=pin.build(person,legacy:true),updated=pin.build(person)
        check(!old.text.contains(person.lastName) && old.textLayout == .singleLine,"old pin loses surname and uses clipped action")
        check(updated.text == "Закрепить у меня и Анастасия Владимировна Длинная Фамилия","pin contains every part of full name")
        check(updated.textLayout == .multiline,"native multiline action selected")
        let controller=ActionController();updated.action(controller,0)
        check(controller.dismissed && pin.calls.count == 1 && pin.calls[0].0 && !pin.calls[0].1,"pin-for-both action scope and dismissal preserved")
        pin.presentationData.nameDisplayOrder=true
        check(pin.build(person).text == "Закрепить у меня и Длинная Фамилия Анастасия Владимировна","name display order respected")

        let host=MeasureHost();var presentation=PresentationData()
        host.state=ItemsState(mergedItems:[Item(peer:person,reaction:nil,timestamp:1)],totalCount:1)
        host.nagramiXMeasureRows(presentationData:presentation,width:280)
        check(host.nagramiXNameMeasureNode.maximumNumberOfLines == 0,"unlimited measured title lines")
        let row=host.nagramiXRowLayout.frame(at:0,width:280)
        check(row.height > 56,"screenshot read-list name grows row beyond fixed native height")
        check(host.nagramiXNameMeasures.keys.first!.text.contains(person.lastName),"measurement uses full name")
        let firstCalls=host.nagramiXNameMeasureNode.measurements
        host.nagramiXMeasureRows(presentationData:presentation,width:280)
        check(host.nagramiXNameMeasureNode.measurements == firstCalls,"unchanged layout uses cached name measurement")
        host.nagramiXMeasureRows(presentationData:presentation,width:220)
        check(host.nagramiXNameMeasureNode.measurements == firstCalls+1,"width change remeasures")
        presentation.listsFontSize.baseDisplaySize=34
        host.nagramiXMeasureRows(presentationData:presentation,width:220)
        check(host.nagramiXRowLayout.frame(at:0,width:220).height > row.height,"large font gets sufficient row height")
        presentation.nameDisplayOrder=true
        host.nagramiXMeasureRows(presentationData:presentation,width:220)
        check(host.nagramiXNameMeasures.keys.first!.text.hasPrefix(person.lastName),"name order invalidates measurement cache")
        let measured=host.nagramiXNameMeasureNode.measurements
        host.state.mergedItems[0].reaction=1
        host.nagramiXMeasureRows(presentationData:presentation,width:220)
        check(host.nagramiXNameMeasureNode.measurements == measured+1,"reaction column reserves space and invalidates width cache")
        for variant in 0..<5 {
            var decorated=person
            if variant==0 { decorated.isScam=true }
            if variant==1 { decorated.isFake=true }
            if variant==2 { decorated.emojiStatus=1 }
            if variant==3 { decorated.isVerified=true }
            if variant==4 { decorated.isPremium=true }
            let inset=nagramiXReactionCredibilityInset(peer:decorated,presentationData:presentation,premiumDisabled:false)
            check(inset>0,"native badge space retained")
            check(nagramiXReactionNameWidth(width:280,hasReaction:true,credibilityInset:inset) < nagramiXReactionNameWidth(width:280,hasReaction:true,credibilityInset:0),"badge reduces actual measured name column")
        }
        var premium=person;premium.isPremium=true
        check(nagramiXReactionCredibilityInset(peer:premium,presentationData:presentation,premiumDisabled:true)==0,"disabled premium icon reserves no phantom space")
        for text in ["Ли",String(repeating:"ИмяФамилия",count:70),"👩🏽‍🚀 \u{200f}أسماء طويلة للغاية", "姓 名前 フルネーム", "Ива\u{0301}н Фамилия"] {
            host.state=ItemsState(mergedItems:[Item(peer:EnginePeer(firstName:text,lastName:""),reaction:nil,timestamp:nil)],totalCount:1)
            host.nagramiXMeasureRows(presentationData:presentation,width:260)
            check(host.nagramiXNameMeasures.count==1,"old peer cache pruned")
            check(host.nagramiXNameMeasures.keys.first!.text==text,"unicode/combining/emoji/long name passed intact to native text measurement")
            let height=host.nagramiXRowLayout.frame(at:0,width:260).height
            check(height>=112,"large-font native minimum preserved")
        }
        host.state=ItemsState();host.nagramiXMeasureRows(presentationData:presentation,width:260)
        check(host.nagramiXNameMeasures.isEmpty && host.nagramiXRowLayout.contentHeight==10,"empty list clears cache, keeps native insets")

        // Exact production geometry vs a linear reference across irregular rows,
        // unloaded tails, negative overscroll and visible regions past the end.
        for count in 0..<90 {
            let loaded=count/2
            let heights=(0..<loaded).map { CGFloat(44+($0*37)%171) }
            let layout=NagramiXReactionRowLayout(heights:heights,count:count,placeholderHeight:44)
            var expectedY: CGFloat=5
            for index in 0..<count {
                let frame=layout.frame(at:index,width:280)
                let height=index<loaded ? max(44,heights[index]) : 44
                check(frame.minY==expectedY && frame.height==height,"loaded and placeholder frames have no gaps/overlap")
                expectedY += height
            }
            check(layout.contentHeight==expectedY+5,"scroll/footer height equals all measured rows plus native insets")
            for y in stride(from:-300,through:Int(layout.contentHeight)+300,by:73) {
                let bounds=CGRect(x:0,y:y,width:280,height:187)
                let expected=(0..<count).filter { index in
                    let f=layout.frame(at:index,width:280);return f.maxY>=bounds.minY && f.minY<=bounds.maxY
                }
                check(Array(layout.visibleRange(in:bounds))==expected,"binary visible selection matches actual variable frames")
            }
        }
        let huge=NagramiXReactionRowLayout(heights:[80,120],count:1_000_000_000,placeholderHeight:44)
        check(huge.visibleRange(in:CGRect(x:0,y:43_999_999_000,width:280,height:300)).count<10,"huge unloaded total remains bounded during scrolling")
        let negative=NagramiXReactionRowLayout(heights:[1],count:-1,placeholderHeight:0)
        check(negative.count==0 && negative.visibleRange(in:.zero).isEmpty,"empty/invalid counts never generate negative item indexes")
        print("PASS \(checks) checks; extracted name measurement/cache, native pin actions and variable row geometry; UIKit/CoreText boundaries")
    }
}
