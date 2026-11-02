import Foundation

// The tested mapping, row counts and provider lookups are extracted verbatim
// from the production controller; UIKit is not involved in this boundary suite.
struct PremiumSettingsScreen {
    enum Page { case settings, languages, preferred, credential(NagramiXTranslationProvider) }
    var page: Page = .settings
    var isPremium: Bool?
    let languages = ["ru", "en"]
    // PRODUCTION_METHODS
}

@main
struct NagramiXTranslationPremiumVisibilityTests {
    static func check(_ condition: @autoclosure () -> Bool, _ reason: String) {
        if !condition() { fatalError(reason) }
    }
    static func main() throws {
        let key = "nagramix.translation.configuration.v1"
        let previous = UserDefaults.standard.data(forKey: key)
        defer {
            if let previous { UserDefaults.standard.set(previous, forKey: key) }
            else { UserDefaults.standard.removeObject(forKey: key) }
        }
        for selected in NagramiXTranslationProvider.allCases {
            var config = NagramiXTranslationConfiguration()
            config.provider = selected
            UserDefaults.standard.set(try JSONEncoder().encode(config), forKey: key)
            let states: [Bool?] = [nil, false, true]
            for premium in states {
                let screen = PremiumSettingsScreen(isPremium: premium)
                let hasPremium = premium == true
                check(screen.numberOfSections() == (hasPremium ? 4 : 3), "no empty Telegram group")
                check(screen.header(section: 0) == "ПЕРЕВОД", "main section stays first")
                check(screen.rows(section: 0) == 5, "main settings preserved")
                if hasPremium {
                    check(screen.header(section: 1) == "TELEGRAM", "Telegram above dictionaries")
                    check(screen.rows(section: 1) == 1, "one Telegram option")
                    check(screen.providerRow(section: 1, row: 0)?.0 == .telegram, "Telegram row selection")
                }
                let dictionaries = hasPremium ? 2 : 1
                check(screen.header(section: dictionaries) == "СЛОВАРИ", "dictionary header follows visibility")
                check(screen.rows(section: dictionaries) == 3, "all dictionaries remain")
                for (row, provider) in [NagramiXTranslationProvider.apple, .google, .yandex].enumerated() {
                    check(screen.providerRow(section: dictionaries, row: row)?.0 == provider, "dictionary row selects matching provider")
                    check(screen.providerRow(section: dictionaries, row: row)?.1 == false, "no dictionary child settings")
                }
                let ai = dictionaries + 1
                check(screen.header(section: ai) == "ИСКУССТВЕННЫЙ ИНТЕЛЛЕКТ", "AI header preserved")
                check(screen.rows(section: ai) == (selected.requiresAPIKey ? 4 : 3), "conditional neural settings row")
                var row = 0
                for provider in [NagramiXTranslationProvider.gemini, .chatgpt, .deepseek] {
                    check(screen.providerRow(section: ai, row: row)?.0 == provider, "neural provider row")
                    check(screen.providerRow(section: ai, row: row)?.1 == false, "neural provider action")
                    row += 1
                    if selected == provider {
                        check(screen.providerRow(section: ai, row: row)?.0 == provider, "selected neural child provider")
                        check(screen.providerRow(section: ai, row: row)?.1 == true, "selected neural child opens settings")
                        row += 1
                    }
                }
            }
        }
        var dynamic = PremiumSettingsScreen(isPremium: nil)
        check(dynamic.numberOfSections() == 3, "unknown membership hides")
        dynamic.isPremium = true
        check(dynamic.numberOfSections() == 4 && dynamic.header(section: 1) == "TELEGRAM", "membership received")
        dynamic.isPremium = false
        check(dynamic.numberOfSections() == 3 && dynamic.header(section: 1) == "СЛОВАРИ", "expiry hides without shifting dictionary actions")
        print("PASS: production section/provider mapping across seven selections and three Premium states")
    }
}
