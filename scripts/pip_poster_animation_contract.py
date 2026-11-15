"""Verify the real backdrop body with explicit UIKit-completion scheduling."""
from pip_transition_coordinator_runtime import poster_fixture
from validate_private_temporary_transcription import execute


def check(source,swiftc,folder):
    folder.mkdir(parents=True,exist_ok=True)
    code=poster_fixture(source)
    runs=execute(swiftc,folder,'poster-animation-boundary',code)
    variants=[
      ('old-immediate-completion','static func animate(withDuration:Double,animations:()->Void,completion:@escaping(Bool)->Void){animations();AnimationClock.pending.append({completion(true)})}','static func animate(withDuration:Double,animations:()->Void,completion:@escaping(Bool)->Void){animations();completion(true)}','PiP poster:'),
      ('lost-image-subscription','[weak self, weak backdrop, poster] in','[weak self, weak backdrop, weak poster] in','PiP poster:'),
      ('unremoved-cover','            backdrop?.removeFromSuperview()','            _ = backdrop','PiP poster:'),
    ]
    # Both positive modes must pass first. A targeted mutant must then fail
    # through this fixture's controlled assertion (96), never compilation/crash.
    # Darwin and Linux can report different first invariants for the same mutant.
    for name,old,new,diagnostic in variants:
        assert code.count(old)==1,(name,code.count(old))
        runs+=execute(swiftc,folder,name,code.replace(old,new,1),diagnostic)
    return {'executions':runs,'boundary':'Unchanged production backdrop/poster bodies. Explicit UIView animation clock executes animations now and completion when flushed; cover/image lifetime is checked before/during/after removal. No UIKit pixels or live decoding emulated.'}
