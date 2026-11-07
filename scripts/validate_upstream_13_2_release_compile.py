#!/usr/bin/env python3
"""Compile the production boundaries that failed in Apple SDK build179.

UIKit declarations and the upload transport are narrow test doubles. This checks
the actual method/closure scopes, not the complete UIKit or Telegram API modules;
the clean Apple SDK build remains mandatory.
"""
import argparse
import json
from pathlib import Path
import subprocess
import tempfile

from validate_quick_format import block
from validate_upstream_13_2_release import OVERLAY, checked_plan, digest, guard_checks

STAGE = 'upstream_13_2_release_compile'
INTRO = 'submodules/RMIntro/Sources/platform/ios/RMIntroViewController.m'
HEADER = 'submodules/RMIntro/PublicHeaders/RMIntro/RMIntroViewController.h'
UPLOAD = 'submodules/TelegramCore/Sources/PendingMessages/PendingMessageUploadedContent.swift'


def objc_probe(text, header):
    ivars = block(header, '@interface RMIntroViewController').split('{', 1)[1].rsplit('}', 1)[0]
    # Use the actual public ivar inventory and the private accessibility state.
    assert '_current_page_end' not in ivars
    method = block(text, '- (void)accessibilityShowPage:')
    return r'''
typedef long NSInteger;
typedef unsigned long NSUInteger;
typedef double CGFloat;
typedef struct { CGFloat x, y; } CGPoint;
typedef struct { CGFloat width, height; } CGSize;
typedef struct { CGPoint origin; CGSize size; } CGRect;
#define true 1
#define MAX(a, b) ((a) > (b) ? (a) : (b))
#define MIN(a, b) ((a) < (b) ? (a) : (b))
typedef signed char BOOL;
@interface NSObject @end
@class EAGLContext, GLKView, NSMutableArray, NSTimer;
@interface NSArray : NSObject
@property (readonly) NSUInteger count;
@end
@interface UIPageControl : NSObject
- (void)setCurrentPage:(NSInteger)page;
@end
@interface UIScrollView : NSObject
@property CGRect frame;
- (void)setContentOffset:(CGPoint)offset animated:(BOOL)animated;
@end
static CGPoint CGPointMake(CGFloat x, CGFloat y) { return (CGPoint){x, y}; }
@interface RMIntroProbe : NSObject {
''' + ivars + '\nNSInteger _accessibilityPendingPage;\n}\n@end\n@implementation RMIntroProbe\n' + method + '\n@end\n'


def swift_probe(text):
    start = text.index('    } else if let poll = media as? TelegramMediaPoll {')
    prefix = text[start:].split('        var pollFlags: Int32 = 0', 1)[0].split('\n', 1)[1]
    # The production prefix contains both the Signal error guard and the
    # result-returning assembler, including its media reference resolver.
    result = block(text, 'enum PendingMessageUploadedContentResult')
    return r'''
enum PendingMessageUploadError: Error { case generic }
struct PendingMessageUploadedContentProgress {}
struct PendingMessageUploadedContentAndReuploadInfo { let content: Int }
enum Api { typealias InputMedia = Int }
typealias MediaId = Int
struct Media { let id: Int? }
struct PeerId { let namespace: Int }
enum Namespaces { enum Peer { static let SecretChat = 5 } }
var cloudCalls = 0
func pollCloudMediaToInputMedia(_ media: Media) -> Int? { cloudCalls += 1; return media.id }
struct Signal<Value, Failure: Error> {
    let value: Value?
    let failure: Failure?
    static func single(_ value: Value) -> Self { .init(value: value, failure: nil) }
    static func fail(_ error: Failure) -> Self { .init(value: nil, failure: error) }
}
''' + result + '''
func uploadPoll(peerId: PeerId, resolved: [MediaId: Api.InputMedia]) -> Signal<PendingMessageUploadedContentResult, PendingMessageUploadError>? {
''' + prefix + '''
            return .content(.init(content: inputPollMedia(Media(id: 42)) ?? -1))
        }
        return .single(assemble(resolved))
}
let secret = uploadPoll(peerId: PeerId(namespace: 5), resolved: [:])!
precondition(secret.failure != nil && secret.value == nil && cloudCalls == 0)
let ordinary = uploadPoll(peerId: PeerId(namespace: 1), resolved: [42: 99])!
if case let .content(content)? = ordinary.value { precondition(content.content == 99) } else { fatalError() }
precondition(ordinary.failure == nil && cloudCalls == 0)
let fallback = uploadPoll(peerId: PeerId(namespace: 1), resolved: [:])!
if case let .content(content)? = fallback.value { precondition(content.content == 42) } else { fatalError() }
precondition(fallback.failure == nil && cloudCalls == 1)
print("PASS: secret-chat failure precedes resolution; cloud/uploaded references retain their results")
'''


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--swiftc', type=Path, required=True)
    parser.add_argument('--clang', type=Path, required=True)
    parser.add_argument('--report', type=Path)
    args = parser.parse_args()
    plan = checked_plan(STAGE)
    for name, expected in {**plan['outputs'], **plan['guards']}.items():
        assert digest(args.source / name) == expected, name
    before = {name: (OVERLAY / snapshot).read_text() for name, snapshot in plan['previous'].items()}
    after = {name: (args.source / name).read_text() for name in plan['outputs']}
    assert after[INTRO] == before[INTRO].replace('    _current_page_end = page;\n', '', 1)
    guard = '        if peerId.namespace == Namespaces.Peer.SecretChat {\n            return .fail(.generic)\n        }\n'
    anchor = '    } else if let poll = media as? TelegramMediaPoll {\n'
    assert before[UPLOAD].count(guard) == 1
    assert after[UPLOAD] == before[UPLOAD].replace(guard, '', 1).replace(anchor, anchor + guard, 1)
    with tempfile.TemporaryDirectory(prefix='nagramix-sdk-132-') as temporary:
        folder = Path(temporary)
        guards = folder / 'guards'
        guards.mkdir()
        rejected = guard_checks(args.source, STAGE, plan, guards)
        header = (args.source / HEADER).read_text()
        objc = folder / 'intro.m'
        command = [str(args.clang), '-fsyntax-only', '-fblocks', '-Werror', '-Wno-objc-root-class', '-x', 'objective-c', str(objc)]
        objc.write_text(objc_probe(after[INTRO], header))
        subprocess.run(command, check=True)
        objc.write_text(objc_probe(before[INTRO], header))
        failed = subprocess.run(command, capture_output=True, text=True)
        assert failed.returncode != 0 and "undeclared identifier '_current_page_end'" in failed.stderr, failed.stderr
        swift = folder / 'poll.swift'
        for flags in ([], ['-O']):
            swift.write_text(swift_probe(after[UPLOAD]))
            executable = folder / 'poll'
            cache = ['-module-cache-path', str(folder / 'module-cache')]
            subprocess.run([str(args.swiftc), *cache, '-warnings-as-errors', *flags, str(swift), '-o', str(executable)], check=True)
            subprocess.run([str(executable)], check=True)
            swift.write_text(swift_probe(before[UPLOAD]))
            failed = subprocess.run([str(args.swiftc), *cache, '-typecheck', *flags, str(swift)], capture_output=True, text=True)
            assert failed.returncode != 0 and "has no member 'fail'" in failed.stderr, failed.stderr
        subprocess.run([str(args.swiftc), '-frontend', '-parse', str(args.source / UPLOAD)], check=True)
    report = {'replacements': 2, 'guards': 4, 'fail_closed': len(rejected), 'objc_boundary': 'passed',
              'swift_boundary_debug_and_optimized': 'passed', 'original_compiler_errors_reproduced': 3,
              'full_apple_sdk': 'pending', 'device': 'pending'}
    if args.report:
        args.report.write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
