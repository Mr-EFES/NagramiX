#!/usr/bin/env python3
"""Prove the eight-stage source inverse and fail-closed validation bridge.

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
    for plan in late.checked_late_plans():
        for name, value in {**plan['inputs'], **plan['guards']}.items():
            expected.setdefault(name, value)
    return {name: value for name, value in expected.items()
            if name not in post['deletions']}


def check(source, published=None):
    post = release.checked_plan('upstream_13_2_release_post')
    plans, final = release.checked_sdk_plans(post)
    for name, value in final.items():
        if name not in post['deletions']:
            assert release.digest(source / name) == value, name
    late_plans = plans[-len(late.LATE_SOURCE_STAGES):]
    assert late.verified_prefix(source, late_plans) == len(late.LATE_SOURCE_STAGES)
    before = manifest(source)
    expected = published_contract(post)
    with late.historical_source(source) as prior:
        for name, value in expected.items():
            assert release.digest(prior / name) == value, 'Inverse differs from published contract: ' + name
            if published is not None:
                assert (prior / name).read_bytes() == (published / name).read_bytes(), 'Inverse differs from actual published pipeline: ' + name
        assert late.verified_prefix(prior, late_plans) == 0

    rejected = []
    with tempfile.TemporaryDirectory(prefix='nagramix-late-source-checks-') as temporary:
        folder = Path(temporary)
        projection = folder / 'projection'
        for name in expected:
            target = projection / name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source / name, target)

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

        # The one native file newly introduced into the final stage chain must
        # have its pinned Git blob proof, not merely an unknown SHA accepted.
        native = copy.deepcopy(late_plans[0])
        assert native.get('native_inputs'), 'Native input provenance missing'
        native.pop('native_inputs')
        checked_plan = release.checked_plan
        try:
            release.checked_plan = lambda stage: native if stage == first else checked_plan(stage)
            try:
                release.checked_sdk_plans(post)
            except AssertionError as error:
                assert 'Unproven native SDK stage input' in str(error), str(error)
                rejected.append('native-blob-proof-missing')
            else:
                raise AssertionError('Unknown native input accepted without provenance')
        finally:
            release.checked_plan = checked_plan

    assert manifest(source) == before, 'The full native source changed during validation'
    return {
        'late_source_stages': list(late.LATE_SOURCE_STAGES),
        'published_contract_paths': len(expected),
        'actual_published_pipeline_compared': published is not None,
        'full_source_files_preserved': len(before),
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
