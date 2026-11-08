#!/usr/bin/env python3
"""Проверить постоянную кнопку расшифровки временного кружка на реальном UI-блоке."""
import argparse
import hashlib
import json
from pathlib import Path
import resource
import subprocess
import tempfile

from validate_quick_format import block

ROOT = Path(__file__).resolve().parents[1]
NODE = 'submodules/TelegramUI/Components/Chat/ChatMessageInteractiveInstantVideoNode/Sources/ChatMessageInteractiveInstantVideoNode.swift'

BOUNDARY = r'''
import Foundation
#if canImport(CoreGraphics)
import CoreGraphics
#endif

// UIKit/ComponentFlow/animation/policy are explicit boundaries. The complete
// native eligibility, button creation/removal, frame, alpha and pressed blocks
// execute. Core temporary eligibility is checked by the parent stage's suite.
struct UIColor: Equatable { let id: Int; static let clear = UIColor(id: 0) }
struct Message { var eligible = false; var handled = false; var secret = false }
struct PeerId { var namespace: Int32 }
struct MessageId { var peerId: PeerId }
extension Message { var id: MessageId { MessageId(peerId: PeerId(namespace: self.secret ? 3 : 0)) } }
enum Namespaces { enum Peer { static let SecretChat: Int32 = 3 } }
func nagramiXCanTranscribeTemporaryMedia(_ message: Message) -> Bool { message.eligible }
enum NagramiXTranscriptionRuntime { static func handles(_ message: Message) -> Bool { message.handled } }
struct NativeTheme {
    struct Chat { struct Message { struct Side { var secondaryTextColor: UIColor }; var incoming = Side(secondaryTextColor: UIColor(id: 11)); var outgoing = Side(secondaryTextColor: UIColor(id: 12)); }; var message = Message() }
    var chat = Chat()
}
struct Theme { let theme = NativeTheme(); let wallpaper = 1 }
struct Colors { let primaryText = UIColor(id: 21) }
func serviceMessageColorComponents(theme: NativeTheme, wallpaper: Int) -> Colors { Colors() }
func selectDateFillStaticColor(theme: NativeTheme, wallpaper: Int) -> UIColor { UIColor(id: 22) }
func dateFillNeedsBlur(theme: NativeTheme, wallpaper: Int) -> Bool { true }
struct Presentation { var isPreview = false; struct Corners { var bubbleMode = false }; var chatBubbleCorners = Corners() }
struct AlwaysDisplay { var providedByGroupBoost = false; var canBeDisplayed = false; var displayForNotConsumed = false }
struct AssociatedData { var isPremium = false; var alwaysDisplayTranscribeButton = AlwaysDisplay() }
struct AppConfiguration { var trialCount = 0 }
struct AtomicConfiguration { var value = AppConfiguration(); func with<R>(_ f: (AppConfiguration) -> R) -> R { f(self.value) } }
struct Context { var currentAppConfiguration = AtomicConfiguration() }
struct Interaction { var enableFullTranslucency = true }
struct Item { var message = Message(); var presentationData = Presentation(); var associatedData = AssociatedData(); var context = Context(); var controllerInteraction = Interaction() }
struct PremiumConfiguration { let audioTransciptionTrialCount: Int; static func with(appConfiguration: AppConfiguration) -> Self { .init(audioTransciptionTrialCount: appConfiguration.trialCount) } }
enum Status { case free, bubble }
final class Layer { var frame = CGRect.zero; var alpha: CGFloat = 1; func animateAlpha(from: CGFloat, to: CGFloat, duration: Double) { self.alpha = to } }
struct Animator {
    func updateFrame(layer: Layer, frame: CGRect, completion: (() -> Void)?) { layer.frame = frame }
    func updateAlpha(layer: Layer, alpha: CGFloat, completion: (() -> Void)?) { layer.alpha = alpha }
}
struct Animation { var isAnimated = false; let animator = Animator() }
enum Transition { case immediate; case easeInOut(duration: Double) }
struct Empty {}
struct AnyComponent<C> { let value: C; init(_ value: C) { self.value = value } }
struct AudioTranscriptionButtonComponent {
    enum TranscriptionState { case collapsed, inProgress, expanded, locked }
    enum Theme { case freeform((UIColor, Bool), UIColor) }
    let theme: Theme
    let transcriptionState: TranscriptionState
    let pressed: () -> Void
}
final class ComponentHostView<E> {
    let layer = Layer()
    var frame: CGRect { get { self.layer.frame } set { self.layer.frame = newValue } }
    var alpha: CGFloat { self.layer.alpha }
    var isHidden = false
    weak var superview: View?
    var component: AudioTranscriptionButtonComponent?
    func update(transition: Transition, component: AnyComponent<AudioTranscriptionButtonComponent>, environment: () -> Void, containerSize: CGSize) -> CGSize { self.component = component.value; return CGSize(width: 30, height: 30) }
    func removeFromSuperview() { self.superview?.children.removeAll { $0 === self }; self.superview = nil }
}
final class View {
    var children: [ComponentHostView<Empty>] = []
    func addSubview(_ button: ComponentHostView<Empty>) { self.children.append(button); button.superview = self }
}
'''


def snippets(text):
    blur_start = text.index('                    var durationBlurColor: (UIColor, Bool)?')
    blur_end = text.index('                    let durationNodeTextColor', blur_start)
    layout_start = text.index('                    var displayTranscribe = false', blur_end)
    layout_end = text.index('                    if let durationNode = strongSelf.durationNode', layout_start)
    return text[blur_start:blur_end], text[layout_start:layout_end]


def controller(text, name, current):
    blur, layout = snippets(text)
    declaration = next(line.strip() for line in text.splitlines() if line.strip().startswith('let nagramiXPersistentTemporaryTranscription =')) if current else ''
    # No replacement of control flow or real native frame/color/alpha expressions.
    return r'''
final class //NAME {
    let view = View()
    var audioTranscriptionButton: ComponentHostView<Empty>?
    var lastDisplay = false
    var durationFill: (UIColor, Bool)?
    var durationColor = UIColor(id: 0)
    var transcribeCalls = 0
    func transcribe() { self.transcribeCalls += 1 }
    func apply(item: Item, incoming: Bool, notConsumed: Bool, isViewOnceMessage: Bool, statusDisplayType: Status, scaleProgress: CGFloat, displayVideoFrame: CGRect, state: AudioTranscriptionButtonComponent.TranscriptionState, animation: Animation = Animation()) {
        let operation = { [weak self] in
            guard let strongSelf = self else { return }
            let theme = Theme()
            let effectiveAudioTranscriptionState = state
            //DECLARATION
            //BLUR
            //LAYOUT
            strongSelf.lastDisplay = displayTranscribe
            strongSelf.durationFill = durationBlurColor
            strongSelf.durationColor = durationTextColor
        }
        operation()
    }
}
'''.replace('//NAME', name).replace('//DECLARATION', declaration).replace('//BLUR', blur).replace('//LAYOUT', layout)


TESTS = r'''
private var count = 0
private func check(_ value: @autoclosure () -> Bool, _ label: String) {
    count += 1
    if !value() { FileHandle.standardError.write(Data(("FAIL " + label + "\n").utf8)); exit(91) }
}
private func color(_ button: ComponentHostView<Empty>?) -> UIColor? {
    guard let button, let component = button.component else { return nil }
    if case let .freeform(_, foreground) = component.theme { return foreground }
    return nil
}
private func fill(_ button: ComponentHostView<Empty>?) -> UIColor? {
    guard let button, let component = button.component else { return nil }
    if case let .freeform(background, _) = component.theme { return background.0 }
    return nil
}
@main struct PermanentTemporaryTranscription {
    static func main() {
        for eligible in [false, true] {
            for preview in [false, true] {
                for bubble in [false, true] {
                    for incoming in [false, true] {
                        for premium in [false, true] {
                            for handled in [false, true] {
                                for consumed in [false, true] {
                                    for trial in [0, 2] {
                                        for progress in [CGFloat(0), 0.25, 1] {
                                            var item = Item()
                                            item.message.eligible = eligible
                                            item.message.handled = handled
                                            item.presentationData.isPreview = preview
                                            item.associatedData.isPremium = premium
                                            item.context.currentAppConfiguration.value.trialCount = trial
                                            item.associatedData.alwaysDisplayTranscribeButton.canBeDisplayed = true
                                            item.associatedData.alwaysDisplayTranscribeButton.displayForNotConsumed = true
                                            let old = PreviousNode(), new = CurrentNode()
                                            let status: Status = bubble ? .bubble : .free
                                            let frame = CGRect(x: 0, y: 0, width: 240 + 164 * progress, height: 240 + 164 * progress)
                                            old.apply(item: item, incoming: incoming, notConsumed: !consumed, isViewOnceMessage: eligible, statusDisplayType: status, scaleProgress: progress, displayVideoFrame: frame, state: .collapsed)
                                            new.apply(item: item, incoming: incoming, notConsumed: !consumed, isViewOnceMessage: eligible, statusDisplayType: status, scaleProgress: progress, displayVideoFrame: frame, state: .collapsed)
                                            if eligible && !preview {
                                                check(new.audioTranscriptionButton != nil, "temporary button exists for free/bubble")
                                                check(new.audioTranscriptionButton?.alpha == 1 && new.lastDisplay, "temporary button remains visible while expanded")
                                                check(color(new.audioTranscriptionButton) == UIColor(id: 21) && fill(new.audioTranscriptionButton) == UIColor(id: 22), "temporary button uses native service palette")
                                                check(new.audioTranscriptionButton?.superview === new.view, "temporary button belongs to current hierarchy")
                                                check(frame.contains(new.audioTranscriptionButton!.frame), "temporary control stays within video frame")
                                                let center = CGPoint(x: new.audioTranscriptionButton!.frame.midX, y: new.audioTranscriptionButton!.frame.midY)
                                                check(new.audioTranscriptionButton!.frame.contains(center), "temporary control target follows frame")
                                                new.audioTranscriptionButton?.component?.pressed()
                                                check(new.transcribeCalls == 1, "temporary pressed callback invokes only transcription")
                                            } else {
                                                check((old.audioTranscriptionButton == nil) == (new.audioTranscriptionButton == nil), "ordinary native visibility unchanged")
                                                check(old.audioTranscriptionButton?.alpha == new.audioTranscriptionButton?.alpha && old.lastDisplay == new.lastDisplay, "ordinary native fade unchanged")
                                                check(old.audioTranscriptionButton?.frame == new.audioTranscriptionButton?.frame, "ordinary native frame unchanged")
                                                check(color(old.audioTranscriptionButton) == color(new.audioTranscriptionButton) && fill(old.audioTranscriptionButton) == fill(new.audioTranscriptionButton), "ordinary native palette unchanged")
                                            }
                                            check(old.durationFill?.0 == new.durationFill?.0 && old.durationFill?.1 == new.durationFill?.1 && old.durationColor == new.durationColor, "native duration appearance preserved")
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }
        // Playback, pause and every transcription state retain the same live control.
        let reused = CurrentNode()
        var item = Item(); item.message.eligible = true
        let frame = CGRect(x: 5, y: 7, width: 120, height: 120)
        for state in [AudioTranscriptionButtonComponent.TranscriptionState.collapsed, .inProgress, .expanded, .locked] {
            for scale in [CGFloat(0), 1, 1, 0] {
                reused.apply(item: item, incoming: false, notConsumed: false, isViewOnceMessage: true, statusDisplayType: .bubble, scaleProgress: scale, displayVideoFrame: frame, state: state, animation: Animation(isAnimated: true))
                check(reused.audioTranscriptionButton != nil && reused.audioTranscriptionButton!.alpha == 1, "repeated playback/pause keeps temporary button")
                check(frame.contains(reused.audioTranscriptionButton!.frame), "small expanded temporary frame clamped")
                check(reused.audioTranscriptionButton?.component?.transcriptionState == state, "pending/expanded/locked state preserved")
                check(reused.view.children.count == 1, "reuse never duplicates button")
            }
        }
        reused.audioTranscriptionButton?.isHidden = true
        reused.apply(item: item, incoming: false, notConsumed: false, isViewOnceMessage: true, statusDisplayType: .bubble, scaleProgress: 1, displayVideoFrame: frame, state: .collapsed)
        check(reused.audioTranscriptionButton?.isHidden == true, "native hidden state is not overwritten")
        let previous = reused.audioTranscriptionButton!
        item.message.eligible = false
        reused.apply(item: item, incoming: false, notConsumed: false, isViewOnceMessage: true, statusDisplayType: .bubble, scaleProgress: 1, displayVideoFrame: frame, state: .collapsed)
        check(reused.audioTranscriptionButton == nil && previous.superview == nil && reused.view.children.isEmpty, "OFF/reuse removes obsolete temporary control")
        print("PASS temporary ASR UI production checks: \(count)")
    }
}
'''


def verify(before, after):
    assert after.count('let nagramiXPersistentTemporaryTranscription = !item.presentationData.isPreview && nagramiXCanTranscribeTemporaryMedia(item.message)') == 1
    for marker in ['    override public func hitTest(', '    private func activateVideoPlayback()', '    private func progressPressed()']:
        assert block(before, marker) == block(after, marker), 'Unrequested playback/transcription change: ' + marker
    expected_transcribe = block(before, '    private func transcribe()').replace('guard let item = self.item, item.message.id.namespace == Namespaces.Message.Cloud else {', 'guard let item = self.item, item.message.id.namespace == Namespaces.Message.Cloud || nagramiXCanTranscribeTemporaryMedia(item.message) else {')
    assert block(after, '    private func transcribe()') == expected_transcribe, 'Only explicit temporary namespace eligibility changes in ASR handler'
    assert block(before, '    deinit') == block(after, '    deinit'), 'Native lifetime changed'
    for marker in ['    @objc private func tapLongTapOrDoubleTapGesture', '    override public func accessibilityActivate()']:
        assert block(before, marker) == block(after, marker), marker
    assert 'audioTranscriptionButton.isHidden = false' not in after
    assert after.count('nagramiXPersistentTemporaryTranscription') == 7


def execute(before, after, compiler, temp):
    def no_core():
        resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
    variants = {
        'expanded_hidden': ('alpha: nagramiXPersistentTemporaryTranscription || scaleProgress.isZero ? 1.0 : 0.0', 'alpha: scaleProgress.isZero ? 1.0 : 0.0', 'temporary button remains visible while expanded'),
        'bubble_hidden': ('if nagramiXPersistentTemporaryTranscription || (statusDisplayType', 'if (nagramiXPersistentTemporaryTranscription && statusDisplayType == .free) || (statusDisplayType', 'temporary button exists for free/bubble'),
        'preview_leak': ('!item.presentationData.isPreview && nagramiXCanTranscribeTemporaryMedia(item.message)', 'nagramiXCanTranscribeTemporaryMedia(item.message)', 'ordinary native visibility unchanged'),
        'expanded_layout_flag': ('if !scaleProgress.isZero && !nagramiXPersistentTemporaryTranscription {', 'if !scaleProgress.isZero {', 'temporary button remains visible while expanded'),
        'narrow_frame': ('if nagramiXPersistentTemporaryTranscription {\n                            audioTranscriptionButtonFrame.origin.x', 'if false {\n                            audioTranscriptionButtonFrame.origin.x', 'small expanded temporary frame clamped'),
    }
    results = []
    rejected = []
    for optimized in [False, True]:
        mode = 'optimized' if optimized else 'debug'
        for variant in [None, *variants]:
            current = after
            if variant:
                old, new, label = variants[variant]
                assert current.count(old) == 1, variant
                current = current.replace(old, new)
            text = BOUNDARY + controller(before, 'PreviousNode', False) + controller(current, 'CurrentNode', True) + TESTS
            file = temp / (mode + '-' + (variant or 'production') + '.swift')
            binary = file.with_suffix('')
            file.write_text(text)
            command = [str(compiler), '-parse-as-library', '-warnings-as-errors', '-module-cache-path', str(temp / 'cache'), str(file), '-o', str(binary)]
            if optimized:
                command.insert(1, '-O')
            result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
            assert result.returncode == 0, result.stdout
            result = subprocess.run([str(binary)], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, preexec_fn=no_core)
            if variant:
                assert result.returncode == 91 and ('FAIL ' + variants[variant][2]) in result.stdout, (variant, result.returncode, result.stdout)
                rejected.append({'mode': mode, 'variant': variant})
            else:
                assert result.returncode == 0 and 'PASS temporary ASR UI production checks:' in result.stdout, result.stdout
                results.append({'mode': mode, 'result': result.stdout.strip()})
    return results, rejected


RUNTIME = 'submodules/NagramiXTranscription/Sources/Runtime.swift'
SETTINGS = 'submodules/NagramiXTranscription/Sources/Settings.swift'

RUNTIME_BOUNDARY = r'''
import Foundation
final class TestDefaults {
    static let shared = TestDefaults()
    var data: [String: Any] = [:]
    func data(forKey key: String) -> Data? { self.data[key] as? Data }
    func set(_ value: Any?, forKey key: String) { self.data[key] = value }
}
enum Namespaces { enum Message { static let Cloud: Int32 = 0 }; enum Peer { static let SecretChat: Int32 = 3 } }
struct PeerId { var namespace: Int32 }
struct MessageId { var namespace: Int32; var peerId: PeerId }
protocol Media {}
protocol MessageAttribute {}
struct FileId { let namespace: Int32; let id: Int64 }
struct ResourceId { let stringRepresentation: String }
struct Resource { let id: ResourceId }
final class TelegramMediaFile: Media {
    let isVoice: Bool
    let isInstantVideo: Bool
    let fileId = FileId(namespace: 10, id: 99)
    let resource: Resource
    let size: Int64?
    let duration: Int32? = 15
    init(round: Bool = false, resource: String = "cloud-original", size: Int64 = 123) {
        self.isVoice = !round; self.isInstantVideo = round
        self.resource = Resource(id: ResourceId(stringRepresentation: resource)); self.size = size
    }
}
final class NagramiXArchivedMessageAttribute: MessageAttribute { let isTemporary: Bool; init(_ temp: Bool = true) { self.isTemporary = temp } }
final class AudioTranscriptionMessageAttribute: MessageAttribute {
    let id: Int64; let text: String; let isPending: Bool; let error: String?
    init(id: Int64 = 0, text: String = "saved text", isPending: Bool = false, error: String? = nil) {
        self.id = id; self.text = text; self.isPending = isPending; self.error = error
    }
}
struct Entry {
    let data: Data
    init<T: Encodable>(_ value: T) { self.data = try! JSONEncoder().encode(value) }
    func get<T: Decodable>(_ type: T.Type) -> T? { try? JSONDecoder().decode(type, from: self.data) }
}
final class DerivedDataMessageAttribute: MessageAttribute { let data: [String: Entry]; init(data: [String: Entry]) { self.data = data } }
struct EngineRawMessage {
    var id: MessageId
    var media: [Media]
    var attributes: [MessageAttribute] = []
    var policyEligible: Bool
    var containsSecretMedia = false
    var isSelfExpiring = false
    var protected = false
    func isCopyProtected() -> Bool { self.protected }
}
// The parent's Core suite checks the actual policy. This adapter supplies its
// decision so Runtime behavior, namespace gating and cache semantics execute.
func nagramiXCanTranscribeTemporaryMedia(_ message: EngineRawMessage) -> Bool { message.policyEligible }
private var checks = 0
private func check(_ value: @autoclosure () -> Bool, _ label: String) {
    checks += 1
    if !value() { FileHandle.standardError.write(Data(("FAIL " + label + "\n").utf8)); exit(91) }
}
'''

RUNTIME_TESTS = r'''
@main struct RuntimeTemporaryEligibility {
    static func main() {
        NagramiXTranscriptionSettings.update { $0.enabled = true; $0.provider = .whisper }
        for round in [false, true] {
            for namespace in [Int32(0), 1, 2] {
                for peer in [Int32(0), 1, 2, 3] {
                    let file = TelegramMediaFile(round: round)
                    var message = EngineRawMessage(id: MessageId(namespace: namespace, peerId: PeerId(namespace: peer)), media: [file], policyEligible: true, containsSecretMedia: true, isSelfExpiring: true)
                    check(NagramiXTranscriptionRuntime.file(message) === file, "approved temporary secret/local file available")
                    check(NagramiXTranscriptionRuntime.handles(message), "local provider accepts approved temporary file")
                    let server = namespace == 0 && peer != 3
                    check(NagramiXTranscriptionRuntime.canUseTelegram(message) == server, "Premium requires live cloud nonsecret ID")
                    NagramiXTranscriptionSettings.update { $0.provider = .telegram }
                    check(NagramiXTranscriptionRuntime.handlesContext(message) == server, "context cannot dispatch invalid Premium ID")
                    check(!NagramiXTranscriptionRuntime.handles(message), "Telegram never silently becomes local provider")
                    NagramiXTranscriptionSettings.update { $0.provider = .whisper }
                    message.attributes = [NagramiXArchivedMessageAttribute()]
                    check(NagramiXTranscriptionRuntime.file(message) === file, "approved retained file accepted")
                    check(!NagramiXTranscriptionRuntime.canUseTelegram(message), "retained original never sent to Premium RPC")
                    message.attributes.append(AudioTranscriptionMessageAttribute(id: 900))
                    check(NagramiXTranscriptionRuntime.hasTemporaryTranscript(message), "completed Premium text opens from retained copy")
                    message.attributes = [NagramiXArchivedMessageAttribute(), AudioTranscriptionMessageAttribute(isPending: true)]
                    check(!NagramiXTranscriptionRuntime.hasTemporaryTranscript(message), "pending text not treated as completed")
                    message.attributes = [NagramiXArchivedMessageAttribute(), AudioTranscriptionMessageAttribute(error: "failed")]
                    check(!NagramiXTranscriptionRuntime.hasTemporaryTranscript(message), "failed text not treated as completed")
                    message.policyEligible = false
                    check(NagramiXTranscriptionRuntime.file(message) == nil && !NagramiXTranscriptionRuntime.handles(message), "OFF keeps native TTL/secret exclusions")
                    check(!NagramiXTranscriptionRuntime.hasTemporaryTranscript(message), "OFF does not reopen retained transcript")
                    message.containsSecretMedia = false; message.isSelfExpiring = false
                    message.attributes = []
                    let ordinaryAllowed = namespace == 0 && peer != 3
                    check((NagramiXTranscriptionRuntime.file(message) != nil) == ordinaryAllowed, "ordinary namespace behavior preserved")
                }
            }
        }
        let live = TelegramMediaFile(), retained = TelegramMediaFile(resource: "local-retained")
        var message = EngineRawMessage(id: MessageId(namespace: 2, peerId: PeerId(namespace: 3)), media: [live], policyEligible: true, containsSecretMedia: true, isSelfExpiring: true)
        let identity = NagramiXTranscriptionRuntime.identity(live, message: message)
        check(identity == NagramiXTranscriptionRuntime.identity(retained, message: message), "temporary identity survives resource move")
        let stamp = NagramiXTranscriptionStamp(tag: NagramiXTranscriptionSettings.current.cacheTag, resource: identity)
        message.attributes = [DerivedDataMessageAttribute(data: ["nagramix.asr.v1": Entry(stamp)]), AudioTranscriptionMessageAttribute()]
        check(NagramiXTranscriptionRuntime.cached(message) == "saved text", "secret temporary cached local text available")
        message.media = [retained]; message.attributes.append(NagramiXArchivedMessageAttribute())
        check(NagramiXTranscriptionRuntime.cached(message) == "saved text", "retained resource uses same cached text")
        NagramiXTranscriptionSettings.update { $0.language = "de" }
        check(NagramiXTranscriptionRuntime.cached(message) == nil, "changed model/language invalidates local stamp")
        check(NagramiXTranscriptionRuntime.hasTemporaryTranscript(message), "finished text still opens without new request")
        NagramiXTranscriptionSettings.update { $0.enabled = false }
        check(!NagramiXTranscriptionRuntime.handles(message) && !NagramiXTranscriptionRuntime.handlesContext(message), "master OFF prevents new provider job")
        check(NagramiXTranscriptionRuntime.hasTemporaryTranscript(message), "cached finished text independent of new-job master")
        message.policyEligible = false
        check(!NagramiXTranscriptionRuntime.hasTemporaryTranscript(message), "temporary OFF hides retained cache path")
        print("PASS temporary ASR runtime production checks: \(checks)")
    }
}
'''


def runtime_execute(source, baseline, compiler, temp):
    original = (baseline / RUNTIME).read_text()
    current = (source / RUNTIME).read_text()
    methods = ['    public static func file(', '    public static func canUseTelegram(']
    reverse = current
    for marker in methods:
        reverse = reverse.replace(block(current, marker), block(original, marker))
    assert reverse == original, 'Runtime changed outside explicit temporary file/Premium eligibility'
    settings_path = source / SETTINGS if (source / SETTINGS).is_file() else baseline / SETTINGS
    settings = settings_path.read_text().replace('UserDefaults.standard', 'TestDefaults.shared')
    settings = '\n'.join(line for line in settings.splitlines() if not line.startswith('import '))
    markers = ['    public static func file(', '    public static func canUseTelegram(', '    public static func hasTemporaryTranscript(',
               '    public static func handlesContext(', '    public static func handles(', '    private static func identity(', '    public static func cached(']
    body = '\n'.join(block(current, marker).replace('private static', 'static') for marker in markers)
    stamp = block(current, 'private struct NagramiXTranscriptionStamp').replace('private ', '')
    def no_core():
        resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
    results, rejected = [], []
    variants = {
        'cloud_only_file': ('        // Temporary-media eligibility', '        guard message.id.namespace == Namespaces.Message.Cloud else { return nil }\n        // Temporary-media eligibility', 'approved temporary secret/local file available'),
        'secret_premium': ('            && message.id.peerId.namespace != Namespaces.Peer.SecretChat\n', '\n', 'Premium requires live cloud nonsecret ID'),
        'resource_cache_reset': ('? "temporary:\\(file.fileId.namespace):\\(file.fileId.id)"', '? file.resource.id.stringRepresentation', 'temporary identity survives resource move'),
    }
    for optimized in [False, True]:
        mode = 'optimized' if optimized else 'debug'
        for variant in [None, *variants]:
            methods_body = body
            if variant:
                old, new, _ = variants[variant]
                assert methods_body.count(old) == 1, variant
                methods_body = methods_body.replace(old, new)
            text = RUNTIME_BOUNDARY + settings + '\n' + stamp + '\nenum NagramiXTranscriptionRuntime {\n    private static let stampKey = "nagramix.asr.v1"\n' + methods_body + '\n}\n' + RUNTIME_TESTS
            file = temp / ('runtime-' + mode + '-' + (variant or 'production') + '.swift')
            binary = file.with_suffix('')
            file.write_text(text)
            command = [str(compiler), '-parse-as-library', '-warnings-as-errors', '-module-cache-path', str(temp / 'cache'), str(file), '-o', str(binary)]
            if optimized:
                command.insert(1, '-O')
            result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
            assert result.returncode == 0, result.stdout
            result = subprocess.run([str(binary)], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, preexec_fn=no_core)
            if variant:
                assert result.returncode == 91 and ('FAIL ' + variants[variant][2]) in result.stdout, (variant, result.returncode, result.stdout)
                rejected.append({'mode': mode, 'variant': variant})
            else:
                assert result.returncode == 0 and 'PASS temporary ASR runtime production checks:' in result.stdout, result.stdout
                results.append({'mode': mode, 'result': result.stdout.strip()})
    return results, rejected


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--baseline', type=Path)
    parser.add_argument('--swiftc', type=Path)
    parser.add_argument('--report', type=Path)
    args = parser.parse_args()
    if args.baseline:
        before_path = args.baseline / NODE
        runtime_baseline = args.baseline
    else:
        plan = json.loads((ROOT / 'ios/temporary_message_interaction_patches.json').read_text())
        before_path = ROOT / 'ios' / plan['previous'][NODE]
        assert hashlib.sha256(before_path.read_bytes()).hexdigest() == plan['inputs'][NODE]
        runtime_baseline = None
    before = before_path.read_text()
    after = (args.source / NODE).read_text()
    verify(before, after)
    with tempfile.TemporaryDirectory(prefix='temporary-interaction-asr-') as folder:
        temp = Path(folder)
        runs, rejected = execute(before, after, args.swiftc, temp) if args.swiftc else ([], [])
        if runtime_baseline is None:
            runtime_baseline = temp / 'runtime-baseline'
            for name in [RUNTIME, SETTINGS]:
                target = runtime_baseline / name
                target.parent.mkdir(parents=True, exist_ok=True)
                if name in plan['previous']:
                    origin = ROOT / 'ios' / plan['previous'][name]
                    assert hashlib.sha256(origin.read_bytes()).hexdigest() == plan['inputs'][name]
                else:
                    origin = args.source / name
                target.write_bytes(origin.read_bytes())
        runtime_runs, runtime_rejected = runtime_execute(args.source, runtime_baseline, args.swiftc, temp) if args.swiftc else ([], [])
        if args.swiftc:
            file = temp / 'complete-node.swift'
            file.write_text(after)
            subprocess.run([str(args.swiftc), '-frontend', '-parse', str(file)], check=True)
            file = temp / 'complete-runtime.swift'
            file.write_bytes((args.source / RUNTIME).read_bytes())
            subprocess.run([str(args.swiftc), '-frontend', '-parse', str(file)], check=True)
    report = {'source_sha256': hashlib.sha256(after.encode()).hexdigest(), 'baseline_sha256': hashlib.sha256(before.encode()).hexdigest(),
              'production_runs': runs, 'semantic_negative_runs': rejected, 'runtime_runs': runtime_runs, 'runtime_semantic_negative_runs': runtime_rejected, 'full_swift_parse_files': 2 if args.swiftc else 0,
              'ordinary_layout': 'Old/new production blocks compared over complete fixture matrix; native playback, hit-test and lifetime byte-identical. ASR handler changes only explicit temporary namespace admission.',
              'boundaries': 'Actual eligibility/button/color/frame/alpha/removal/pressed blocks and Runtime file/Premium/cache/Settings bodies execute. UIKit/ComponentFlow/animation, Core policy, Defaults/CodableEntry, network/decoder/frame presentation are boundaries. No playback, consume, TTL or network request is generated by this validation.',
              'apple_sdk': 'pending', 'physical_device': 'pending'}
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
