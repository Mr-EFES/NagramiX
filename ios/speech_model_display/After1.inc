import Foundation
import CryptoKit

enum NagramiXWhisperActivationPolicy {
    static func permits(_ configuration: NagramiXTranscriptionConfiguration, revision: String) -> Bool {
        return configuration.enabled && configuration.provider == .whisper && configuration.revision == revision
    }
}

public final class NagramiXWhisperModels: NSObject, URLSessionDownloadDelegate, @unchecked Sendable {
    public static let shared = NagramiXWhisperModels()
    public static let changed = Notification.Name("NagramiXWhisperModelsChanged")
    private let lock = NSLock()
    private var downloads: [Int: NagramiXWhisperModel] = [:]
    private var tasks: [NagramiXWhisperModel: URLSessionDownloadTask] = [:]
    private var progress: [NagramiXWhisperModel: Int] = [:]
    private var errors: [NagramiXWhisperModel: String] = [:]
    private var leases: [NagramiXWhisperModel: Int] = [:]
    private var activations: [Int: String] = [:]
    private lazy var session: URLSession = {
        let config = URLSessionConfiguration.ephemeral
        config.urlCache = nil; config.httpCookieStorage = nil
        config.timeoutIntervalForRequest = 60; config.timeoutIntervalForResource = 3600
        let queue = OperationQueue(); queue.maxConcurrentOperationCount = 1
        return URLSession(configuration: config, delegate: self, delegateQueue: queue)
    }()
    private var directory: URL {
        FileManager.default.urls(for: .applicationSupportDirectory, in: .userDomainMask)[0].appendingPathComponent("NagramiXWhisper", isDirectory: true)
    }
    private func url(_ model: NagramiXWhisperModel) -> URL { self.directory.appendingPathComponent(model.fileName) }
    public func installed(_ model: NagramiXWhisperModel) -> Bool {
        let size = (try? FileManager.default.attributesOfItem(atPath: self.url(model).path)[.size] as? NSNumber)?.int64Value
        return size == model.size
    }
    public func isDownloading(_ model: NagramiXWhisperModel) -> Bool {
        self.lock.lock(); defer { self.lock.unlock() }
        return self.tasks[model] != nil
    }
    public func downloadProgress(_ model: NagramiXWhisperModel) -> Int? { self.lock.lock(); defer { self.lock.unlock() }; return self.progress[model] }
    public func status(_ model: NagramiXWhisperModel) -> String {
        self.lock.lock(); defer { self.lock.unlock() }
        if let value = self.progress[model] { return "Загрузка · \(value)%" }
        if let error = self.errors[model] { return error }
        return self.installed(model) ? "Загружена" : "\(model.size / 1_000_000) МБ"
    }
    public func downloadOrCancel(_ model: NagramiXWhisperModel, activateWhenInstalled: Bool = false) {
        let revision = activateWhenInstalled ? NagramiXTranscriptionSettings.current.revision : nil
        self.lock.lock()
        if let task = self.tasks[model] { self.lock.unlock(); task.cancel(); return }
        self.errors[model] = nil; self.progress[model] = 0
        let request = URLRequest(url: model.url)
        // Network choice is confirmed in the UI for each new download.
        let task = self.session.downloadTask(with: request)
        self.downloads[task.taskIdentifier] = model; self.tasks[model] = task
        if let revision { self.activations[task.taskIdentifier] = revision }
        self.lock.unlock(); self.notify(); task.resume()
    }
    public func remove(_ model: NagramiXWhisperModel) -> Bool {
        self.lock.lock(); defer { self.lock.unlock() }
        guard self.tasks[model] == nil, (self.leases[model] ?? 0) == 0 else { return false }
        do { if self.installed(model) { try FileManager.default.removeItem(at: self.url(model)) }; self.errors[model] = nil; self.notify(); return true }
        catch { return false }
    }
    func withLease<T>(_ model: NagramiXWhisperModel, _ body: (URL) throws -> T) throws -> T {
        self.lock.lock()
        guard self.installed(model) else { self.lock.unlock(); throw NagramiXTranscriptionFailure.missingModel }
        self.leases[model, default: 0] += 1; self.lock.unlock()
        defer { self.lock.lock(); self.leases[model, default: 1] -= 1; self.lock.unlock() }
        return try body(self.url(model))
    }
    private func notify() { DispatchQueue.main.async { NotificationCenter.default.post(name: Self.changed, object: nil) } }
    public func urlSession(_ session: URLSession, downloadTask: URLSessionDownloadTask, didWriteData bytesWritten: Int64, totalBytesWritten: Int64, totalBytesExpectedToWrite: Int64) {
        self.lock.lock()
        guard let model = self.downloads[downloadTask.taskIdentifier] else { self.lock.unlock(); return }
        if totalBytesWritten > model.size || (totalBytesExpectedToWrite > 0 && totalBytesExpectedToWrite != model.size) { self.lock.unlock(); downloadTask.cancel(); return }
        let percent = Int(min(99, totalBytesWritten * 100 / model.size))
        let changed = self.progress[model] != percent; self.progress[model] = percent; self.lock.unlock()
        if changed { self.notify() }
    }
    public func urlSession(_ session: URLSession, downloadTask: URLSessionDownloadTask, didFinishDownloadingTo location: URL) {
        self.lock.lock(); let model = self.downloads[downloadTask.taskIdentifier]; let revision = self.activations[downloadTask.taskIdentifier]; self.lock.unlock()
        guard let model else { return }
        do {
            guard (downloadTask.response as? HTTPURLResponse)?.statusCode == 200,
                  (try FileManager.default.attributesOfItem(atPath: location.path)[.size] as? NSNumber)?.int64Value == model.size else { throw NagramiXTranscriptionFailure.storage }
            let file = try FileHandle(forReadingFrom: location); defer { try? file.close() }
            var hash = SHA256()
            while let data = try file.read(upToCount: 1_048_576), !data.isEmpty { hash.update(data: data) }
            guard hash.finalize().map({ String(format: "%02x", $0) }).joined() == model.sha256 else { throw NagramiXTranscriptionFailure.storage }
            self.lock.lock(); defer { self.lock.unlock() }
            guard (self.leases[model] ?? 0) == 0, downloadTask.state != .canceling else { throw NagramiXTranscriptionFailure.cancelled }
            try FileManager.default.createDirectory(at: self.directory, withIntermediateDirectories: true)
            var directory = self.directory; var values = URLResourceValues(); values.isExcludedFromBackup = true; try directory.setResourceValues(values)
            let target = self.url(model)
            if FileManager.default.fileExists(atPath: target.path) { _ = try FileManager.default.replaceItemAt(target, withItemAt: location) }
            else { try FileManager.default.moveItem(at: location, to: target) }
            try FileManager.default.setAttributes([.protectionKey: FileProtectionType.completeUntilFirstUserAuthentication], ofItemAtPath: target.path)
            if let revision {
                DispatchQueue.main.async {
                    let current = NagramiXTranscriptionSettings.current
                    guard NagramiXWhisperActivationPolicy.permits(current, revision:revision) else { return }
                    NagramiXTranscriptionSettings.update { value in
                        guard NagramiXWhisperActivationPolicy.permits(value, revision:revision) else { return }
                        value.whisper = model; if model.englishOnly { value.language = "en" }
                    }
                }
            }
        } catch { self.lock.lock(); self.errors[model] = "Загрузка не завершена. Повторите попытку."; self.lock.unlock() }
    }
    public func urlSession(_ session: URLSession, task: URLSessionTask, didCompleteWithError error: Error?) {
        self.lock.lock()
        self.activations.removeValue(forKey: task.taskIdentifier)
        if let model = self.downloads.removeValue(forKey: task.taskIdentifier) {
            self.tasks[model] = nil; self.progress[model] = nil
            if let error, (error as NSError).code != NSURLErrorCancelled { self.errors[model] = "Не удалось загрузить модель. Проверьте сеть и свободное место." }
        }
        self.lock.unlock(); self.notify()
    }
    public func urlSession(_ session: URLSession, task: URLSessionTask, willPerformHTTPRedirection response: HTTPURLResponse, newRequest request: URLRequest, completionHandler: @escaping (URLRequest?) -> Void) {
        let host = request.url?.host?.lowercased() ?? ""
        let allowed = request.url?.scheme == "https" && (host == "huggingface.co" || host.hasSuffix(".huggingface.co") || host.hasSuffix(".hf.co") || host.hasSuffix(".xethub.hf.co"))
        completionHandler(allowed ? request : nil)
    }
}
