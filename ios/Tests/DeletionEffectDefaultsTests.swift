let suiteName = "NagramiX.DeletionEffectTests." + UUID().uuidString
let first = UserDefaults(suiteName: suiteName)!
precondition(NagramiXDeletionEffectSettings.isEnabled(in: first))
NagramiXDeletionEffectSettings.setEnabled(false, in: first)
let reopened = UserDefaults(suiteName: suiteName)!
precondition(!NagramiXDeletionEffectSettings.isEnabled(in: reopened))
NagramiXDeletionEffectSettings.setEnabled(true, in: reopened)
precondition(NagramiXDeletionEffectSettings.isEnabled(in: UserDefaults(suiteName: suiteName)!))
NagramiXDeletionEffectSettings.setEnabled(false, in: reopened)
reopened.set(true, forKey: "unrelated")
precondition(!NagramiXDeletionEffectSettings.isEnabled(in: UserDefaults(suiteName: suiteName)!))
first.removePersistentDomain(forName: suiteName)
