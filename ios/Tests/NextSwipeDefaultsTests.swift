let suiteName = "NagramiX.NextSwipeTests." + UUID().uuidString
let first = UserDefaults(suiteName: suiteName)!
precondition(NagramiXNextSwipeSettings.isDisabled(in: first))
NagramiXNextSwipeSettings.setDisabled(false, in: first)
let reopened = UserDefaults(suiteName: suiteName)!
precondition(!NagramiXNextSwipeSettings.isDisabled(in: reopened))
NagramiXNextSwipeSettings.setDisabled(true, in: reopened)
precondition(NagramiXNextSwipeSettings.isDisabled(in: UserDefaults(suiteName: suiteName)!))
NagramiXNextSwipeSettings.setDisabled(false, in: reopened)
reopened.set(true, forKey: "unrelated")
precondition(!NagramiXNextSwipeSettings.isDisabled(in: UserDefaults(suiteName: suiteName)!))

first.removePersistentDomain(forName: suiteName)
