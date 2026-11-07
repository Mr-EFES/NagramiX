#!/usr/bin/env python3
"""Compile production UI boundaries that failed in SDK build180.

Foundation lifecycle/JSON/file I/O are real. UIKit, transport and the archive
writer are test boundaries; full Apple SDK compilation remains mandatory.
"""
import argparse
import json
from pathlib import Path
import re
import subprocess
import tempfile

from validate_quick_format import block
from validate_upstream_13_2_release import OVERLAY, checked_plan, digest, guard_checks

STAGE = 'upstream_13_2_release_ui_compile'
TITLE = 'submodules/TelegramUI/Components/ChatTitleView/Sources/ChatTitleView.swift'
CRASH = 'submodules/DebugSettingsUI/Sources/CrashReportsController.swift'
MEDIA = 'submodules/TelegramUI/Components/Chat/ChatMessageInteractiveMediaNode/Sources/ChatMessageInteractiveMediaNode.swift'
REPORT = 'submodules/CrashReporting/Sources/CrashReport.swift'


def braced(text, start, brace=None):
    brace = text.index('{', start) if brace is None else brace
    depth = 1
    for end in range(brace + 1, len(text)):
        if text[end] == '{':
            depth += 1
        elif text[end] == '}':
            depth -= 1
        if depth == 0:
            return text[start:end + 1]
    raise AssertionError('Unbalanced production block')


def title_probe(text):
    # These are the real class destructors, preserving the duplicate in Before.
    destructors = '\n'.join(braced(text, match.start()) for match in re.finditer(r'^    deinit \{', text, re.M))
    return r'''
import Foundation
var disposalCount = 0
var notificationCount = 0
final class Disposable { func dispose() { disposalCount += 1 } }
final class TitleProbe {
    let agentSelectionDisposable = Disposable()
    var nagramiXSettingsObserver: NSObjectProtocol?
    init(observe: Bool) {
        if observe {
            nagramiXSettingsObserver = NotificationCenter.default.addObserver(forName: .init("probe"), object: nil, queue: nil) { _ in notificationCount += 1 }
        }
    }
''' + destructors + r'''
}
final class WeakProbe { weak var value: TitleProbe?; init(_ value: TitleProbe?) { self.value = value } }
var title: TitleProbe? = TitleProbe(observe: true)
let reference = WeakProbe(title)
NotificationCenter.default.post(name: .init("probe"), object: nil)
precondition(notificationCount == 1)
title = nil
NotificationCenter.default.post(name: .init("probe"), object: nil)
precondition(reference.value == nil && notificationCount == 1 && disposalCount == 1)
title = TitleProbe(observe: false)
title = nil
precondition(disposalCount == 2)
print("PASS: native subscription disposed and settings observer removed exactly once")
'''


def crash_probe(text, report):
    metadata = block(report, 'public struct CrashReportMetadata:')
    export_type = block(report, 'private struct ExportMetadata:')
    export = block(report, '    public func exportMetadata(')
    archive = block(text, 'private func crashReportArchive(')
    return r'''
import Foundation
''' + metadata + r'''
struct CrashReport {
    let id: String
    let diagnosticJSON: Data
    let text: String
    let metadata: CrashReportMetadata
    let receivedAt: Date
''' + export + '\n}\n' + export_type + r'''
var currentBundleIdentifier: String? = "org.nagramix.test"
struct AppBundleProbe { let bundleIdentifier: String? }
func getAppBundle() -> AppBundleProbe { .init(bundleIdentifier: currentBundleIdentifier) }
var archivedDirectories: [String] = []
enum SSZipArchive {
    static func createZipFile(atPath path: String, withFilesAtPaths paths: [String]) -> Bool {
        precondition(Set(paths.map { URL(fileURLWithPath: $0).lastPathComponent }) == Set(["crash.json", "metadata.json", "report.txt"]))
        let metadataPath = paths.first { $0.hasSuffix("metadata.json") }!
        let data = try! Data(contentsOf: URL(fileURLWithPath: metadataPath))
        let json = try! JSONSerialization.jsonObject(with: data) as! [String: Any]
        precondition(json["bundleId"] as? String == (currentBundleIdentifier ?? "Unknown"))
        precondition(json["reportId"] as? String == "test-report")
        let app = json["metadata"] as! [String: Any]
        precondition(app["applicationVersion"] as? String == "0.8.9")
        precondition(app["buildVersion"] as? String == "181")
        try! Data([1, 2, 3]).write(to: URL(fileURLWithPath: path))
        archivedDirectories.append(URL(fileURLWithPath: path).deletingLastPathComponent().path)
        return true
    }
}
''' + archive + r'''
let report = CrashReport(id: "test-report", diagnosticJSON: Data("{}".utf8), text: "text", metadata: CrashReportMetadata(applicationVersion: "0.8.9", buildVersion: "181", osVersion: "15", deviceType: "test", architecture: "arm64"), receivedAt: Date(timeIntervalSince1970: 100))
for value: String? in ["org.nagramix.test", nil] {
    currentBundleIdentifier = value
    precondition(try! crashReportArchive(report) == Data([1, 2, 3]))
    precondition(!FileManager.default.fileExists(atPath: archivedDirectories.last!))
}
print("PASS: production metadata/archive call preserves app bundle, fallback, fields and cleanup")
'''


def spoiler_probe(text, utils):
    method = block(utils, '    func isSensitiveContent(').split('{', 1)[0]
    marker = '                            if message.attributes.contains(where: { $0 is MediaSpoilerMessageAttribute }) {'
    assert text.count(marker) == 1
    start = text.index(marker)
    section = braced(text, start, start + len(marker) - 1)
    return r'''
import Foundation
protocol MessageAttribute {}
struct MediaSpoilerMessageAttribute: MessageAttribute {}
struct ContentSettings { let sensitive: Bool }
struct Atomic { let value: ContentSettings; func with<T>(_ body: (ContentSettings) -> T) -> T { body(value) } }
struct Context { let currentContentSettings: Atomic }
var sensitivityChecks = 0
struct Message {
    let attributes: [MessageAttribute]
''' + method + r''' { sensitivityChecks += 1; precondition(platform == "ios"); return contentSettings.sensitive }
}
enum NagramiXMediaSettings { static var autoRevealSpoilersEnabled = false }
final class Node {
    var internallyVisible: Bool
    var extendedMediaOverlayNode: Int? = nil
    var updates = 0
    init(_ visible: Bool) { internallyVisible = visible }
    func updateVisibility() { updates += 1 }
}
func render(context: Context, message: Message, strongSelf: Node, isSecretMedia: Bool, isExtendedMediaPreview: Bool) {
''' + section + r'''
}
for enabled in [false, true] {
 for sensitive in [false, true] {
  for secret in [false, true] {
   for extended in [false, true] {
    for visible in [false, true] {
     NagramiXMediaSettings.autoRevealSpoilersEnabled = enabled
     let node = Node(visible)
     let initialChecks = sensitivityChecks
     render(context: .init(currentContentSettings: .init(value: .init(sensitive: sensitive))), message: .init(attributes: [MediaSpoilerMessageAttribute()]), strongSelf: node, isSecretMedia: secret, isExtendedMediaPreview: extended)
     let expected = enabled && !secret && !extended && !sensitive
     precondition(node.internallyVisible == expected)
     precondition(node.updates == (visible == expected ? 0 : 1))
     precondition(sensitivityChecks == initialChecks + (enabled && !secret && !extended ? 1 : 0))
    }
   }
  }
 }
}
print("PASS: 32 spoiler visibility cases retain current content settings and protected-media gates")
'''


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--swiftc', type=Path, required=True)
    parser.add_argument('--report', type=Path)
    args = parser.parse_args()
    plan = checked_plan(STAGE)
    for name, expected in {**plan['outputs'], **plan['guards']}.items():
        assert digest(args.source / name) == expected, name
    before = {name: (OVERLAY / snapshot).read_text() for name, snapshot in plan['previous'].items()}
    after = {name: (args.source / name).read_text() for name in plan['outputs']}
    assert after[TITLE].count('    deinit {') == 1
    assert 'import AppBundle' in after[CRASH] and '#if DEBUG\nimport AppBundle' not in after[CRASH]
    report_source = (args.source / REPORT).read_text()
    utils = (args.source / 'submodules/TelegramCore/Sources/Utils/MessageUtils.swift').read_text()
    fixtures = [(TITLE, title_probe, "invalid redeclaration of 'deinit'"),
                (CRASH, lambda t: crash_probe(t, report_source), "missing argument for parameter 'bundleId'"),
                (MEDIA, lambda t: spoiler_probe(t, utils), "missing argument for parameter 'contentSettings'")]
    with tempfile.TemporaryDirectory(prefix='nagramix-ui-sdk-132-') as temporary:
        folder = Path(temporary)
        guard_folder = folder / 'guards'
        guard_folder.mkdir()
        rejected = guard_checks(args.source, STAGE, plan, guard_folder)
        for index, (name, fixture, diagnostic) in enumerate(fixtures):
            file = folder / f'probe{index}.swift'
            for flags in ([], ['-O']):
                cache = ['-module-cache-path', str(folder / 'cache')]
                file.write_text(fixture(after[name]))
                binary = folder / f'probe{index}'
                subprocess.run([str(args.swiftc), *cache, '-warnings-as-errors', *flags, str(file), '-o', str(binary)], check=True)
                subprocess.run([str(binary)], check=True)
                file.write_text(fixture(before[name]))
                bad = subprocess.run([str(args.swiftc), *cache, '-typecheck', *flags, str(file)], capture_output=True, text=True)
                assert bad.returncode != 0 and diagnostic in bad.stderr, bad.stderr
            subprocess.run([str(args.swiftc), '-frontend', '-parse', str(args.source / name)], check=True)
    result = {'replacements': 3, 'guards': 6, 'fail_closed': len(rejected),
              'production_boundary_executions': 6, 'old_api_errors_reproduced': 6,
              'full_apple_sdk': 'pending', 'device': 'pending'}
    if args.report:
        args.report.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
