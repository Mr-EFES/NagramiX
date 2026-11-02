// Compile together with the production NagramiXPiPStopState.
func testPiPStopEventOrders() {
    var playing = NagramiXPiPStopState()
    playing.begin(playing: true)
    // AVPlayer's automatic pause during the system animation must not become
    // the destination player's playback intent, even if WillStop repeats.
    playing.begin(playing: false)
    precondition(playing.isStopping && playing.playing == true)

    var paused = NagramiXPiPStopState()
    paused.begin(playing: false)
    paused.begin(playing: true)
    precondition(paused.playing == false)

    var restoreBeforeStop = NagramiXPiPStopState()
    restoreBeforeStop.capture(playing: true)
    precondition(!restoreBeforeStop.isStopping)
    restoreBeforeStop.begin(playing: false)
    precondition(restoreBeforeStop.isStopping && restoreBeforeStop.playing == true)

    var stopBeforeRestore = NagramiXPiPStopState()
    stopBeforeRestore.begin(playing: true)
    stopBeforeRestore.capture(playing: false)
    precondition(stopBeforeRestore.playing == true)

    var pausedRestore = NagramiXPiPStopState()
    pausedRestore.capture(playing: false)
    pausedRestore.begin(playing: true)
    precondition(pausedRestore.playing == false)
}
testPiPStopEventOrders()
print("PiP stop event orders: OK")
