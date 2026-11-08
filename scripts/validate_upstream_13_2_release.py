#!/usr/bin/env python3
"""Verify the final Telegram13.2 migration and its guarded historical bridge."""
import argparse
import copy
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile

from validate_quick_format import block, manifest
from validate_pip_playback_commands import execute
from late_source_stages import LATE_SOURCE_STAGES, check_copy_contract, copy_outputs

ROOT = Path(__file__).resolve().parents[1]
OVERLAY = ROOT / 'ios'
PIN = '24638bc69bd083981b178dd1e7f921eebbf7fc46'
BASE = '279f89e4d4f63f17227bf877dc3d8990f22ecd58'
STATE = 'submodules/TelegramCore/Sources/State/Sync/'
SDK_COMPILE_STAGES = ('upstream_13_2_release_compile', 'upstream_13_2_release_ui_compile', 'upstream_13_2_release_auth_compile', 'upstream_13_2_release_delivery_compile', 'upstream_13_2_release_ack_compile', 'upstream_13_2_release_string_compile')
SDK_STAGES = SDK_COMPILE_STAGES + LATE_SOURCE_STAGES


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def native_input_contract(plan, require_account=True):
    account = 'submodules/TelegramCore/Sources/Account/AccountIntermediateState.swift'
    if require_account:
        assert account in plan['native_inputs'], 'Missing native13.2 account-state origin'
    for name, expected_blob in plan['native_inputs'].items():
        data = (OVERLAY / plan['previous'][name]).read_bytes()
        blob = hashlib.sha1(b'blob ' + str(len(data)).encode() + b'\0' + data).hexdigest()
        assert blob == expected_blob, 'Native13.2 input origin mismatch: ' + name


def checked_plan(stage):
    plan = json.loads((OVERLAY / (stage + '_patches.json')).read_text())
    assert plan['target_pin'] == PIN and plan['overlay_base_pin'] == BASE
    assert all(plan['inputs'].keys() == plan[field].keys() for field in ('outputs', 'previous', 'replacements'))
    assert not set(plan['inputs']) & set(plan['guards'])
    assert not set(plan['copies']) & (set(plan['inputs']) | set(plan['guards']))
    for name, expected in plan['templates'].items():
        path = OVERLAY / name
        assert path.resolve().is_relative_to(OVERLAY.resolve())
        assert digest(path) == expected, name
    for name, expected in plan['inputs'].items():
        assert digest(OVERLAY / plan['previous'][name]) == expected, name
        assert digest(OVERLAY / plan['replacements'][name]) == plan['outputs'][name], name
    for name, item in plan['copies'].items():
        destination = Path(name)
        assert not destination.is_absolute() and '..' not in destination.parts, name
        path = OVERLAY / item['source']
        assert path.resolve().is_relative_to(OVERLAY.resolve()), name
        assert digest(path) == item['sha256'], name
    if stage in LATE_SOURCE_STAGES:
        check_copy_contract(stage, plan)
    if stage == 'upstream_13_2_release_post':
        native_input_contract(plan, require_account=True)
    elif plan.get('native_inputs'):
        assert set(plan['native_inputs']) <= set(plan['inputs']), stage
        native_input_contract(plan, require_account=False)
    for name, item in plan['deletions'].items():
        assert plan['guards'][name] == item['sha256']
        assert digest(OVERLAY / item['source']) == item['sha256']
    return plan


def checked_sdk_plans(post):
    expected = {**post['outputs'], **post['guards']}
    plans = []
    for stage in SDK_STAGES:
        plan = checked_plan(stage)
        if stage in LATE_SOURCE_STAGES:
            check_copy_contract(stage, plan)
        else:
            assert not plan['copies'] and not plan['deletions']
        assert not set(plan['copies']) & set(expected), 'Copy replaces an existing SDK stage path'
        for name, value in plan['inputs'].items():
            if name not in expected:
                assert name in plan.get('native_inputs', {}), 'Unproven native SDK stage input: ' + name
                # checked_plan verified both SHA256 and Git's blob origin for
                # the exact pinned native snapshot; unknown inputs cannot pass.
                expected[name] = value
            assert expected[name] == value, 'Broken SDK stage chain: ' + name
        for name, value in plan['guards'].items():
            assert expected.get(name, value) == value, name
        expected.update(plan['guards'])
        expected.update(plan['outputs'])
        expected.update(copy_outputs(plan))
        plans.append(plan)
    return plans, expected


def verify(source):
    pre = checked_plan('upstream_13_2_release_pre')
    post = checked_plan('upstream_13_2_release_post')
    sdk_plans, final_outputs = checked_sdk_plans(post)
    for plan in sdk_plans:
        for name in plan['copies']:
            assert not (source / name).is_symlink(), 'Copied helper is not a regular source: ' + name
        for name, expected in plan['guards'].items():
            assert digest(source / name) == final_outputs.get(name, expected), name
    for name, expected in final_outputs.items():
        if name not in post['deletions']:
            assert digest(source / name) == expected, 'Final source output differs: ' + name
    for name, expected in {**post['outputs'], **post['guards']}.items():
        if name in post['deletions']:
            assert not (source / name).exists(), name
        else:
            assert digest(source / name) == final_outputs[name], name
    assert set(pre['copies']) == set(post['deletions'])
    versions = json.loads((source / 'versions.json').read_text())
    assert versions['app'] == '13.2' and versions['xcode'] == '27.1'
    pins = dict(line.split('=', 1) for line in (OVERLAY / 'upstream.env').read_text().splitlines() if '=' in line)
    assert pins['TELEGRAM_IOS_REF'] == PIN and pins['TELEGRAM_IOS_VERSION'] == '13.2'
    pipeline = (OVERLAY / 'apply_overlay.py').read_text()
    assert pipeline.index('    apply_upstream_13_2_release_pre(') < pipeline.index('    apply_upstream_13_2_pre(')
    workflow = (ROOT / '.github/workflows/build-unsigned-ipa.yml').read_text()
    assert workflow.index('apply_upstream_13_2_post(') < workflow.index('apply_upstream_13_2_release_post(')
    assert workflow.index('apply_upstream_13_2_release_post(') < workflow.index('apply_upstream_13_2_release_compile(') < workflow.index('validate_upstream_13_2_release.py')
    assert workflow.index('apply_upstream_13_2_release_compile(') < workflow.index('apply_upstream_13_2_release_ui_compile(') < workflow.index('validate_upstream_13_2_release.py')
    assert workflow.index('apply_upstream_13_2_release_ui_compile(') < workflow.index('apply_upstream_13_2_release_auth_compile(') < workflow.index('validate_upstream_13_2_release.py')
    assert workflow.index('apply_upstream_13_2_release_auth_compile(') < workflow.index('apply_upstream_13_2_release_delivery_compile(') < workflow.index('validate_upstream_13_2_release.py')
    assert workflow.index('apply_upstream_13_2_release_delivery_compile(') < workflow.index('apply_upstream_13_2_release_ack_compile(') < workflow.index('validate_upstream_13_2_release.py')
    assert workflow.index('apply_upstream_13_2_release_ack_compile(') < workflow.index('apply_upstream_13_2_release_string_compile(') < workflow.index('validate_upstream_13_2_release.py')
    order = [workflow.index('apply_' + stage + '(') for stage in SDK_STAGES]
    assert order == sorted(order) and len(order) == len(set(order))
    for index, stage in enumerate(LATE_SOURCE_STAGES):
        validation = workflow.index('python3 scripts/validate_' + stage + '.py')
        next_stage = LATE_SOURCE_STAGES[index + 1] if index + 1 < len(LATE_SOURCE_STAGES) else None
        boundary = workflow.index('apply_' + next_stage + '(') if next_stage else workflow.index('python3 scripts/validate_upstream_13_2_release.py')
        assert workflow.index('apply_' + stage + '(') < validation < boundary
    assert workflow.index('python3 scripts/validate_temporary_message_interaction.py') < workflow.index('python3 scripts/validate_account_settings_entry.py') < workflow.index('python3 scripts/validate_release_090_preflight_fixes.py') < workflow.index('python3 scripts/validate_late_source_stages.py') < workflow.index('python3 scripts/validate_upstream_13_2_release.py')
    assert workflow.index('validate_custom_member_references.py --canonical') < workflow.index('Применить overlay NagramiX')
    assert workflow.index('validate_upstream_13_2_release.py') < workflow.index('--final-upstream-13-2')
    messages = (source / (STATE + 'StateReplay+Messages.swift')).read_text()
    for hook in ('captureIncoming', 'recordIncomingEdit', 'archiveMessagesBeforeDeletion',
                 'archiveServerDeletion', 'archiveMessageRangeBeforeDeletion',
                 'cacheResourcesToRemove', 'retainTelegramTranscription'):
        assert hook in messages, hook
    reads = (source / (STATE + 'StateReplay+ReadStates.swift')).read_text()
    assert reads.count('consumeDate: date, messageArchive: NagramiXMessageArchive.forPostbox(postbox)') == 2
    interpreter = (source / (STATE + 'UpdateInterpreter+Peers.swift')).read_text()
    assert 'updatedState.nagramiXBlockedPeerUpdates[userPeerId] = (updatePeerBlockedData.flags & (1 << 0)) != 0' in interpreter
    assert 'NagramiXBlockedMessageFilter' not in interpreter  # Pure interpretation; persistence is replay-only.
    state = (source / 'submodules/TelegramCore/Sources/Account/AccountIntermediateState.swift').read_text()
    assert 'var nagramiXBlockedPeerUpdates: [PeerId: Bool] = [:]' in state
    assert 'nagramiXBlockedPeerUpdates' not in block(state, '    func branch()')
    assert 'self.nagramiXBlockedPeerUpdates.merge(other.nagramiXBlockedPeerUpdates, uniquingKeysWith: { _, latest in latest })' in block(state, '    mutating func merge(')
    replay = (source / (STATE + 'StateReplay.swift')).read_text()
    assert replay.index('ReplayRejection') < replay.index('for (peerId, blocked) in finalState.state.nagramiXBlockedPeerUpdates') < replay.index('ReplayPrepass.prepare(')
    read = (source / 'submodules/TelegramCore/Sources/TelegramEngine/Messages/ApplyMaxReadIndexInteractively.swift').read_text()
    assert read.index('transaction.applyInteractiveReadMaxIndex(readIndex)') < read.index('nagramiXRecordPrivateRead(transaction: transaction, index: readIndex)')
    hls = (source / 'submodules/TelegramUniversalVideoContent/Sources/HLSVideoNativeContentNode.swift').read_text()
    assert 'private var nagramiXBackgroundPlaybackOwners = Set<UUID>()' in hls
    assert 'self.nagramiXBackgroundPlaybackOwners.insert(id)' in hls and 'self.nagramiXBackgroundPlaybackOwners.remove(id)' in hls
    copier = (source / 'submodules/TelegramUI/Sources/Chat/NagramiXCopyDelivery.swift').read_text()
    assert 'LottieSettings' not in copier
    filters = (source / 'submodules/AccountContext/Sources/PeerSelectionController.swift').read_text()
    import re
    bits = re.findall(r'public static let (\w+) = ChatListNodePeersFilter\(rawValue: 1 << (\d+)\)', filters)
    for name, bit in bits:
        if name.startswith('nagramiX'):
            assert sum(other_bit == bit for _, other_bit in bits) == 1, 'Colliding custom recipient filter: ' + name
    return pre, post


def guard_checks(source, stage, plan, folder):
    """Exercise replay and representative corruptions; prove refusal precedes writes."""
    spec = importlib.util.spec_from_file_location(stage, OVERLAY / (stage + '.py'))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    apply = getattr(module, 'apply_' + stage)
    baseline = folder / 'baseline'
    for name in {**plan['inputs'], **plan['guards']}:
        path = baseline / name
        path.parent.mkdir(parents=True, exist_ok=True)
        if name in plan['previous']:
            origin = OVERLAY / plan['previous'][name]
        elif name in plan['deletions']:
            origin = OVERLAY / plan['deletions'][name]['source']
        else:
            origin = source / name
            if digest(origin) != plan['guards'][name]:
                # A later SDK fix can replace an otherwise guarded post file.
                # Reconstruct that earlier stage's exact input, never relax SHA.
                candidates = {}
                for sdk_stage in SDK_STAGES:
                    sdk = checked_plan(sdk_stage)
                    if sdk['inputs'].get(name) == plan['guards'][name]:
                        candidate = OVERLAY / sdk['previous'][name]
                        candidates[candidate.read_bytes()] = candidate
                    if sdk['outputs'].get(name) == plan['guards'][name]:
                        candidate = OVERLAY / sdk['replacements'][name]
                        candidates[candidate.read_bytes()] = candidate
                    if sdk['copies'].get(name, {}).get('sha256') == plan['guards'][name]:
                        candidate = OVERLAY / sdk['copies'][name]['source']
                        candidates[candidate.read_bytes()] = candidate
                assert len(candidates) == 1, 'Cannot reconstruct guarded input: ' + name
                data, origin = next(iter(candidates.items()))
                assert hashlib.sha256(data).hexdigest() == plan['guards'][name], name
        path.write_bytes(origin.read_bytes())

    def seed(label):
        tree = folder / label
        shutil.copytree(baseline, tree, copy_function=os.link)
        return tree

    def detach_write(path, data):
        if path.exists() or path.is_symlink():
            path.unlink()
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)

    rejected = []
    def reject(tree, label, overlay=OVERLAY):
        before = manifest(tree)
        try:
            apply(tree, overlay)
        except (SystemExit, OSError):
            pass
        else:
            raise AssertionError('Invalid migration input accepted: ' + label)
        assert manifest(tree) == before, 'Partial migration: ' + label
        rejected.append(label)
        shutil.rmtree(tree)

    valid = seed('valid')
    for name in plan['inputs']:
        detach_write(valid / name, (valid / name).read_bytes())
    apply(valid, OVERLAY)
    for name, expected in plan['outputs'].items():
        assert digest(valid / name) == expected, name
    for name, item in plan['copies'].items():
        assert digest(valid / name) == item['sha256'], name
    for name in plan['deletions']:
        assert not (valid / name).exists(), name
    reject(valid, 'repeat')
    for field in ('inputs', 'guards'):
        names = sorted(plan[field])
        selected = set(names[:1] + names[len(names)//2:len(names)//2+1] + names[-1:])
        selected.update(name for name in names if name.startswith('build-system/') or name.startswith(STATE))
        for index, name in enumerate(sorted(selected)):
            for kind in ('missing', 'drift'):
                tree = seed(field + '-' + str(index) + '-' + kind)
                path = tree / name
                path.unlink()
                if kind == 'drift':
                    path.write_bytes(b'changed migration input')
                reject(tree, field + '/' + name + '/' + kind)
    for index, name in enumerate(plan['copies']):
        tree = seed('copy-' + str(index))
        detach_write(tree / name, b'existing destination')
        reject(tree, 'existing-copy/' + name)
    for kind in ('template-drift', 'unsafe-output', 'invalid-manifest', 'invalid-deletion', 'copy-template-drift', 'unsafe-copy', 'invalid-copy'):
        if kind == 'invalid-deletion' and not plan['deletions']:
            continue
        if kind in ('copy-template-drift', 'unsafe-copy', 'invalid-copy') and not plan['copies']:
            continue
        local = folder / ('overlay-' + kind)
        for name in plan['templates']:
            target = local / name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(OVERLAY / name, target)
        changed = copy.deepcopy(plan)
        name = next(iter(plan['inputs']))
        if kind == 'template-drift':
            detach_write(local / plan['replacements'][name], b'changed template')
        elif kind == 'invalid-manifest':
            del changed['outputs'][name]
        elif kind == 'unsafe-output':
            for field in ('inputs', 'outputs', 'previous', 'replacements'):
                changed[field]['../escape'] = changed[field].pop(name)
        elif kind == 'invalid-deletion':
            changed['deletions'][next(iter(changed['deletions']))]['sha256'] = '0' * 64
        elif kind == 'copy-template-drift':
            detach_write(local / next(iter(plan['copies'].values()))['source'], b'changed copy template')
        elif kind == 'unsafe-copy':
            changed['copies']['../escape.swift'] = changed['copies'].pop(next(iter(changed['copies'])))
        else:
            changed['copies'][next(iter(changed['copies']))]['sha256'] = '0' * 64
        (local / (stage + '_patches.json')).write_text(json.dumps(changed))
        reject(seed(kind), kind, local)
        shutil.rmtree(local)
    shutil.rmtree(baseline)
    return rejected


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--swiftc', type=Path, required=True)
    parser.add_argument('--report', type=Path)
    args = parser.parse_args()
    pre, post = verify(args.source)
    with tempfile.TemporaryDirectory(prefix='nagramix-13-2-') as temporary:
        temp = Path(temporary)
        rejected = {}
        for suffix, plan in (('pre', pre), ('post', post)):
            folder = temp / suffix
            folder.mkdir()
            rejected[suffix] = len(guard_checks(args.source, 'upstream_13_2_release_' + suffix, plan, folder))
        run = temp / 'runtime'
        run.mkdir()
        from validate_system_video_pip import historical_late_source
        with historical_late_source(args.source) as historical:
            executions = execute(historical, args.swiftc, run)
        _, final_outputs = checked_sdk_plans(post)
        paths = {name for name in final_outputs if name.endswith('.swift') and name not in post['deletions']}
        for name in sorted(paths):
            subprocess.run([str(args.swiftc), '-frontend', '-parse', str(args.source / name)], check=True)
    subprocess.run([os.sys.executable, str(args.source / 'build-system/Make/PostboxImportCheck.py'), str(args.source)], check=True)
    report = {'target_pin': PIN, 'pre_replacements': len(pre['outputs']), 'post_replacements': len(post['outputs']),
              'deleted_obsolete_files': len(post['deletions']), 'fail_closed': rejected, 'parsed_swift': len(paths),
              'executions': executions, 'historical_runtime_boundary': 'exact published bytes after verified inverse of all registered late source stages',
              'late_source_stages': list(LATE_SOURCE_STAGES), 'native_postbox_imports': 'passed', 'apple_sdk': 'pending', 'device': 'pending'}
    if args.report:
        args.report.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps(report, ensure_ascii=False, indent=2), flush=True)


if __name__ == '__main__':
    main()
