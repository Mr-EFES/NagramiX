#!/usr/bin/env python3
"""Prove the registered source inverse and fail-closed validation bridge.

No SDK or application compilation is performed. The original source is read
only; corruptions and temporary historical views live in temporary folders.
"""
import argparse
import copy
import json
from pathlib import Path
import shutil
import tempfile

import late_source_stages as late
import validate_upstream_13_2_release as release
from validate_quick_format import manifest


def published_contract(post):
    expected = {**post['outputs'], **post['guards']}
    for stage in release.SDK_COMPILE_STAGES:
        plan = release.checked_plan(stage)
        expected.update(plan['guards'])
        expected.update(plan['outputs'])
    # First appearances in the source-only chain describe untouched native
    # paths (notably TabBarComponent); later appearances must not overwrite the
    # original published bytes used for inverse verification.
    introduced = set()
    for plan in late.checked_late_plans():
        for name, value in {**plan['inputs'], **plan['guards']}.items():
            if name not in introduced:
                expected.setdefault(name, value)
        introduced.update(plan['copies'])
    return {name: value for name, value in expected.items()
            if name not in post['deletions'] and name not in introduced}


def check(source, published=None):
    post = release.checked_plan('upstream_13_2_release_post')
    plans, final = release.checked_sdk_plans(post)
    for name, value in final.items():
        if name not in post['deletions']:
            assert release.digest(source / name) == value, name
    late_plans = plans[-len(late.LATE_SOURCE_STAGES):]
    introduced = {name for plan in late_plans for name in plan['copies']}
    assert late.verified_prefix(source, late_plans) == len(late.LATE_SOURCE_STAGES)
    before = manifest(source)
    expected = published_contract(post)
    with late.historical_source(source) as prior:
        for name, value in expected.items():
            assert release.digest(prior / name) == value, 'Inverse differs from published contract: ' + name
            if published is not None:
                assert (prior / name).read_bytes() == (published / name).read_bytes(), 'Inverse differs from actual published pipeline: ' + name
        assert late.verified_prefix(prior, late_plans) == 0
        for name in introduced:
            assert not (prior / name).exists() and not (prior / name).is_symlink(), 'Introduced API leaked into historical source: ' + name
            if published is not None:
                assert not (published / name).exists() and not (published / name).is_symlink(), name
    with late.historical_source(source, before_stage=late.TEMPORARY_INTERACTION_STAGE) as before_ninth:
        assert late.verified_prefix(before_ninth, late_plans) == len(late.LATE_SOURCE_STAGES) - 1
        assert not (before_ninth / late.TEMPORARY_REPLY_HELPER).exists(), 'New helper leaked into pre-ninth checkpoint'

    rejected = []
    with tempfile.TemporaryDirectory(prefix='nagramix-late-source-checks-') as temporary:
        folder = Path(temporary)
        projection = folder / 'projection'
        for name in final:
            if name in post['deletions']:
                continue
            target = projection / name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source / name, target)
        assert late.verified_prefix(projection, late_plans) == len(late.LATE_SOURCE_STAGES), 'Negative projection is not a valid final checkpoint'
        projection_before = manifest(projection)

        def reject(label):
            snapshot = manifest(projection)
            try:
                assert late.verified_prefix(projection, late_plans) == len(late.LATE_SOURCE_STAGES)
            except (AssertionError, OSError):
                pass
            else:
                raise AssertionError('Corrupted late source accepted: ' + label)
            assert manifest(projection) == snapshot, 'Validation mutated source: ' + label
            rejected.append(label)

        for stage, plan in zip(late.LATE_SOURCE_STAGES, late_plans):
            name = next(iter(plan['outputs']))
            path = projection / name
            data = path.read_bytes()
            path.write_bytes(data + b'\n// simulated source drift\n')
            reject(stage + '/output-drift')
            path.write_bytes(data)
        name = next(iter(late_plans[-1]['guards']))
        path = projection / name
        data = path.read_bytes()
        path.unlink()
        reject('native-guard-missing')
        path.write_bytes(data)

        for name in introduced:
            path = projection / name
            data = path.read_bytes()
            path.write_bytes(data + b'\n// simulated copied helper drift\n')
            reject('copied-helper-drift')
            path.unlink()
            reject('copied-helper-missing')
            external = folder / 'external-helper.swift'
            external.write_bytes(data)
            path.symlink_to(external)
            reject('copied-helper-external-symlink')
            path.unlink()
            path.write_bytes(data)
        assert manifest(projection) == projection_before, 'Source mutations were not restored between negative cases'

        # Template drift must be rejected before historical_source creates or
        # writes a historical view, and must never mutate the actual source.
        overlay = folder / 'bad-overlay'
        first = late.LATE_SOURCE_STAGES[0]
        plan = late_plans[0]
        for name in plan['templates']:
            target = overlay / name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(release.OVERLAY / name, target)
        (overlay / (first + '_patches.json')).write_text(json.dumps(plan))
        output = overlay / next(iter(plan['replacements'].values()))
        output.write_bytes(output.read_bytes() + b'\n// simulated template drift\n')
        original = release.OVERLAY
        try:
            release.OVERLAY = overlay
            try:
                with late.historical_source(source):
                    raise RuntimeError('Corrupt template reached historical view')
            except AssertionError:
                rejected.append('template-drift-before-inverse')
        finally:
            release.OVERLAY = original

        # Every newly reached native input requires its exact Git blob proof.
        # The wide component and stage-nine native hooks have separate origins;
        # rejecting only the first stage would mask missing later proofs.
        for stage, actual_plan in zip(late.LATE_SOURCE_STAGES, late_plans):
            if not actual_plan.get('native_inputs'):
                continue
            native = copy.deepcopy(actual_plan)
            native.pop('native_inputs')
            checked_plan = release.checked_plan
            try:
                release.checked_plan = lambda name: native if name == stage else checked_plan(name)
                try:
                    release.checked_sdk_plans(post)
                except AssertionError as error:
                    assert 'Unproven native SDK stage input' in str(error), str(error)
                    rejected.append(stage + '/native-blob-proof-missing')
                else:
                    raise AssertionError('Unknown native input accepted without provenance: ' + stage)
            finally:
                release.checked_plan = checked_plan
            for name in actual_plan['native_inputs']:
                native = copy.deepcopy(actual_plan)
                native['native_inputs'][name] = '0' * 40
                try:
                    release.native_input_contract(native, require_account=False)
                except AssertionError as error:
                    assert 'Native13.2 input origin mismatch: ' + name in str(error), str(error)
                    rejected.append(stage + '/native-blob-drift/' + name)
                else:
                    raise AssertionError('Wrong native input origin accepted: ' + name)

    assert manifest(source) == before, 'The full native source changed during validation'
    return {
        'late_source_stages': list(late.LATE_SOURCE_STAGES),
        'published_contract_paths': len(expected),
        'actual_published_pipeline_compared': published is not None,
        'full_source_files_preserved': len(before),
        'introduced_helpers_absent_from_history': sorted(introduced),
        'pre_ninth_checkpoint_verified': True,
        'negative_projection_verified_before_mutation': True,
        'fail_closed': rejected,
        'sdk': 'not_run',
        'device': 'pending',
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--published', type=Path)
    parser.add_argument('--report', type=Path)
    args = parser.parse_args()
    result = check(args.source, args.published)
    if args.report:
        args.report.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps(result, ensure_ascii=False, indent=2), flush=True)


if __name__ == '__main__':
    main()
