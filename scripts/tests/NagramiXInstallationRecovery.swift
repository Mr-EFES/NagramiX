@main struct InstallationRecovery {
    static func main() async throws {
        let root = FileManager.default.temporaryDirectory.appendingPathComponent(UUID().uuidString)
        defer { try? FileManager.default.removeItem(at: root) }
        try FileManager.default.createDirectory(at: root, withIntermediateDirectories: true)
        let config = URLSessionConfiguration.ephemeral
        config.protocolClasses = [Stub.self]
        let session = URLSession(configuration: config)
        defer { session.invalidateAndCancel() }
        let endpoint = URL(string: "https://local.invalid/v1/installation")!
        func observe(_ authorized: Bool) async {
            await NagramiXInstallationMetrics(endpoint: endpoint, directory: root, session: session).observe(isAuthorized: authorized)
        }
        let file = root.appendingPathComponent("installation.json"), backup = root.appendingPathComponent("installation-backup.json")
        let id = UUID()
        let legacy = try JSONSerialization.data(withJSONObject: ["id": id.uuidString, "observed": 3, "acknowledged": "opened"])
        try legacy.write(to: file)
        await observe(true)
        precondition(Stub.received().count == 1 && Stub.received()[0].0 == id && Stub.received()[0].1 == "authorized")
        let valid = try Data(contentsOf: backup)
        try Data("{".utf8).write(to: file)
        await observe(false)
        let repaired = try Data(contentsOf: file)
        let dictionary = try JSONSerialization.jsonObject(with: repaired) as! [String: String]
        precondition(dictionary["id"] == id.uuidString && dictionary["acknowledged"] == "authorized")
        try FileManager.default.removeItem(at: file)
        await observe(true)
        try Data("broken".utf8).write(to: backup)
        await observe(false)
        precondition(Stub.received().count == 1)
        let restored = try JSONDecoder().decode([String: String].self, from: Data(contentsOf: backup))
        precondition(restored["id"] == id.uuidString && restored["observed"] == "authorized")

        // Verified progress in the surviving copy wins over an interrupted older write.
        let older = try JSONEncoder().encode(["id": id.uuidString, "observed": "opened", "acknowledged": "opened"])
        try older.write(to: file)
        try valid.write(to: backup)
        await observe(false)
        precondition(Stub.received().count == 1)
        let merged = try JSONDecoder().decode([String: String].self, from: Data(contentsOf: file))
        precondition(merged["observed"] == "authorized" && merged["acknowledged"] == "authorized")

        try FileManager.default.removeItem(at: backup)
        let cut = "{\"id\":\"" + id.uuidString + "\",\"observed\":\"auth"
        try Data(cut.utf8).write(to: file)
        await observe(true)
        precondition(Stub.received().count == 2 && Stub.received().last!.0 == id && Stub.received().last!.1 == "authorized")

        try Data("broken".utf8).write(to: file)
        try FileManager.default.removeItem(at: backup)
        await observe(true)
        precondition(Stub.received().count == 2)
        print("PASS legacy UUID, corrupt state, missing primary, replica repair, monotonic acknowledgement and no duplicate installation")
    }
}
