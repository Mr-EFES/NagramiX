"""Фактический кеш диапазона при непрерывной прокрутке под удерживаемым пальцем."""
from selection_column_coordinates_runtime import fixture as column_fixture,HISTORY,HELPER


def fixture(source):
    code=column_fixture(source)
    marker='}\n@main struct Main { static func main() { HistoryHarness.checkAll(); HistoryHarness.checkVisualColumn() } }\n'
    assert code.count(marker)==1
    return code.replace(marker,CHECKS+'}\n@main struct Main { static func main() { HistoryHarness.checkAll(); HistoryHarness.checkVisualColumn(); HistoryHarness.checkVideoAutoScroll() } }\n',1)


CHECKS = r'''

    static func checkVideoAutoScroll() {
        // A property keeps the lifetime observation weak on old and new Swift.
        // Newer Apple Swift diagnoses never-reassigned local weak variables.
        final class WeakHistoryViewProbe {
            weak var value: MessageHistoryView?
            init(_ value: MessageHistoryView?) { self.value = value }
        }
        let initialChecks=checks
        for nestedHost in [false,true] { for checked in [false,true] {
            let h=HistoryHarness();h.rotated=true
            let window=UIView(),wrapper=UIView()
            wrapper.bounds=CGRect(x:0,y:0,width:390,height:800)
            wrapper.affine=SelectionTestAffine(a:-1,d:-1,tx:390,ty:800)
            wrapper.offset=CGPoint(x:31,y:43)
            window.addSubview(wrapper);wrapper.addSubview(h.listView.view)
            if nestedHost {
                h.listView.view.addSubview(h.listView.scrollGestureHostView)
                h.listView.scrollGestureHostView.offset=CGPoint(x:7,y:25)
                h.listView.scrollGestureHostView.bounds.origin.y=1200
            } else { h.listView.scrollGestureHostView=h.listView.view }
            let original=[ChatMessageItemView([Message(id:1,index:1)],frame:CGRect(x:0,y:300,width:390,height:440)),ChatMessageItemView([Message(id:2,index:2)],frame:CGRect(x:0,y:160,width:390,height:130)),ChatMessageItemView([Message(id:3,index:3)],frame:CGRect(x:0,y:80,width:390,height:70))]
            h.listView.nodes=original
            h.historyView=ChatHistoryView(filteredEntries:(1...3).map { .MessageEntry(Message(id:$0,index:$0),0,false,nil,0,0) })
            h.controllerInteraction.selectionState=SelectionState(selectedIds:checked ? [1,90] : [90])
            h.nagramiXBindSingleSelection()
            let host=h.listView.scrollGestureHostView
            let r=host.gestureRecognizers!.last as! NagramiXMessageDragSelectionRecognizer
            func point(_ y:CGFloat)->CGPoint { window.convert(CGPoint(x:51,y:43+y),to:host) }
            let touch=UITouch(point(400));r.touchesBegan([touch],with:UIEvent())
            expect(r.state == .possible,"video: one left touch accepted below tall-row checkbox")
            touch.point=point(412);r.touchesMoved([touch],with:UIEvent())
            r.point=touch.point;r.state = .began;h.nagramiXSingleSelectionPan(r)
            expect(h.controllerInteraction.selectionState?.selectedIds == [1,90],"video: one held touch selects anchor without release")
            r.point=point(730);r.state = .changed;h.nagramiXSingleSelectionPan(r)
            expect(h.controllerInteraction.selectionState?.selectedIds == [1,2,3,90],"video: downward drag marks intervening rows")
            guard let timer=h.selectionScrollActivationTimer else { expect(false,"video: bottom edge schedules continuous scrolling");return }
            expect(timer.active && timer.timeout == 0.45,"video: bottom edge keeps existing activation delay")
            timer.fire()
            guard let display=h.selectionScrollDisplayLink else { expect(false,"video: continuous scrolling starts while held");return }
            var target=3
            h.listView.onScroll = {
                target += 1
                h.listView.nodes=[ChatMessageItemView([Message(id:target,index:target)],frame:CGRect(x:0,y:60,width:390,height:40))]
                h.historyView=ChatHistoryView(filteredEntries:((target-1)...target).map { .MessageEntry(Message(id:$0,index:$0),0,false,nil,0,0) })
            }
            display.update()
            expect(h.listView.scrolls.count == 1 && h.listView.scrolls[0].0 == .up && h.listView.scrolls[0].1 > 0 && h.listView.scrolls[0].1 <= 15,"video: rotated screen-bottom uses correct backend scroll direction")
            expect(h.controllerInteraction.selectionState?.selectedIds == [1,2,3,4,90],"video: stationary held finger selects newly loaded row")
            let cachedView=WeakHistoryViewProbe(h.historyView?.originalView)
            display.update()
            expect(cachedView.value != nil,"video: cached snapshot stays alive across skipped display update")
            display.update()
            expect(h.controllerInteraction.selectionState?.selectedIds == [1,2,3,4,5,6,90],"video: repeated scrolling includes rows between display updates")
            h.listView.onScroll=nil;h.listView.nodes=original
            h.historyView=ChatHistoryView(filteredEntries:(1...6).map { .MessageEntry(Message(id:$0,index:$0),0,false,nil,0,0) })
            r.point=point(600);h.nagramiXSingleSelectionPan(r)
            expect(h.controllerInteraction.selectionState?.selectedIds == [1,2,90],"video: upward reversal removes only later additions")
            expect(display.isPaused,"video: leaving edge pauses auto-scroll")
            r.point=point(400);h.nagramiXSingleSelectionPan(r)
            expect(h.controllerInteraction.selectionState?.selectedIds == [1,90],"video: return to anchor preserves prior checks")
            let finalCachedView=WeakHistoryViewProbe(h.historyView?.originalView)
            h.historyView=nil
            r.state = .ended;h.nagramiXSingleSelectionPan(r)
            expect(finalCachedView.value == nil,"video: cached snapshot releases when gesture ends")
            expect(h.nagramiXSingleSelection == nil && h.selectionScrollDisplayLink == nil && h.selectionScrollActivationTimer == nil,"video: release clears scrolling and gesture state")
        }}
        print("Video held-edge selection checks: \(checks-initialChecks)")
    }
'''
