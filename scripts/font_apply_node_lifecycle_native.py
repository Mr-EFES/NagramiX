"""Проверить реальную ObjC/Swift диспетчеризацию init, отдельно от UIKit."""
import hashlib
import platform
import resource
import subprocess
import sys

from app_font_selection_runtime import UI
from validate_quick_format import block
from validate_upstream_13_2_release import checked_plan, OVERLAY
from transcription_compatibility_apple import write_module_map

STAGE = 'font_apply_node_lifecycle'
IMPLEMENTATION = 'submodules/AsyncDisplayKit/Source/ASDisplayNode.mm'
EXAMPLE = 'submodules/Display/Source/TextFieldNode.swift'
NEW = 'super.init()\n        self.setViewBlock({ button })'
OLD208 = 'super.init(viewBlock: { button }, didLoad: nil)'


def no_core():
    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))


def native_bodies(source):
    plan = checked_plan(STAGE)
    def native(name):
        path = source/name
        data = path.read_bytes() if path.exists() else (OVERLAY/plan['guard_sources'][name]).read_bytes()
        assert hashlib.sha256(data).hexdigest() == plan['guards'][name], name
        return data.decode()
    text = native(IMPLEMENTATION)
    default = block(text, '- (instancetype)init\n')
    one = block(text, '- (instancetype)initWithViewBlock:(ASDisplayNodeViewBlock)viewBlock\n')
    two = block(text, '- (instancetype)initWithViewBlock:(ASDisplayNodeViewBlock)viewBlock didLoadBlock:')
    setter = block(text, '- (void)setViewBlock:')
    assert '[super init]' in default and '[self init]' not in default
    assert 'self = [self init]' in two and '[self setViewBlock:viewBlock]' in two
    assert 'ASDisplayNodeAssertFalse(self.nodeLoaded)' in setter and '_viewBlock = viewBlock;' in setter
    example = block(native(EXAMPLE), '    override public init()')
    assert 'super.init()' in example and 'self.setViewBlock({' in example
    return default, one, two, setter


def check(source, swiftc, folder):
    from font_preview_apply_native import final_ui, native_declarations, NODE
    bodies = native_bodies(source)
    if sys.platform != 'darwin':
        return {'status': 'not_run', 'native_implementation_guards': 'passed',
                'reason': 'Mixed Swift/Objective-C Foundation runtime requires macOS; Linux model is only a constructor-route/identity/size boundary. Device208 matching-dSYM crash independently proves old default-init redispatch.'}
    folder.mkdir(parents=True, exist_ok=True)
    header, _ = native_declarations(source)
    header = header.replace('#import <UIKit/UIKit.h>', '''#import <Foundation/Foundation.h>
#import <CoreGraphics/CoreGraphics.h>
@interface UIView : NSObject
@property(nonatomic) CGRect bounds;
@end''', 1)
    header = header.replace('@interface ASDisplayNode : NSObject\n', '''@interface ASDisplayNode : NSObject {
    ASDisplayNodeViewBlock _viewBlock;
    UIView *_loadedView;
    NSUInteger _nativeInitializations;
    BOOL _nativeSynchronous;
}
@property(nonatomic, readonly) UIView *view;
@property(nonatomic, readonly) BOOL nodeLoaded;
@property(nonatomic, readonly) NSUInteger nativeInitializations;
- (void)_initializeInstance;
- (void)onDidLoad:(ASDisplayNodeDidLoadBlock)body;
''', 1)
    header_path = folder/'TextureRuntime.h'; header_path.write_text(header)
    implementation = '''#import "TextureRuntime.h"
#define ASDisplayNodeAssertFalse(v) NSCAssert(!(v), @"Node must not be loaded")
#define ASDisplayNodeAssertNotNil(v, ...) NSCAssert((v) != nil, @"A view factory is required")
#define setFlag(name, value) (_nativeSynchronous = (value))
@implementation UIView
@end
@implementation ASDisplayNode
- (void)_initializeInstance { _nativeInitializations++; }
''' + '\n'.join(bodies) + '''
- (NSUInteger)nativeInitializations { return _nativeInitializations; }
- (BOOL)nodeLoaded { return _loadedView != nil; }
- (UIView *)view {
    if (_loadedView == nil) { _loadedView = _viewBlock != nil ? _viewBlock() : [UIView new]; }
    return _loadedView;
}
- (void)onDidLoad:(ASDisplayNodeDidLoadBlock)body { body(self); }
- (CGSize)calculateSizeThatFits:(CGSize)constrainedSize { return CGSizeZero; }
@end
'''
    implementation_path = folder/'TextureRuntime.m'; implementation_path.write_text(implementation)
    module = folder/'module'; write_module_map(module, header_path, 'NagramiXTextureRuntime')
    sdk = subprocess.check_output(['xcrun', '--sdk', 'macosx', '--show-sdk-path'], text=True).strip()
    clang = subprocess.check_output(['xcrun', '--sdk', 'macosx', '--find', 'clang'], text=True).strip()
    target = platform.machine()+'-apple-macos12.0'
    library = folder/'libNagramiXTextureRuntime.dylib'
    result = subprocess.run([clang, '-fobjc-arc', '-fblocks', '-dynamiclib', '-Werror', '-isysroot', sdk,
                             '-target', target, '-framework', 'Foundation', '-framework', 'CoreGraphics',
                             str(implementation_path), '-o', str(library)], capture_output=True, text=True, timeout=120)
    assert result.returncode == 0, result.stdout+result.stderr
    ui, contract = final_ui(source); node = block(ui, NODE)
    code = '''import Foundation
import CoreGraphics
import NagramiXTextureRuntime
final class UIButton: UIView {}
''' + node + '''
@main struct NativeInitializationChecks {
 static func main() {
    let button=UIButton();button.bounds=CGRect(x:0,y:0,width:136,height:40)
    let node=NagramiXFontApplyNode(button:button)
    precondition(node.nativeInitializations == 1 && !node.nodeLoaded)
    precondition(node.view === button && node.view === button)
    precondition(node.calculateSizeThatFits(.zero) == button.bounds.size)
    button.bounds=CGRect(x:0,y:0,width:184,height:48)
    precondition(node.calculateSizeThatFits(.zero) == button.bounds.size)
    print("4 actual Objective-C initializer-dispatch checks")
 }
}
'''
    assert code.count(NEW) == 1
    runs = []
    for mode, flags in [('debug', []), ('optimized', ['-O'])]:
        for name, text, expected in [('current', code, True), ('original208', code.replace(NEW, OLD208, 1), False)]:
            path = folder/(name+'-'+mode+'.swift'); path.write_text(text)
            binary = folder/(name+'-'+mode)
            command = [str(swiftc), '-swift-version', '5', '-parse-as-library', '-warnings-as-errors',
                       '-sdk', sdk, '-target', target, '-module-cache-path', str(folder/'cache'),
                       '-I', str(module), '-L', str(folder), '-lNagramiXTextureRuntime',
                       '-Xlinker', '-rpath', '-Xlinker', str(folder), *flags, str(path), '-o', str(binary)]
            result = subprocess.run(command, capture_output=True, text=True, timeout=120)
            assert result.returncode == 0, result.stdout+result.stderr
            result = subprocess.run([str(binary)], capture_output=True, text=True, timeout=30, preexec_fn=no_core)
            if expected:
                assert result.returncode == 0 and '4 actual Objective-C initializer-dispatch checks' in result.stdout, result.stdout+result.stderr
            else:
                assert result.returncode != 0 and 'unimplemented initializer' in result.stderr.lower() and 'init()' in result.stderr, result.stdout+result.stderr
            runs.append({'case': name, 'mode': mode, 'expected': 'passed' if expected else 'original208 unimplemented-init trap reproduced', 'verified': True})
            binary.unlink()
    return {'status': 'passed', 'source_contract': contract, 'runs': runs,
            'scope': 'Native default/view-block initializers and setViewBlock bodies copied verbatim from guarded Texture implementation; actual macOS Objective-C/Foundation/Swift dispatch. UIView/UIButton, flags and _initializeInstance internals are explicit I/O adapters. UIKit/rendering/full Texture and iPhone are separate gates.'}
