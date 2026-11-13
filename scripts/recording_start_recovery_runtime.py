"""Фактический арбитр сессии и SwiftSignalKit; граница только native audio/capture."""
from pathlib import Path
from validate_quick_format import block

AUDIO = 'submodules/TelegramAudio/Sources/ManagedAudioSession.swift'
SIGNAL = 'submodules/SSignalKit/SwiftSignalKit/Source/'
RECORDER = 'submodules/TelegramUI/Sources/ManagedAudioRecorder.swift'
CAMERA = 'submodules/TelegramUI/Components/VideoMessageCameraScreen/Sources/VideoMessageCameraScreen.swift'


def fixture(source):
    audio = (source / AUDIO).read_text()
    library = '\n'.join((source / (SIGNAL+n)).read_text() for n in ['Atomic.swift','Disposable.swift','Subscriber.swift'])
    library += '\n'+(source/(SIGNAL+'Signal.swift')).read_text().split('@available(iOS 13.0, macOS 10.15, *)',1)[0]
    library += '\n'+block((source/(SIGNAL+'Signal_Dispatch.swift')).read_text(),'public func deliverOn<T, E>(_ queue: Queue)')
    queue = (source/(SIGNAL+'Queue.swift')).read_text()
    # Swift6's Linux Dispatch overlay diagnoses upstream's pre-concurrency
    # closure signatures. WorkItem bridges only the dispatch submission;
    # Queue.async's real isCurrent/inline branch is retained verbatim.
    for old,new in [('self.nativeQueue.async(execute: f)','self.nativeQueue.async(execute: DispatchWorkItem(block: f))'),
                    ('self.nativeQueue.async(group: nil, qos: qos, flags: [.enforceQoS], execute: f)','self.nativeQueue.async(execute: DispatchWorkItem(qos: qos, flags: [.enforceQoS], block: f))'),
                    ('self.nativeQueue.asyncAfter(deadline: time, execute: f)','self.nativeQueue.asyncAfter(deadline: time, execute: DispatchWorkItem(block: f))')]:
        assert old in queue; queue=queue.replace(old,new)
    library += '\n'+queue
    library += '\n'+block(audio,'public enum ManagedAudioSessionType: Equatable')
    library += '\n'+block(audio,'private final class HolderRecord')
    methods='\n'.join(block(audio, m) for m in ['private func removeDeactivatedHolder(id: Int32)', 'private func updateHolders(interruption: Bool = false)'])
    return library + r'''
func managedAudioSessionLog(_ message: @autoclosure () -> String) {}
enum AudioSessionOutputMode { case system }
enum AudioSessionOutput {}
final class ManagedAudioSessionControl {}
final class TestTimer { func invalidate() {} }
private final class Arbiter {
    let queue = Queue(name: "recording-transfer-test")
    var holders: [HolderRecord] = []
    var deactivateTimer: TestTimer?
    var idle = 0
    var nextId: Int32 = 0
    func applyNoneDelayed() { idle += 1 }
''' + methods + r'''
    // Fixture client boundary: no AVAudioSession configuration/capture is
    // simulated. Production update/remove and real queue/signals run above.
    func push(_ type: ManagedAudioSessionType, once: Bool = false,
              activate: @escaping () -> Void, deactivate: @escaping (Bool) -> Signal<Void,NoError> = { _ in .complete() }) -> Int32 {
        assert(queue.isCurrent()); nextId += 1
        let id = nextId
        holders.append(HolderRecord(id: id, audioSessionType: type, control: ManagedAudioSessionControl(), activate: { _ in activate() }, deactivate: deactivate, headsetConnectionStatusChanged: { _ in }, availableOutputsChanged: { _,_ in }, once: once, outputMode: .system))
        updateHolders(); return id
    }
    func remove(_ id: Int32) { removeDeactivatedHolder(id: id) }
    func interrupt() { updateHolders(interruption: true) }
    func tick() { updateHolders() }
}
private var assertions = 0
private func check(_ value: @autoclosure () -> Bool, _ message: String) {
    assertions += 1
    if !value() { print("FAIL: " + message); exit(96) }
}
@main struct RecordingTransferTests {
    static func main() {
        let playback: [ManagedAudioSessionType] = [.play(mixWithOthers: false), .play(mixWithOthers: true), .playWithPossiblePortOverride, .ambient]
        for type in playback { for withOthers in [false,true] { for once in [false,true] { for single in [false,true] {
            let a = Arbiter()
            a.queue.sync {
                var plays = 0; var records = 0; var temporarilyReleased: [Bool] = []
                let p = a.push(type, once: once, activate: { plays += 1 }, deactivate: { temporary in
                    temporarilyReleased.append(temporary)
                    return single ? .single(()) : .complete()
                })
                for n in 1...30 {
                    let r = a.push(.voiceMessageRecording(beginWithTone: false, pauseMusicOnRecording: !withOthers), activate: { records += 1 })
                    check(records == n, "every repeated voice/round request acquires the session")
                    check(a.holders.allSatisfy { $0.deactivatingDisposable == nil }, "inline completion must not leave a stale deactivation holder")
                    a.tick()
                    check(a.holders.last?.id == r && a.holders.last?.active == true, "recording remains active after arbitration")
                    a.remove(r)
                    check(!a.holders.contains { $0.id == r }, "cancelled recording releases its holder")
                    check(plays == (once ? 1 : n+1), "previous playback is restored only for reusable holder")
                }
                check(temporarilyReleased.allSatisfy { $0 == withOthers }, "music mixing handoff contract retained")
                a.remove(p)
                check(a.holders.isEmpty, "no stranded holder after stop")
            }
        }}}}
        // Delayed completion must block activation, including repeated calls
        // and cancellation/replacement of a waiting recorder.
        for cancelRecording in [false,true] { for removePlayer in [false,true] {
            let a=Arbiter()
            a.queue.sync {
                var completion: Subscriber<Void,NoError>?
                var cancelled=0; var started=0
                let p=a.push(.play(mixWithOthers:false), activate:{}, deactivate:{ _ in Signal { s in
                    completion=s; return ActionDisposable { cancelled += 1 }
                }})
                let r=a.push(.record(speaker:false,video:false,withOthers:false),activate:{ started += 1 })
                for _ in 0..<5 { a.tick() }
                check(started == 0, "async player release is awaited before recording")
                if cancelRecording { a.remove(r) }
                if removePlayer { a.remove(p) }
                completion?.putCompletion()
                check(started == (cancelRecording ? 0 : 1), "cancelled pending take never starts; live take starts once")
                check(cancelled == 1, "async deactivation disposable is released exactly once")
                check(a.holders.allSatisfy { $0.deactivatingDisposable == nil }, "async/cancel path clears deactivation")
                a.remove(r);a.remove(p)
                var next=0
                let nextId=a.push(.record(speaker:false,video:false,withOthers:true),activate:{ next += 1 })
                check(next == 1,"recording recovers after cancelled transfer without restart")
                a.remove(nextId)
            }
        }}
        // AV calls retain their existing priority. No timeout/forced activation.
        for mixed in [false,true] {
            let a=Arbiter()
            a.queue.sync {
                var callReleases=0;var started=0
                let call=a.push(.voiceCall,activate:{},deactivate:{ _ in callReleases += 1;return .complete() })
                let r=a.push(.record(speaker:false,video:false,withOthers:mixed),activate:{ started += 1 })
                a.interrupt()
                check(started == 0 && callReleases == 0,"recording and interruption preserve active call priority")
                a.remove(r);a.remove(call)
            }
        }
        // An interrupted reusable playback lease can be reacquired repeatedly.
        let a=Arbiter()
        a.queue.sync {
            var played=0;var released=0
            let p=a.push(.play(mixWithOthers:false),activate:{ played += 1 },deactivate:{ _ in released += 1;return .complete() })
            for n in 1...10 {
                a.interrupt()
                check(released == n && played == n+1,"repeated interruption remains usable")
                check(a.holders.first?.deactivatingDisposable == nil,"interruption clears inline completion marker")
            }
            a.remove(p)
        }
        print("PASS: \(assertions) recording-transfer assertions")
    }
}
'''
