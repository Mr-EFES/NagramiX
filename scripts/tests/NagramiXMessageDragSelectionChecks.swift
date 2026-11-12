    static var checks = 0
    static func expect(_ condition: @autoclosure () -> Bool, _ label: String) {
        checks += 1
        if !condition() { print("FAILED: " + label); exit(96) }
    }
    static func checkAll() {
        // Baseline is protected, including an already-selected anchor and IDs outside the range.
        var model = NagramiXMessageDragSelection<Int, Int>(baseline: [2, 8], anchorId: 2, anchorOrder: 2)
        model.cache((0...9).map { ($0, [$0]) })
        var selected: Set<Int> = [2, 8]
        func apply(_ change: (add: Set<Int>, remove: Set<Int>)) { selected.subtract(change.remove); selected.formUnion(change.add) }
        apply(model.update(targetId: 6, fallbackOrder: 6))
        expect(selected == [2, 3, 4, 5, 6, 8], "fast drag includes intermediate rows")
        apply(model.update(targetId: 3, fallbackOrder: 3))
        expect(selected == [2, 3, 8], "reverse retracts only this gesture")
        apply(model.update(targetId: 2, fallbackOrder: 2))
        expect(selected == [2, 8], "earlier selection survives reversal")
        apply(model.update(targetId: 0, fallbackOrder: 0))
        expect(selected == [0, 1, 2, 8], "crossing anchor extends opposite range")
        let noop = model.update(targetId: 0, fallbackOrder: 0)
        expect(noop.add.isEmpty && noop.remove.isEmpty, "repeated point has no callbacks")
        var paged = NagramiXMessageDragSelection<Int, Int>(baseline: [0], anchorId: 0, anchorOrder: 0)
        paged.cache([(0, [0]), (1, [1, 11]), (2, [2])])
        _ = paged.update(targetId: 2, fallbackOrder: 2)
        paged.cache([(3, [3]), (4, [4])])
        _ = paged.update(targetId: 4, fallbackOrder: 4)
        let reverse = paged.update(targetId: 1, fallbackOrder: 1)
        expect(reverse.remove == [2, 3, 4] && reverse.add.isEmpty, "loaded windows retain the anchor range")
        paged.cacheMissing(order: 90, ids: [1, 12])
        let album = paged.update(targetId: 12, fallbackOrder: 90)
        expect(album.add == [12] && album.remove.isEmpty, "realized album inherits cached group position")
        var missing = NagramiXMessageDragSelection<Int, Int>(baseline: [], anchorId: 1, anchorOrder: 1)
        missing.cacheMissing(order: 3, ids: [3, 4])
        expect(missing.update(targetId: 4, fallbackOrder: 3).add == [1, 3, 4], "newly realized rows include anchor and whole group")

        // Repeated reversal/fast jumps over thousands of rows, deterministic independent oracle.
        var random: UInt64 = 773
        for anchor in [0, 3, 48, 299] {
            let baseline: Set<Int> = [anchor, 17, 90]
            var m = NagramiXMessageDragSelection<Int, Int>(baseline: baseline, anchorId: anchor, anchorOrder: anchor)
            m.cache((0..<300).map { ($0, [$0]) })
            var current = baseline
            for _ in 0..<600 {
                random = random &* 6364136223846793005 &+ 1
                let target = Int((random >> 32) % 300)
                let change = m.update(targetId: target, fallbackOrder: target)
                expect(change.remove.isDisjoint(with: baseline), "earlier selection survives reversal")
                current.subtract(change.remove); current.formUnion(change.add)
                expect(current == baseline.union(Set(min(anchor, target)...max(anchor, target))), "range matches chronological oracle")
            }
        }
        let inside = CGPoint(x: 22, y: 100)
        expect(NagramiXMessageSelectionColumn.contains(inside, leftInset: 0, topInset: 60, bottomInset: 50, height: 800), "checkbox column accepts one finger")
        for point in [CGPoint(x: 45, y: 100), CGPoint(x: -1, y: 100), CGPoint(x: 20, y: 59), CGPoint(x: 20, y: 751), CGPoint(x: CGFloat.nan, y: 100)] {
            expect(!NagramiXMessageSelectionColumn.contains(point, leftInset: 0, topInset: 60, bottomInset: 50, height: 800), "outside checkbox column scrolls normally")
        }
        expect(NagramiXMessageSelectionColumn.contains(CGPoint(x: 66, y: 60), leftInset: 22, topInset: 60, bottomInset: 50, height: 800), "landscape safe inset and boundary")
        checkGesture()
        checkHistory()
        print("single-touch message selection: \(checks) production checks passed")
    }
    static func checkGesture() {
        let event = UIEvent(), touch = UITouch(CGPoint(x: 20, y: 100))
        let r = NagramiXMessageDragSelectionRecognizer(target: nil, action: nil)
        expect(r.minimumNumberOfTouches == 1 && r.maximumNumberOfTouches == 1, "single touch only; native two-finger separate")
        expect(r.allowedTouchTypes == [NSNumber(value: 0)], "direct touches only")
        r.shouldBeginAt = { $0.x < 44 }
        r.touchesBegan([touch], with: event)
        expect(r.initialPoint == touch.point && r.state == .possible, "anchor captured on touch down")
        touch.point.y += 2; r.touchesMoved([touch], with: event)
        expect(r.forwardedMoves == 0, "tap jitter leaves checkbox tap available")
        touch.point.y += 12; r.touchesMoved([touch], with: event)
        expect(r.forwardedMoves == 1, "vertical drag reaches native pan")
        r.touchesBegan([UITouch(CGPoint(x: 21, y: 100))], with: event)
        expect(r.state == .failed && r.initialPoint == CGPoint(x: 20, y: 100), "second finger does not move anchor")
        r.reset(); touch.point = CGPoint(x: 20, y: 100); r.touchesBegan([touch], with: event)
        touch.point.x = 40; touch.point.y += 2; r.touchesMoved([touch], with: event)
        expect(r.state == .failed, "horizontal gesture releases pan arbitration")
        r.reset(); touch.point = CGPoint(x: 100, y: 100); r.touchesBegan([touch], with: event)
        expect(r.state == .failed, "outside column fails immediately")
        r.reset(); r.shouldBeginAt = { _ in false }; touch.point.x = 20; r.touchesBegan([touch], with: event)
        expect(r.state == .failed, "selection mode required at touch down")
    }
    static func checkHistory() {
        let h = HistoryHarness()
        let nativeScroll = UIPanGestureRecognizer(target: nil, action: nil)
        let twoFinger = UIPanGestureRecognizer(target: nil, action: nil); twoFinger.minimumNumberOfTouches = 2
        h.listView.scrollGestureHostView.addGestureRecognizer(nativeScroll)
        h.listView.scrollGestureHostView.addGestureRecognizer(twoFinger)
        h.listView.scrollGestureHostView.offset = CGPoint(x: 0, y: 25)
        h.nagramiXBindSingleSelection()
        guard let r = h.listView.scrollGestureHostView.gestureRecognizers?.last as? NagramiXMessageDragSelectionRecognizer else {
            expect(false, "both backends use actual scroll pan host"); return
        }
        expect(nativeScroll.dependencies.count == 1 && nativeScroll.dependencies[0] === r && twoFinger.dependencies.isEmpty, "scroll defers only to eligible one-finger pan")
        expect(r.shouldBeginAt?(CGPoint(x: 20, y: 40)) == true, "host coordinates convert into list coordinates")
        h.controllerInteraction.selectionState = nil
        expect(r.shouldBeginAt?(CGPoint(x: 20, y: 100)) == false, "outside selection mode normal scroll")
        h.controllerInteraction.selectionState = SelectionState(selectedIds: [0, 90])
        let messages = (0...8).map { Message(id: $0, index: $0) }
        let service = Message(id: 99, index: 4, media: [TelegramMediaAction()])
        h.historyView = ChatHistoryView(filteredEntries: messages.map { .MessageEntry($0, 0, false, nil, 0, 0) } + [.MessageEntry(service, 0, false, nil, 0, 0), .UnreadEntry])
        expect(!h.nagramiXDragRows().flatMap { $0.1 }.contains(99), "service rows cannot enter selection")
        h.listView.nodes = messages.map { ChatMessageItemView([$0], frame: CGRect(x: 0, y: 90 + $0.index * 65, width: 390, height: 60)) }
        expect(h.nagramiXDragMessages(at: CGPoint(x: 20, y: 152))?.first?.id == 0, "gaps resolve nearest selectable row")
        r.touchesBegan([UITouch(CGPoint(x: 20, y: 75))], with: UIEvent())
        r.state = .began; r.point = CGPoint(x: 20, y: 86); h.nagramiXSingleSelectionPan(r)
        expect(h.controllerInteraction.selectionState?.selectedIds == [0, 90], "checked anchor never toggles off")
        r.state = .changed; r.point.y = 360; h.nagramiXSingleSelectionPan(r)
        expect(h.controllerInteraction.selectionState?.selectedIds == [0, 1, 2, 3, 4, 90], "actual history fast drag selects full interval")
        r.point.y = 170; h.nagramiXSingleSelectionPan(r)
        expect(h.controllerInteraction.selectionState?.selectedIds == [0, 1, 90], "actual history reverses newly added rows")
        r.point.y = 710; h.nagramiXSingleSelectionPan(r)
        guard let timer = h.selectionScrollActivationTimer else { expect(false, "edge autoscroll activation"); return }
        expect(timer.active && timer.timeout == 0.45, "native edge delay retained")
        r.state = .ended; h.nagramiXSingleSelectionPan(r)
        expect(!timer.active, "release cancels edge activation")
        expect(h.selectionScrollDisplayLink == nil && h.selectionLastLocation == nil && h.selectionPanState == nil, "release clears only gesture machinery")
        let retained = h.controllerInteraction.selectionState!.selectedIds
        r.reset(); r.touchesBegan([UITouch(CGPoint(x: 20, y: 75))], with: UIEvent())
        r.state = .began; r.point.y = 710; h.nagramiXSingleSelectionPan(r)
        h.selectionScrollActivationTimer?.fire()
        guard let display = h.selectionScrollDisplayLink else { expect(false, "native display link starts"); return }
        h.listView.onScroll = {
            h.listView.nodes = [ChatMessageItemView([Message(id: 12, index: 12)], frame: CGRect(x: 0, y: 700, width: 390, height: 60))]
            h.historyView = ChatHistoryView(filteredEntries: (9...12).map { .MessageEntry(Message(id: $0, index: $0), 0, false, nil, 0, 0) })
        }
        display.update()
        expect(h.listView.scrolls.count == 1 && h.listView.scrolls[0].0 == .down && h.listView.scrolls[0].1 <= 15, "existing edge autoscroll advances history")
        expect(h.controllerInteraction.selectionState!.selectedIds.isSuperset(of: retained.union([9, 10, 11, 12])), "stationary finger selects newly loaded rows")
        h.listView.onScroll = nil
        h.controllerInteraction.selectionState = nil; display.update(); display.update()
        expect(h.nagramiXSingleSelection == nil && h.selectionScrollDisplayLink == nil && h.selectionScrollActivationTimer == nil, "leaving selection mode stops scrolling")
        h.controllerInteraction.selectionState = SelectionState(selectedIds: [0])
        r.reset(); r.touchesBegan([UITouch(CGPoint(x: 20, y: 700))], with: UIEvent()); r.state = .began; h.nagramiXSingleSelectionPan(r)
        h.isSelectionGestureEnabled = false
        h.handlePanSelection(location: CGPoint(x: 20, y: 749))
        expect(h.nagramiXSingleSelection == nil && h.selectionScrollActivationTimer == nil, "disabled gesture cannot rearm edge scrolling")
        h.isSelectionGestureEnabled = true
        h.historyView = ChatHistoryView(filteredEntries: [.MessageGroupEntry(42, [(Message(id: 20, index: 20), false, 0, 0, nil), (Message(id: 21, index: 21), false, 0, 0, nil)], 0)])
        let groups = h.nagramiXDragRows()
        expect(groups.count == 1 && Set(groups[0].1) == [20, 21] && groups[0].0 == 20, "album represented as one atomic row")
        let probe = LifetimeProbe()
        do { let temporary = HistoryHarness(); probe.value = temporary; temporary.nagramiXBindSingleSelection() }
        expect(probe.value == nil, "binding captures history weakly")
    }
    final class LifetimeProbe { weak var value: HistoryHarness? }
