import Foundation
import CryptoKit
import ZipArchive

struct NagramiXVoskModel: Codable {
    let name: String
    let lang: String
    let type: String
    let size: Int64
    let md5: String
    let url: String
    let version: String
    let license: String
    var title: String { self.type == "small" ? "Компактная" : "Точная" }
    static let all: [NagramiXVoskModel] = {
        // Pinned official catalog; only explicitly Apache-2.0 models are included.
        let data = Data(catalog.utf8)
        return (try? JSONDecoder().decode([NagramiXVoskModel].self, from: data)) ?? []
    }()
    private static let catalog = #"[{"lang":"ar-tn","lang_text":"Arabic Tunisian","md5":"82352c37047a618fa8ceaea5039f0767","name":"vosk-model-ar-tn-0.1-linto","obsolete":"false","size":543344119,"size_text":"518.2MiB","type":"big","url":"https://alphacephei.com/vosk/models/vosk-model-ar-tn-0.1-linto.zip","version":"0.1-linto","license":"Apache 2.0"},{"lang":"cn","lang_text":"Chinese","md5":"c050f6849398ceecfa723cca69b8c67d","name":"vosk-model-cn-0.22","obsolete":"false","size":1358736686,"size_text":"1.3GiB","type":"big","url":"https://alphacephei.com/vosk/models/vosk-model-cn-0.22.zip","version":"0.22","license":"Apache 2.0"},{"lang":"de","lang_text":"German","md5":"23298ddeb602739016956144ac4c74de","name":"vosk-model-de-0.21","obsolete":"false","size":2031717803,"size_text":"1.9GiB","type":"big","url":"https://alphacephei.com/vosk/models/vosk-model-de-0.21.zip","version":"0.21","license":"Apache 2.0"},{"lang":"el-gr","lang_text":"Greek","md5":"3a00ab31d11a15d1d5ace08b47c82bdf","name":"vosk-model-el-gr-0.7","obsolete":"false","size":1115076503,"size_text":"1.0GiB","type":"big","url":"https://alphacephei.com/vosk/models/vosk-model-el-gr-0.7.zip","version":"0.7","license":"Apache 2.0"},{"lang":"en-in","lang_text":"Indian English","md5":"0c203ec203f471fc3482aba52853ee1d","name":"vosk-model-en-in-0.5","obsolete":"false","size":971186187,"size_text":"926.2MiB","type":"big","url":"https://alphacephei.com/vosk/models/vosk-model-en-in-0.5.zip","version":"0.5","license":"Apache 2.0"},{"lang":"en-us","lang_text":"US English","md5":"228741ed058893e403dce60bdd659f42","name":"vosk-model-en-us-0.22","obsolete":"false","size":1913365522,"size_text":"1.8GiB","type":"big","url":"https://alphacephei.com/vosk/models/vosk-model-en-us-0.22.zip","version":"0.22","license":"Apache 2.0"},{"lang":"en-us","lang_text":"US English","md5":"2df36985f8ed8eb7b78476cadcdab48f","name":"vosk-model-en-us-0.22-lgraph","obsolete":"false","size":130557655,"size_text":"124.5MiB","type":"big-lgraph","url":"https://alphacephei.com/vosk/models/vosk-model-en-us-0.22-lgraph.zip","version":"0.22-lgraph","license":"Apache 2.0"},{"lang":"en-us","lang_text":"US English","md5":"db1202c15b40ea4b1ec27b85a90dffbe","name":"vosk-model-en-us-0.42-gigaspeech","obsolete":"false","size":2423807363,"size_text":"2.3GiB","type":"big","url":"https://alphacephei.com/vosk/models/vosk-model-en-us-0.42-gigaspeech.zip","version":"0.42-gigaspeech","license":"Apache 2.0"},{"lang":"es","lang_text":"Spanish","md5":"83f83e045a4537c53ed5ed42f959bf6d","name":"vosk-model-es-0.42","obsolete":"false","size":1484681703,"size_text":"1.4GiB","type":"big","url":"https://alphacephei.com/vosk/models/vosk-model-es-0.42.zip","version":"0.42","license":"Apache 2.0"},{"lang":"fa","lang_text":"Farsi","md5":"c47c8e497e35e5e3a27cb71c4f0af275","name":"vosk-model-fa-0.42","obsolete":"false","size":1667089770,"size_text":"1.6GiB","type":"big","url":"https://alphacephei.com/vosk/models/vosk-model-fa-0.42.zip","version":"0.42","license":"Apache 2.0"},{"lang":"fr","lang_text":"French","md5":"12662b25b4d35059ec05e3a75a27841e","name":"vosk-model-fr-0.22","obsolete":"false","size":1523026348,"size_text":"1.4GiB","type":"big","url":"https://alphacephei.com/vosk/models/vosk-model-fr-0.22.zip","version":"0.22","license":"Apache 2.0"},{"lang":"gu","lang_text":"Gujarati","md5":"b0ca9c90014cbf85a489019894ddbbe2","name":"vosk-model-gu-0.42","obsolete":"false","size":750805731,"size_text":"716.0MiB","type":"big","url":"https://alphacephei.com/vosk/models/vosk-model-gu-0.42.zip","version":"0.42","license":"Apache 2.0"},{"lang":"hi","lang_text":"Hindi","md5":"247e9d0fb3ee0a6c520162554d902e2a","name":"vosk-model-hi-0.22","obsolete":"false","size":1561909274,"size_text":"1.5GiB","type":"big","url":"https://alphacephei.com/vosk/models/vosk-model-hi-0.22.zip","version":"0.22","license":"Apache 2.0"},{"lang":"it","lang_text":"Italian","md5":"973cf0adc17ea0acd042d079bba67a94","name":"vosk-model-it-0.22","obsolete":"false","size":1306765292,"size_text":"1.2GiB","type":"big","url":"https://alphacephei.com/vosk/models/vosk-model-it-0.22.zip","version":"0.22","license":"Apache 2.0"},{"lang":"ja","lang_text":"Japanese","md5":"e7ab21ff213aff2edf1f04724487846c","name":"vosk-model-ja-0.22","obsolete":"false","size":1045975323,"size_text":"997.5MiB","type":"big","url":"https://alphacephei.com/vosk/models/vosk-model-ja-0.22.zip","version":"0.22","license":"Apache 2.0"},{"lang":"ka","lang_text":"Georgian","md5":"0808fea0c88d8f3387ef017b2793dce8","name":"vosk-model-ka-0.42","obsolete":"false","size":733004425,"size_text":"699.0MiB","type":"big","url":"https://alphacephei.com/vosk/models/vosk-model-ka-0.42.zip","version":"0.42","license":"Apache 2.0"},{"lang":"ky","lang_text":"Kyrgyz","md5":"9a7c9151a0abc16f1aa3e1118cf28e91","name":"vosk-model-ky-0.42","obsolete":"false","size":1206525064,"size_text":"1.1GiB","type":"big","url":"https://alphacephei.com/vosk/models/vosk-model-ky-0.42.zip","version":"0.42","license":"Apache 2.0"},{"lang":"kz","lang_text":"Kazakh","md5":"7ced5a09d2ae7190d037b6d8c494ef3d","name":"vosk-model-kz-0.42","obsolete":"false","size":1402452122,"size_text":"1.3GiB","type":"big","url":"https://alphacephei.com/vosk/models/vosk-model-kz-0.42.zip","version":"0.42","license":"Apache 2.0"},{"lang":"ru","lang_text":"Russian","md5":"ae356c0fc8879deed1982d879f40880a","name":"vosk-model-ru-0.42","obsolete":"false","size":1937602113,"size_text":"1.8GiB","type":"big","url":"https://alphacephei.com/vosk/models/vosk-model-ru-0.42.zip","version":"0.42","license":"Apache 2.0"},{"lang":"ar-tn","lang_text":"Arabic Tunisian","md5":"67bbe16beaa17e6cf14f8c295ee5ddd1","name":"vosk-model-small-ar-tn-0.1-linto","obsolete":"false","size":165703754,"size_text":"158.0MiB","type":"small","url":"https://alphacephei.com/vosk/models/vosk-model-small-ar-tn-0.1-linto.zip","version":"0.1-linto","license":"Apache 2.0"},{"lang":"ca","lang_text":"Catalan","md5":"5dc7901815fef3dc8b784b31f309385c","name":"vosk-model-small-ca-0.4","obsolete":"false","size":43405881,"size_text":"41.4MiB","type":"small","url":"https://alphacephei.com/vosk/models/vosk-model-small-ca-0.4.zip","version":"0.4","license":"Apache 2.0"},{"lang":"cn","lang_text":"Chinese","md5":"d1a8e82933dcc7632667c036b0bb3dbb","name":"vosk-model-small-cn-0.22","obsolete":"false","size":43898754,"size_text":"41.9MiB","type":"small","url":"https://alphacephei.com/vosk/models/vosk-model-small-cn-0.22.zip","version":"0.22","license":"Apache 2.0"},{"lang":"de","lang_text":"German","md5":"4f21f92c0897b48287ef8839420608eb","name":"vosk-model-small-de-0.15","obsolete":"false","size":46499967,"size_text":"44.3MiB","type":"small","url":"https://alphacephei.com/vosk/models/vosk-model-small-de-0.15.zip","version":"0.15","license":"Apache 2.0"},{"lang":"en-in","lang_text":"Indian English","md5":"62fd085f33c8c5fc01a235030e2a1fe3","name":"vosk-model-small-en-in-0.4","obsolete":"false","size":37573330,"size_text":"35.8MiB","type":"small","url":"https://alphacephei.com/vosk/models/vosk-model-small-en-in-0.4.zip","version":"0.4","license":"Apache 2.0"},{"lang":"en-us","lang_text":"US English","md5":"09ab50ccd62b674cbaa231b825f9c1cb","name":"vosk-model-small-en-us-0.15","obsolete":"false","size":41205931,"size_text":"39.3MiB","type":"small","url":"https://alphacephei.com/vosk/models/vosk-model-small-en-us-0.15.zip","version":"0.15","license":"Apache 2.0"},{"lang":"eo","lang_text":"Esperanto","md5":"3e9319ca789fa06fd3efa68d51c85d6b","name":"vosk-model-small-eo-0.42","obsolete":"false","size":43839401,"size_text":"41.8MiB","type":"small","url":"https://alphacephei.com/vosk/models/vosk-model-small-eo-0.42.zip","version":"0.42","license":"Apache 2.0"},{"lang":"es","lang_text":"Spanish","md5":"2d5c94f9859a84881a0ef744738ebd31","name":"vosk-model-small-es-0.42","obsolete":"false","size":39817833,"size_text":"38.0MiB","type":"small","url":"https://alphacephei.com/vosk/models/vosk-model-small-es-0.42.zip","version":"0.42","license":"Apache 2.0"},{"lang":"fa","lang_text":"Farsi","md5":"cc2b18af256ffab2c44055f6a02ecb3d","name":"vosk-model-small-fa-0.42","obsolete":"false","size":53431220,"size_text":"51.0MiB","type":"small","url":"https://alphacephei.com/vosk/models/vosk-model-small-fa-0.42.zip","version":"0.42","license":"Apache 2.0"},{"lang":"fr","lang_text":"French","md5":"8873b1234503f6edd55f54bfff31cf3e","name":"vosk-model-small-fr-0.22","obsolete":"false","size":42233323,"size_text":"40.3MiB","type":"small","url":"https://alphacephei.com/vosk/models/vosk-model-small-fr-0.22.zip","version":"0.22","license":"Apache 2.0"},{"lang":"gu","lang_text":"Gujarati","md5":"4595a6f0cc0c88fee6eec7d80496fc10","name":"vosk-model-small-gu-0.42","obsolete":"false","size":108054987,"size_text":"103.0MiB","type":"small","url":"https://alphacephei.com/vosk/models/vosk-model-small-gu-0.42.zip","version":"0.42","license":"Apache 2.0"},{"lang":"hi","lang_text":"Hindi","md5":"80f1265262c9a8a515f2707498e1b485","name":"vosk-model-small-hi-0.22","obsolete":"false","size":44458845,"size_text":"42.4MiB","type":"small","url":"https://alphacephei.com/vosk/models/vosk-model-small-hi-0.22.zip","version":"0.22","license":"Apache 2.0"},{"lang":"it","lang_text":"Italian","md5":"fbd8f9c72cbb8c3dfa3e4581bd3585f4","name":"vosk-model-small-it-0.22","obsolete":"false","size":49665141,"size_text":"47.4MiB","type":"small","url":"https://alphacephei.com/vosk/models/vosk-model-small-it-0.22.zip","version":"0.22","license":"Apache 2.0"},{"lang":"ja","lang_text":"Japanese","md5":"0e3163dd62dfb0d823353718ac3cbf79","name":"vosk-model-small-ja-0.22","obsolete":"false","size":49704573,"size_text":"47.4MiB","type":"small","url":"https://alphacephei.com/vosk/models/vosk-model-small-ja-0.22.zip","version":"0.22","license":"Apache 2.0"},{"lang":"ka","lang_text":"Georgian","md5":"7e95b6a69b60a5f1c45e29d1cd2ac353","name":"vosk-model-small-ka-0.42","obsolete":"false","size":45682310,"size_text":"43.6MiB","type":"small","url":"https://alphacephei.com/vosk/models/vosk-model-small-ka-0.42.zip","version":"0.42","license":"Apache 2.0"},{"lang":"ko","lang_text":"Korean","md5":"fa8029a173787a159e0e72fe6135f890","name":"vosk-model-small-ko-0.22","obsolete":"false","size":86914329,"size_text":"82.9MiB","type":"small","url":"https://alphacephei.com/vosk/models/vosk-model-small-ko-0.22.zip","version":"0.22","license":"Apache 2.0"},{"lang":"ky","lang_text":"Kyrgyz","md5":"541eb45589c2b6f8350905086a76f072","name":"vosk-model-small-ky-0.42","obsolete":"false","size":51041096,"size_text":"48.7MiB","type":"small","url":"https://alphacephei.com/vosk/models/vosk-model-small-ky-0.42.zip","version":"0.42","license":"Apache 2.0"},{"lang":"kz","lang_text":"Kazakh","md5":"1c7dc487ac5e0c24acfa7566c106ba2d","name":"vosk-model-small-kz-0.42","obsolete":"false","size":59697294,"size_text":"56.9MiB","type":"small","url":"https://alphacephei.com/vosk/models/vosk-model-small-kz-0.42.zip","version":"0.42","license":"Apache 2.0"},{"lang":"nl","lang_text":"Dutch","md5":"4582e1f20d6849099da08511f9797017","name":"vosk-model-small-nl-0.22","obsolete":"false","size":40441176,"size_text":"38.6MiB","type":"small","url":"https://alphacephei.com/vosk/models/vosk-model-small-nl-0.22.zip","version":"0.22","license":"Apache 2.0"},{"lang":"pl","lang_text":"Polish","md5":"91cbbd6231320467da672be31827b6ac","name":"vosk-model-small-pl-0.22","obsolete":"false","size":52979372,"size_text":"50.5MiB","type":"small","url":"https://alphacephei.com/vosk/models/vosk-model-small-pl-0.22.zip","version":"0.22","license":"Apache 2.0"},{"lang":"pt","lang_text":"Portuguese","md5":"458c69371c5a0b9ab6ee8fa417bf89da","name":"vosk-model-small-pt-0.3","obsolete":"false","size":32453112,"size_text":"30.9MiB","type":"small","url":"https://alphacephei.com/vosk/models/vosk-model-small-pt-0.3.zip","version":"0.3","license":"Apache 2.0"},{"lang":"ru","lang_text":"Russian","md5":"d1759dc83eb8fd87850129afbd9f4b7b","name":"vosk-model-small-ru-0.22","obsolete":"false","size":46236750,"size_text":"44.1MiB","type":"small","url":"https://alphacephei.com/vosk/models/vosk-model-small-ru-0.22.zip","version":"0.22","license":"Apache 2.0"},{"lang":"te","lang_text":"Telugu","md5":"ae3c093fd7dd883d462983b15900ca61","name":"vosk-model-small-te-0.42","obsolete":"false","size":60544249,"size_text":"57.7MiB","type":"small","url":"https://alphacephei.com/vosk/models/vosk-model-small-te-0.42.zip","version":"0.42","license":"Apache 2.0"},{"lang":"tg","lang_text":"Tajik","md5":"fca4e40de915a5bd2f30e32d60af45c0","name":"vosk-model-small-tg-0.22","obsolete":"false","size":51879043,"size_text":"49.5MiB","type":"small","url":"https://alphacephei.com/vosk/models/vosk-model-small-tg-0.22.zip","version":"0.22","license":"Apache 2.0"},{"lang":"tr","lang_text":"Turkish","md5":"198511631860597639a0ebf779263fcf","name":"vosk-model-small-tr-0.3","obsolete":"false","size":36855784,"size_text":"35.1MiB","type":"small","url":"https://alphacephei.com/vosk/models/vosk-model-small-tr-0.3.zip","version":"0.3","license":"Apache 2.0"},{"lang":"ua","lang_text":"Ukrainian","md5":"3188e41b4a38369d8b9527d0149616ab","name":"vosk-model-small-uk-v3-small","obsolete":"false","size":143914407,"size_text":"137.2MiB","type":"small","url":"https://alphacephei.com/vosk/models/vosk-model-small-uk-v3-small.zip","version":"0.3","license":"Apache 2.0"},{"lang":"uz","lang_text":"Uzbek","md5":"4d75acfef76fe919c8fb68cd1179c182","name":"vosk-model-small-uz-0.22","obsolete":"false","size":51061189,"size_text":"48.7MiB","type":"small","url":"https://alphacephei.com/vosk/models/vosk-model-small-uz-0.22.zip","version":"0.22","license":"Apache 2.0"},{"lang":"vn","lang_text":"Vietnamese","md5":"b31b474a1ef75488c5fa575f8e2a1269","name":"vosk-model-small-vn-0.4","obsolete":"false","size":33656337,"size_text":"32.1MiB","type":"small","url":"https://alphacephei.com/vosk/models/vosk-model-small-vn-0.4.zip","version":"0.4","license":"Apache 2.0"},{"lang":"all","lang_text":"All","md5":"63b868d866a756c30f048b007541fd25","name":"vosk-model-spk-0.4","obsolete":"false","size":13869103,"size_text":"13.2MiB","type":"spk","url":"https://alphacephei.com/vosk/models/vosk-model-spk-0.4.zip","version":"0.4","license":"Apache 2.0"},{"lang":"tg","lang_text":"Tajik","md5":"44aef3049d0cba96d2bffda308ef0859","name":"vosk-model-tg-0.22","obsolete":"false","size":335635924,"size_text":"320.1MiB","type":"big","url":"https://alphacephei.com/vosk/models/vosk-model-tg-0.22.zip","version":"0.22","license":"Apache 2.0"},{"lang":"ua","lang_text":"Ukrainian","md5":"138fb6e39f858619527030f064c0a8fc","name":"vosk-model-uk-v3","obsolete":"false","size":371048965,"size_text":"353.9MiB","type":"big","url":"https://alphacephei.com/vosk/models/vosk-model-uk-v3.zip","version":"v3","license":"Apache 2.0"},{"lang":"ua","lang_text":"Ukrainian","md5":"dc44144856364743c83555bc48aa3792","name":"vosk-model-uk-v3-lgraph","obsolete":"false","size":340762018,"size_text":"325.0MiB","type":"big-lgraph","url":"https://alphacephei.com/vosk/models/vosk-model-uk-v3-lgraph.zip","version":"v3-lgraph","license":"Apache 2.0"},{"lang":"vn","lang_text":"Vietnamese","md5":"55d5f767f7423fe81a33ebded6c5987b","name":"vosk-model-vn-0.4","obsolete":"false","size":74423562,"size_text":"71.0MiB","type":"big","url":"https://alphacephei.com/vosk/models/vosk-model-vn-0.4.zip","version":"0.4","license":"Apache 2.0"}]"#
}

final class NagramiXVoskModels: NSObject, URLSessionDownloadDelegate, @unchecked Sendable {
    static let shared = NagramiXVoskModels()
    static let changed = Notification.Name("NagramiXVoskModelsChanged")
    private let lock = NSRecursiveLock()
    private var tasks: [Int: (NagramiXVoskModel, (Result<Void, NagramiXTranscriptionFailure>) -> Void)] = [:]
    private var leases: [String: Int] = [:]
    private var errors: [String: String] = [:]
    private var progress: [String: Int] = [:]
    private var active: [String: URLSessionDownloadTask] = [:]
    private lazy var session: URLSession = {
        let config = URLSessionConfiguration.ephemeral
        config.timeoutIntervalForRequest = 120
        config.timeoutIntervalForResource = 7200
        config.urlCache = nil; config.httpCookieStorage = nil
        let queue = OperationQueue(); queue.maxConcurrentOperationCount = 1
        return URLSession(configuration: config, delegate: self, delegateQueue: queue)
    }()
    private var directory: URL { FileManager.default.urls(for: .applicationSupportDirectory, in: .userDomainMask)[0].appendingPathComponent("NagramiXVosk", isDirectory: true) }
    private func path(_ model: NagramiXVoskModel) -> URL { self.directory.appendingPathComponent(model.name, isDirectory: true) }
    func installed(_ model: NagramiXVoskModel) -> Bool { (try? Data(contentsOf: self.path(model).appendingPathComponent(".installed"))) == Data(model.md5.utf8) }
    func downloadProgress(_ model: NagramiXVoskModel) -> Int? { self.lock.lock(); defer { self.lock.unlock() }; return self.progress[model.name] }
    func status(_ model: NagramiXVoskModel) -> String {
        self.lock.lock(); defer { self.lock.unlock() }
        if let value = self.progress[model.name] { return "Загрузка · \(value)%" }
        if let error = self.errors[model.name] { return error }
        return self.installed(model) ? "Загружена" : "\(model.size / 1_000_000) МБ"
    }
    private func notify() { DispatchQueue.main.async { NotificationCenter.default.post(name: Self.changed, object: nil) } }
    func download(_ model: NagramiXVoskModel, completion: @escaping (Result<Void, NagramiXTranscriptionFailure>) -> Void) {
        self.lock.lock(); defer { self.lock.unlock() }
        guard self.active[model.name] == nil, let url = URL(string: model.url), url.scheme == "https", url.host == "alphacephei.com", url.lastPathComponent == model.name + ".zip" else { completion(.failure(.busy)); return }
        self.errors[model.name] = nil
        let task = self.session.downloadTask(with: url)
        self.tasks[task.taskIdentifier] = (model, completion); self.active[model.name] = task; self.progress[model.name] = 0
        task.resume(); self.notify()
    }
    func isDownloading(_ model: NagramiXVoskModel) -> Bool {
        self.lock.lock(); defer { self.lock.unlock() }; return self.active[model.name] != nil
    }
    func cancel(_ model: NagramiXVoskModel) { self.lock.lock(); let task = self.active[model.name]; self.lock.unlock(); task?.cancel() }
    func remove(_ model: NagramiXVoskModel) -> Bool {
        self.lock.lock(); defer { self.lock.unlock() }
        guard self.active[model.name] == nil, (self.leases[model.name] ?? 0) == 0 else { return false }
        do { if self.installed(model) { try FileManager.default.removeItem(at: self.path(model)) }; self.notify(); return true }
        catch { return false }
    }
    func withLease<T>(_ model: NagramiXVoskModel, _ body: (URL) throws -> T) throws -> T {
        self.lock.lock()
        guard self.installed(model) else { self.lock.unlock(); throw NagramiXTranscriptionFailure.missingModel }
        self.leases[model.name, default: 0] += 1; self.lock.unlock()
        defer { self.lock.lock(); self.leases[model.name, default: 1] -= 1; self.lock.unlock() }
        return try body(self.path(model))
    }
    func urlSession(_ session: URLSession, downloadTask: URLSessionDownloadTask, didWriteData bytesWritten: Int64, totalBytesWritten: Int64, totalBytesExpectedToWrite: Int64) {
        self.lock.lock()
        guard let model = self.tasks[downloadTask.taskIdentifier]?.0 else { self.lock.unlock(); return }
        if totalBytesWritten > model.size || (totalBytesExpectedToWrite > 0 && totalBytesExpectedToWrite != model.size) { self.lock.unlock(); downloadTask.cancel(); return }
        let percent = Int(min(99, totalBytesWritten * 100 / model.size))
        let changed = self.progress[model.name] != percent; self.progress[model.name] = percent
        self.lock.unlock(); if changed { self.notify() }
    }
    func urlSession(_ session: URLSession, downloadTask: URLSessionDownloadTask, didFinishDownloadingTo location: URL) {
        self.lock.lock(); let item = self.tasks[downloadTask.taskIdentifier]; self.lock.unlock()
        guard let (model, _) = item else { return }
        let stage = self.directory.appendingPathComponent("stage-" + UUID().uuidString, isDirectory: true)
        defer { try? FileManager.default.removeItem(at: stage) }
        do {
            guard (downloadTask.response as? HTTPURLResponse)?.statusCode == 200,
                  (try FileManager.default.attributesOfItem(atPath: location.path)[.size] as? NSNumber)?.int64Value == model.size else { throw NagramiXTranscriptionFailure.network }
            let file = try FileHandle(forReadingFrom: location); defer { try? file.close() }
            var hash = Insecure.MD5()
            while let data = try file.read(upToCount: 1_048_576), !data.isEmpty { hash.update(data: data) }
            guard hash.finalize().map({ String(format: "%02x", $0) }).joined() == model.md5 else { throw NagramiXTranscriptionFailure.storage }
            guard let entries = SSZipArchive.getEntriesForFile(atPath: location.path), !entries.isEmpty, entries.count <= 20000 else { throw NagramiXTranscriptionFailure.storage }
            var size: UInt64 = 0
            for entry in entries {
                let parts = entry.path.split(separator: "/", omittingEmptySubsequences: false)
                guard !entry.path.hasPrefix("/"), !entry.path.contains("\\"), !parts.contains(".."), !parts.contains("."), parts.first == Substring(model.name) else { throw NagramiXTranscriptionFailure.storage }
                let (sum, overflow) = size.addingReportingOverflow(UInt64(entry.uncompressedSize)); size = sum
                guard !overflow, size <= 8_000_000_000 else { throw NagramiXTranscriptionFailure.tooLarge }
            }
            let capacity = try self.directory.deletingLastPathComponent().resourceValues(forKeys: [.volumeAvailableCapacityForImportantUsageKey]).volumeAvailableCapacityForImportantUsage
            guard let capacity, capacity > 0, UInt64(capacity) >= size + 64 * 1024 * 1024 else { throw NagramiXTranscriptionFailure.storage }
            try FileManager.default.createDirectory(at: stage, withIntermediateDirectories: true)
            var values = URLResourceValues(); values.isExcludedFromBackup = true
            var excluded = stage; try excluded.setResourceValues(values)
            for entry in entries {
                guard downloadTask.state != .canceling else { throw NagramiXTranscriptionFailure.cancelled }
                let destination = stage.appendingPathComponent(entry.path)
                if entry.path.hasSuffix("/") { try FileManager.default.createDirectory(at: destination, withIntermediateDirectories: true); continue }
                try FileManager.default.createDirectory(at: destination.deletingLastPathComponent(), withIntermediateDirectories: true)
                // Extract each vetted entry as a regular file, without restoring symlink attributes.
                guard SSZipArchive.extractFileFromArchive(atPath: location.path, filePath: entry.path, toPath: destination.path) else { throw NagramiXTranscriptionFailure.storage }
            }
            let unpacked = stage.appendingPathComponent(model.name, isDirectory: true)
            guard FileManager.default.fileExists(atPath: unpacked.appendingPathComponent("am/final.mdl").path), FileManager.default.fileExists(atPath: unpacked.appendingPathComponent("conf/model.conf").path) else { throw NagramiXTranscriptionFailure.storage }
            self.lock.lock(); defer { self.lock.unlock() }
            guard (self.leases[model.name] ?? 0) == 0, downloadTask.state != .canceling else { throw NagramiXTranscriptionFailure.cancelled }
            let target = self.path(model)
            try Data(model.md5.utf8).write(to: unpacked.appendingPathComponent(".installed"), options: .atomic)
            if FileManager.default.fileExists(atPath: target.path) { _ = try FileManager.default.replaceItemAt(target, withItemAt: unpacked) }
            else { try FileManager.default.moveItem(at: unpacked, to: target) }
        } catch { self.lock.lock(); self.errors[model.name] = (error as? NagramiXTranscriptionFailure ?? .storage).text; self.lock.unlock() }
    }
    func urlSession(_ session: URLSession, task: URLSessionTask, didCompleteWithError error: Error?) {
        self.lock.lock()
        guard let (model, completion) = self.tasks.removeValue(forKey: task.taskIdentifier) else { self.lock.unlock(); return }
        self.active[model.name] = nil; self.progress[model.name] = nil
        let result: Result<Void, NagramiXTranscriptionFailure>
        if error == nil && self.installed(model) && self.errors[model.name] == nil { result = .success(Void()) }
        else { result = .failure((error as NSError?)?.code == NSURLErrorCancelled ? .cancelled : .storage) }
        self.lock.unlock(); self.notify(); DispatchQueue.main.async { completion(result) }
    }
    func urlSession(_ session: URLSession, task: URLSessionTask, willPerformHTTPRedirection response: HTTPURLResponse, newRequest request: URLRequest, completionHandler: @escaping (URLRequest?) -> Void) {
        completionHandler(request.url?.scheme == "https" && request.url?.host == "alphacephei.com" ? request : nil)
    }
}
