// Compile with the production NagramiXSinglePiPRestoration declaration.
func testPiPRestorationOrdering() {
    var restoreThenStop = NagramiXSinglePiPRestoration()
    precondition(restoreThenStop.begin())
    precondition(!restoreThenStop.stopped())
    precondition(restoreThenStop.isRestoring && restoreThenStop.didStop)
    precondition(restoreThenStop.restorationFinished())
    precondition(!restoreThenStop.restorationFinished())
    precondition(!restoreThenStop.stopped())

    var restoreThenFinish = NagramiXSinglePiPRestoration()
    precondition(restoreThenFinish.begin())
    precondition(!restoreThenFinish.begin())
    precondition(!restoreThenFinish.restorationFinished())
    precondition(!restoreThenFinish.begin())
    precondition(restoreThenFinish.stopped())
    precondition(!restoreThenFinish.stopped())

    var closeWithoutRestore = NagramiXSinglePiPRestoration()
    precondition(closeWithoutRestore.stopped())
    precondition(!closeWithoutRestore.begin())

    var timedOut = NagramiXSinglePiPRestoration()
    precondition(timedOut.begin())
    precondition(!timedOut.restorationFinished())
    precondition(timedOut.stopped())
    precondition(!timedOut.restorationFinished())
}
testPiPRestorationOrdering()
print("Single-player PiP restoration ordering: OK")
