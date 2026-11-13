"""Реальный recognizer/history с независимой аффинной границей UIKit."""
from single_touch_message_selection_runtime import production, HISTORY_FIELDS, ROOT, HISTORY, HELPER
from validate_quick_format import block

VIEW_BOUNDARY = r'''
// Explicit UIKit geometry boundary. Coordinates pass through a view hierarchy
// and inverse affine transforms; this does not claim physical UIKit arbitration.
struct SelectionTestAffine {
    var a: CGFloat = 1, b: CGFloat = 0, c: CGFloat = 0, d: CGFloat = 1, tx: CGFloat = 0, ty: CGFloat = 0
    func apply(_ p: CGPoint) -> CGPoint { CGPoint(x:a*p.x+c*p.y+tx,y:b*p.x+d*p.y+ty) }
    func invert(_ p: CGPoint) -> CGPoint {
        let det=a*d-b*c, x=p.x-tx, y=p.y-ty
        precondition(abs(det)>0.0001)
        return CGPoint(x:(d*x-c*y)/det,y:(a*y-b*x)/det)
    }
}
class UIView {
    var gestureRecognizers: [UIGestureRecognizer]?
    var offset = CGPoint.zero
    var bounds = CGRect(x:0,y:0,width:390,height:800)
    var affine = SelectionTestAffine()
    weak var superview: UIView?
    func addSubview(_ view:UIView) { view.superview=self }
    func addGestureRecognizer(_ gesture: UIGestureRecognizer) {
        gesture.view = self
        if gestureRecognizers == nil { gestureRecognizers = [] }
        gestureRecognizers?.append(gesture)
    }
    func toRoot(_ point:CGPoint)->CGPoint {
        let p=affine.apply(CGPoint(x:point.x-bounds.minX,y:point.y-bounds.minY))
        let parent=CGPoint(x:p.x+offset.x,y:p.y+offset.y)
        return superview?.toRoot(parent) ?? parent
    }
    func fromRoot(_ point:CGPoint)->CGPoint {
        let p=superview?.fromRoot(point) ?? point
        let local=affine.invert(CGPoint(x:p.x-offset.x,y:p.y-offset.y))
        return CGPoint(x:local.x+bounds.minX,y:local.y+bounds.minY)
    }
    func convert(_ point: CGPoint, to other: UIView?) -> CGPoint {
        let root=toRoot(point)
        return other?.fromRoot(root) ?? root
    }
}
'''
FIELDS = HISTORY_FIELDS + '\n    var rotated = false\n'


def fixture(source):
    helper,methods=production(source)
    boundary=(ROOT/'scripts/tests/NagramiXMessageDragSelectionBoundary.swift').read_text()
    boundary=boundary.replace(block(boundary,'class UIView {'),VIEW_BOUNDARY,1)
    boundary=boundary.replace('    let view = UIView()\n    let scrollGestureHostView = UIView()', '    let view = UIView()\n    var scrollGestureHostView = UIView()',1)
    tests=(ROOT/'scripts/tests/NagramiXMessageDragSelectionChecks.swift').read_text()
    methods=methods.replace('@objc ','').replace('#selector(self.nagramiXSingleSelectionPan(_:))','"single-selection"')
    return 'import Foundation\n'+boundary+'\n'+helper+'\nfinal class HistoryHarness {\n'+FIELDS+methods+'\n'+tests+'\n'+CHECKS+'\n}\n@main struct Main { static func main() { HistoryHarness.checkAll(); HistoryHarness.checkVisualColumn() } }\n'


CHECKS = r'''
    static func checkVisualColumn() {
        let oldChecks=checks
        for rotated in [true,false] { for nestedHost in [false,true] { for width:CGFloat in [320,390,744] { for safeLeft:CGFloat in [0,20,44] {
            let h=HistoryHarness();h.rotated=rotated
            let window=UIView(),wrapper=UIView()
            window.bounds=CGRect(x:0,y:0,width:width+100,height:1000)
            wrapper.bounds=CGRect(x:0,y:0,width:width,height:800)
            wrapper.offset=CGPoint(x:31,y:43)
            if rotated { wrapper.affine=SelectionTestAffine(a:-1,d:-1,tx:width,ty:800) }
            window.addSubview(wrapper);wrapper.addSubview(h.listView.view)
            h.listView.view.bounds=CGRect(x:0,y:0,width:width,height:800)
            h.frame=CGRect(x:31,y:43,width:width,height:800)
            h.insets=Insets(left:safeLeft,top:60,bottom:50)
            if nestedHost {
                h.listView.view.addSubview(h.listView.scrollGestureHostView)
                h.listView.scrollGestureHostView.offset=CGPoint(x:7,y:25)
                h.listView.scrollGestureHostView.bounds=CGRect(x:0,y:1200,width:width,height:800)
            } else { h.listView.scrollGestureHostView=h.listView.view }
            h.nagramiXBindSingleSelection()
            let host=h.listView.scrollGestureHostView
            let r=host.gestureRecognizers!.last as! NagramiXMessageDragSelectionRecognizer
            func point(_ visualX:CGFloat,_ visualY:CGFloat)->CGPoint {
                window.convert(CGPoint(x:31+visualX,y:43+visualY),to:host)
            }
            // These are screen-space expectations, independent of list-space x.
            for y:CGFloat in [100,180,320,500,680] {
                expect(r.shouldBeginAt?(point(safeLeft+20,y)) == true,"visual left checkbox column starts selection")
                expect(r.shouldBeginAt?(point(width-safeLeft-20,y)) == false,"visual right side remains normal scroll")
                expect(r.shouldBeginAt?(point(safeLeft+90,y)) == false,"message bubble does not steal scrolling")
            }
            let visualTop:CGFloat = rotated ? 50 : 60
            let visualBottom:CGFloat = rotated ? 740 : 750
            for y in [visualTop+2,visualBottom-2] { expect(r.shouldBeginAt?(point(safeLeft+20,y)) == true,"existing vertical safe area stays in list coordinates") }
            for y in [visualTop-2,visualBottom+2] { expect(r.shouldBeginAt?(point(safeLeft+20,y)) == false,"header and input panel remain outside selection") }
            h.controllerInteraction.selectionState=nil
            expect(r.shouldBeginAt?(point(safeLeft+20,200)) == false,"left drag requires selection mode")
            h.controllerInteraction.selectionState=SelectionState(selectedIds:[1,90])
            h.isSelectionGestureEnabled=false
            expect(r.shouldBeginAt?(point(safeLeft+20,200)) == false,"disabled selection gesture stays disabled")
            h.isSelectionGestureEnabled=true
            // A tall first row: the touch starts far below its checkbox; the
            // complete left strip belongs to the row, not just the icon itself.
            let rows:[(Int,CGFloat,CGFloat)] = rotated ? [(1,350,400),(2,220,120),(3,80,130)] : [(1,60,400),(2,470,120),(3,600,130)]
            h.historyView=ChatHistoryView(filteredEntries:rows.map { .MessageEntry(Message(id:$0.0,index:$0.0),0,false,nil,0,0) })
            h.listView.nodes=rows.map { ChatMessageItemView([Message(id:$0.0,index:$0.0)],frame:CGRect(x:0,y:$0.1,width:width,height:$0.2)) }
            let start=point(safeLeft+20,400)
            expect(r.shouldBeginAt?(start) == true,"tall message accepts entire checkbox column height")
            r.touchesBegan([UITouch(start)],with:UIEvent())
            r.point=point(safeLeft+20,412);r.state = .began;h.nagramiXSingleSelectionPan(r)
            expect(h.controllerInteraction.selectionState?.selectedIds == [1,90],"checked anchor stays checked on visual left drag")
            r.point=point(safeLeft+20,650);r.state = .changed;h.nagramiXSingleSelectionPan(r)
            expect(h.controllerInteraction.selectionState?.selectedIds == [1,2,3,90],"downward screen drag selects following rows with rotated backend")
            r.point=point(safeLeft+20,400);h.nagramiXSingleSelectionPan(r)
            expect(h.controllerInteraction.selectionState?.selectedIds == [1,90],"upward reversal preserves earlier selection")
            r.state = .ended;h.nagramiXSingleSelectionPan(r)
            expect(h.nagramiXSingleSelection == nil,"visual drag releases its state")
            // No intermediate tap/ended event: the same single touch starts on
            // an unchecked row and keeps dragging. There is no two-touch path.
            h.controllerInteraction.selectionState=SelectionState(selectedIds:[90])
            r.reset();let touch=UITouch(start)
            r.touchesBegan([touch],with:UIEvent())
            expect(r.state == .possible && r.initialPoint == start,"one continuous touch accepts unchecked anchor")
            touch.point=point(safeLeft+20,412);r.touchesMoved([touch],with:UIEvent())
            expect(r.forwardedMoves>0,"one-finger held movement reaches native pan without release")
            r.point=touch.point;r.state = .began;h.nagramiXSingleSelectionPan(r)
            expect(h.controllerInteraction.selectionState?.selectedIds == [1,90],"unchecked anchor becomes selected when same touch starts drag")
            r.point=point(safeLeft+20,650);r.state = .changed;h.nagramiXSingleSelectionPan(r)
            expect(h.controllerInteraction.selectionState?.selectedIds == [1,2,3,90],"same held touch expands selected range")
            r.point=start;h.nagramiXSingleSelectionPan(r)
            expect(h.controllerInteraction.selectionState?.selectedIds == [1,90],"same touch reversal retracts later rows")
            r.state = .ended;h.nagramiXSingleSelectionPan(r)
            // Current bounds, not stale frame/portrait width, define the column.
            if rotated {
                h.listView.view.bounds.size.width=width+40
                wrapper.affine.tx=width+40
                expect(r.shouldBeginAt?(point(safeLeft+20,200)) == true,"column follows current bounds after resize")
            }
        }}}}
        print("Visual checkbox column production checks: \(checks-oldChecks)")
    }
'''
