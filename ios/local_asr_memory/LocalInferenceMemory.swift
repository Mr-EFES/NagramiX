import Foundation
import os

/// Additional allocation budget for the pinned CPU recognizers. Download size
/// is not a RAM requirement: Vosk ZIP compression varies by model and language.
enum NagramiXLocalInferenceMemory {
    private static let queueName = "NagramiXTranscription.LocalInference"
    static let queue = DispatchQueue(label: queueName, qos: .utility)
    // The download menu uses the same multilingual mobile weights on every
    // supported device. Existing saved/installed legacy models remain readable.
    static let whisperModels: [NagramiXWhisperModel] = [.base, .small_full, .large_v3_turbo_q8_0]
    static func isMobileVosk(_ model: NagramiXVoskModel) -> Bool {
        model.type == "small" || model.name == "vosk-model-ru-0.10-lgraph"
    }
    static func voskModels(language: String) -> [NagramiXVoskModel] {
        Array(NagramiXVoskModel.all.filter { $0.lang == language && self.isMobileVosk($0) }.sorted { $0.size < $1.size }.prefix(2))
    }
    static var voskLanguages: Set<String> {
        Set(NagramiXVoskModel.all.filter { self.isMobileVosk($0) }.map { $0.lang })
    }
    static let mib: UInt64 = 1024 * 1024
    static let reserve: UInt64 = 128 * mib

    static func require(_ bytes: UInt64, available: UInt64 = UInt64(os_proc_available_memory())) throws {
        guard bytes <= available else { throw NagramiXTranscriptionFailure.insufficientMemory }
    }

    static func sum(_ lhs: UInt64, _ rhs: UInt64) throws -> UInt64 {
        let (value, overflow) = lhs.addingReportingOverflow(rhs)
        guard !overflow else { throw NagramiXTranscriptionFailure.tooLarge }
        return value
    }

    static func product(_ lhs: UInt64, _ rhs: UInt64) throws -> UInt64 {
        let (value, overflow) = lhs.multipliedReportingOverflow(by: rhs)
        guard !overflow else { throw NagramiXTranscriptionFailure.tooLarge }
        return value
    }

    static func whisper(_ model: NagramiXWhisperModel) throws -> UInt64 {
        let name = model.rawValue
        let width: UInt64
        let layers: UInt64
        if name.hasPrefix("tiny") { width = 384; layers = 4 }
        else if name.hasPrefix("base") { width = 512; layers = 6 }
        else if name.hasPrefix("small") { width = 768; layers = 12 }
        else if name.hasPrefix("medium") { width = 1024; layers = 24 }
        else if name.hasPrefix("large") { width = 1280; layers = name.contains("turbo") ? 4 : 32 }
        else { throw NagramiXTranscriptionFailure.missingModel }
        // whisper.cpp v1.7.6: fp16 K/V for padded 512-token self attention and
        // 1536-frame cross attention, plus the encoder padding cache.
        let kv = 4 * width * (layers * (512 + 1536) + 1536)
        // Float logits for the multilingual vocabulary and 448 text tokens.
        let logits: UInt64 = 51866 * 448 * 4
        // CPU flash-attention graph/metadata/work buffers; independently checked
        // against allocation probes for all upstream model families.
        let workspace = 256 * mib + width * 1500 * 32
        guard model.size > 0 else { throw NagramiXTranscriptionFailure.missingModel }
        return try sum(UInt64(model.size), kv + logits + workspace + reserve)
    }

    static func vosk(at directory: URL) throws -> UInt64 {
        var scanError: Error?
        let keys: [URLResourceKey] = [.isRegularFileKey, .isSymbolicLinkKey, .fileSizeKey]
        guard let files = FileManager.default.enumerator(at: directory, includingPropertiesForKeys: keys,
            errorHandler: { _, error in scanError = error; return false }) else { throw NagramiXTranscriptionFailure.storage }
        var bytes: UInt64 = 0
        for case let file as URL in files {
            let values = try file.resourceValues(forKeys: Set(keys))
            guard values.isSymbolicLink != true else { throw NagramiXTranscriptionFailure.storage }
            guard values.isRegularFile == true else { continue }
            guard let count = values.fileSize, count >= 0 else { throw NagramiXTranscriptionFailure.storage }
            let size = UInt64(count)
            let contribution: UInt64
            if file.pathExtension == "fst" {
                contribution = try self.fst(at: file, fileBytes: size)
            } else if ["mdl", "ie", "mat", "raw"].contains(file.pathExtension) {
                // Kaldi compressed matrices can expand to float32 at load time.
                contribution = try self.product(size, 4)
            } else {
                contribution = try self.sum(size, size / 4)
            }
            bytes = try self.sum(bytes, contribution)
        }
        guard scanError == nil, bytes > 0 else { throw NagramiXTranscriptionFailure.storage }
        // Decoder tokens, feature pipeline, symbol tables and allocator slack.
        return try self.sum(bytes, 256 * mib + self.reserve)
    }

    static func fst(at file: URL, fileBytes: UInt64) throws -> UInt64 {
        let handle = try FileHandle(forReadingFrom: file)
        defer { try? handle.close() }
        let header = try handle.read(upToCount: 4096) ?? Data()
        return try self.fst(header: header, fileBytes: fileBytes)
    }

    static func fst(header: Data, fileBytes: UInt64) throws -> UInt64 {
        var offset = 0
        func integer(_ width: Int) -> UInt64? {
            guard offset <= header.count, width <= header.count - offset else { return nil }
            var value: UInt64 = 0
            for index in 0 ..< width { value |= UInt64(header[offset + index]) << (8 * index) }
            offset += width
            return value
        }
        func string() -> String? {
            guard let length = integer(4), length <= 256, Int(length) <= header.count - offset else { return nil }
            defer { offset += Int(length) }
            return String(data: header.subdata(in: offset ..< offset + Int(length)), encoding: .utf8)
        }
        let fallback = try self.product(fileBytes, 2)
        guard integer(4) == 2125659606, let type = string(), string() == "standard",
              integer(4) != nil, integer(4) != nil, integer(8) != nil, integer(8) != nil,
              let states = integer(8), let arcs = integer(8), states < (1 << 40), arcs < (1 << 40) else { return fallback }
        // OpenFst StdArc uses four 32-bit fields. VectorFst state/vector growth
        // costs more than its serialized bytes; ConstFst has contiguous arrays.
        let graph: UInt64
        if type == "const" || type == "const64" {
            graph = try self.sum(self.product(states, 32), self.product(arcs, 16))
        } else if type == "vector" {
            graph = try self.sum(self.product(states, 64), self.product(arcs, 32))
        } else { return fallback }
        return max(fileBytes, try self.sum(graph, 16 * mib))
    }
}
